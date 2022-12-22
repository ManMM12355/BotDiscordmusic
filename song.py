import discord
from discord.utils import get
import youtube_dl
import asyncio
from async_timeout import timeout
from functools import partial
import itertools
from discord import ActionRow, Button, ButtonStyle

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'yesplaylist': True,
    'playliststart': 1,
    'playlistend': 100,
    #'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5" ## song will end if no this line
    #'before_options': '-nostdin',

}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        await ctx.send(f'```ini\n[Added {data["title"]} to the Queue.]\n```') #delete after can be added

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source, **ffmpeg_options), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, requester=requester)

class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get() # get the next song from the queue
            except asyncio.TimeoutError:
                #await self._guild.voice_client.disconnect()
                #return  self.bot.loop.create_task(self._cog.cleanup(self._guild))
                #del songAPI.players[self._guild]
                return await self.destroy(self._guild) 

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                            f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                            f'`{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    async def destroy(self, guild):
        """Disconnect and cleanup the player."""
        #del self.players[guild.id]
        #await self._guild.voice_client.disconnect()
        return self.bot.loop.create_task(self.cleanup(guild))

    async def cleanup(self, guild):
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass

        try:
            del songAPI.players[guild.id]
        except KeyError:
            pass

############
class songAPI:

    players = {}

    async def play(self, ctx,search: str):
        self.bot = ctx.bot
        self._guild = ctx.guild
        channel = ctx.author.voice.channel
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        
        print(f"{ctx.author}:{search}")

        if voice_client == None:
            await ctx.send(f'Connected to: **{channel}**', delete_after=5)
            await channel.connect()
            voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        await ctx.trigger_typing()

        _player = self.get_player(ctx)
        source = await YTDLSource.create_source(ctx, search, loop=self.bot.loop, download=False)

        await _player.queue.put(source)

    def get_player(self, ctx):
        try:
            player = self.players[ctx.guild.id]
        except:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
        
        return player

    async def stop(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            await ctx.channel.send("Bot is not connected to vc")
            return

        if voice_client.channel != ctx.author.voice.channel:
            await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
            return

        voice_client.stop()

    async def pause(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            await ctx.channel.send("Bot is not connected to vc")
            return

        if voice_client.channel != ctx.author.voice.channel:
            await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
            return

        voice_client.pause()

    async def resume(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        if voice_client == None:
            await ctx.channel.send("Bot is not connected to vc")
            return

        if voice_client.channel != ctx.author.voice.channel:
            await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
            return

        voice_client.resume()

    async def leave(self, ctx):
        del self.players[ctx.guild.id]
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)
        await ctx.voice_client.disconnect()

    async def queueList(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return
        
        player = self.get_player(ctx)
        if player.queue.empty():
            return await ctx.send('There are currently no more queued songs')
        
        # 1 2 3
        upcoming = list(itertools.islice(player.queue._queue,0,player.queue.qsize()))
        fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
        embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)
        await ctx.send(embed=embed)

    async def skip(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return

        if voice_client.is_paused():
            pass
        elif not voice_client.is_playing():
            return

        voice_client.stop()
        await ctx.send(f'**`{ctx.author}`**: Skipped the song!')

    async def now_playing_(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return
        
        player = self.get_player(ctx)
        if player.current == None:
            return await ctx.send('There is currently no song playing')
        
        await ctx.send(f'**Now Playing:** `{player.current.title}` requested by `{player.current.requester}`')

    async def volume(self, ctx, volume: int):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return

        if volume > 100:
            return await ctx.send('Volume cannot be greater than 100%')

        voice_client.source.volume = volume / 100
        await ctx.send(f'**`{ctx.author.name}`**: Set the volume to **{volume}%**') 

    async def move(self, ctx, channel: discord.VoiceChannel):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client.channel == channel:
            return await ctx.send('I am already in that channel')
        
        await voice_client.move_to(channel)
        await ctx.send(f'**`{ctx.author}`**: Moved to **{channel}**', delete_after=10)

    async def deletemessage(self, ctx, index: int):
        await ctx.channel.purge(limit=index)
        await ctx.send(f'**`{ctx.author}`**: Deleted  {index} message', delete_after=10)

    async def deleteall(self, ctx):
        msg = await ctx.channel.history(limit=None).flatten()
        await ctx.send(f'**`{ctx.author.name}`**: Deleted total {len(msg)} messages', delete_after=10)

        await ctx.channel.purge(limit=None)
        await ctx.send(f'**`{ctx.author.name}`**: Deleted all messages', delete_after=10)
        print(f'{ctx.author} deleted all messages')

    async def move_user(self, ctx, user: discord.Member, channel: discord.VoiceChannel):

        if ctx.author.channel == channel:
            return await ctx.send('I am already in that channel')

        await ctx.author.move_to(channel)
        await ctx.send(f'**`{ctx.author}`**: Moved {user} to **{channel}**', delete_after=10)

    async def move_all(self, ctx, channel: discord.VoiceChannel):

        if ctx.author.channel == channel:
            return await ctx.send('I am already in that channel')

        await ctx.author.move_to(channel)
        await ctx.send(f'**`{ctx.author}`**: Moved everyone to **{channel}**', delete_after=10)

    async def kick(self, ctx, user: discord.Member,timeout: int):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return

        if voice_client.channel == user.voice.channel:
            await voice_client.move_to(None)
            await ctx.send(f'**`{ctx.author}`**: Kicked {user}', delete_after=10)
            await asyncio.sleep(timeout)
            await voice_client.move_to(user.voice.channel)
            await ctx.send(f'**`{ctx.author}`**: Moved {user} back to {user.voice.channel}', delete_after=10)
        else:
            await ctx.send(f'**`{ctx.author}`**: {user} is not in the same channel as the bot', delete_after=10)

    async def countuser(self, ctx):
        await ctx.send(f'**`{ctx.author}`**: {len(ctx.channel.members)} users in this channel', delete_after=10)

    async def countmessage(self, ctx):
        msg_list = await ctx.channel.history(limit=None).flatten()
        # with open("log.txt", "w") as f:
        #     for msg in msg_list:
        #         print(msg.content,
        #         msg.author,
        #         msg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        #         file=f)

        await ctx.send(f'**`{ctx.author}`**: {len(msg_list)} messages in this channel', delete_after=10)

    async def vol_c(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return
        
        await ctx.send(f'**`{ctx.author}`**: Volume is **{voice_client.source.volume * 100}%**', delete_after=10)

    async def autodisconnect(self, ctx):
        voice_client = get(self.bot.voice_clients, guild=ctx.guild)

        if voice_client == None or not voice_client.is_connected():
            await ctx.channel.send("Bot is not connected to vc", delete_after=10)
            return

        if asyncio.TimeoutError:   # if the bot is not playing or paused
            print(f'{ctx.author} disconnected from vc')
            del self.players[ctx.guild.id]
            await voice_client.disconnect()
            await ctx.send(f'**`{ctx.author}`**: Disconnected from vc', delete_after=10)



    async def button(self,ctx):
        await ctx.send( 
            components = [
                ActionRow(
                Button(
                    label = "Resume",
                    custom_id = "Resume",
                    style = ButtonStyle.blurple
                ),
                Button(
                    label = "Pause",
                    custom_id = "Pause",
                    style = ButtonStyle.green
                ),
                Button(
                    label = "Stop",
                    custom_id = "Stop",
                    style = ButtonStyle.gray
                ),Button(
                    label = "Help",
                    custom_id = "Help",
                    style = ButtonStyle.green
                )
                ),ActionRow(
                Button(
                    label = "Skip",
                    custom_id = "Skip",
                    style = ButtonStyle.green
                ),
                Button(
                    label = "List",
                    custom_id = "List",
                    style = ButtonStyle.grey
                ),
                Button(
                    label = "Now",
                    custom_id = "np",
                    style = ButtonStyle.blurple
                ),
                Button(
                    label = "Bot Disconnect",
                    custom_id = "Disconnect",
                    style = ButtonStyle.red
                )),ActionRow(
                Button(
                    label = "Bot Connect",
                    custom_id = "Connect",
                    style = ButtonStyle.green),
                Button(
                    label = "Volume Up",
                    custom_id = "Volume Up",
                    style = ButtonStyle.blurple
                ),
                Button(
                    label = "Volume Down",
                    custom_id = "Volume Down",
                    style = ButtonStyle.blurple
                )
                )
                ])
