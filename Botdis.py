import discord
from discord.utils import get
from discord.ext import commands
from song import songAPI

# Token variable for the bot, replace with your own
Token = ''

# Creating the bot instance with command prefix "!" and disabling the default help command
bot = commands.Bot(command_prefix='!',help_command=None)

# Creating an instance of the custom songAPI class
songsInstance = songAPI()

# Event that triggers when the bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    print("------")
    await bot.change_presence(activity=discord.Game(name="!help"))

# Command for testing bot's latency
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms", delete_after=5)

# Command for testing bot's response
@bot.command()
async def test(ctx, *, par):
    await ctx.channel.send("{}".format(par), delete_after=5)

# Command for displaying all available commands
@bot.command() 
async def help(ctx):
    emBed = discord.Embed(title="Bot help", description="All available bot commands", color=0x42f5a7)
    emBed.add_field(name="!help", value="Get help command", inline=False)
    emBed.add_field(name="!test พิมพ์ไรก็ได้", value="Respond message that you've send", inline=False)
    emBed.add_field(name="!play ชื่อหรือลิ้งค์เพลง", value="play music", inline=False)
    emBed.add_field(name="!stop", value="stop music", inline=False)
    emBed.add_field(name="!resume", value="resume music", inline=False)
    emBed.add_field(name="!pause", value="pause music", inline=False)
    emBed.add_field(name="!skip", value="skip music", inline=False)
    emBed.add_field(name="!List", value="List msic", inline=False)
    emBed.add_field(name="!np", value="Now music", inline=False)
    emBed.add_field(name="!vol ค่าความดัง", value="change volume", inline=False)
    emBed.add_field(name="!leave", value="Bot leave", inline=False)

    await ctx.channel.send(embed=emBed)

# Command for generating buttons
@bot.command()
async def button(ctx):
    # Calling the button method from the songAPI class
    await songsInstance.button(ctx)

#Command for playing music
@bot.command() 
async def play(ctx,* ,search: str):
    # Calling the play method from the songAPI class
    await songsInstance.play(ctx, search)
    # Generating buttons after music starts playing
    await songsInstance.button(ctx)

#Event for handling the "Resume" button click
@bot.on_click(custom_id='Resume')
async def resume(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:Resume")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return    
    if voice_client.is_paused():
        voice_client.resume()
        an_embed = discord.Embed(title='Music playing', description='Resume', color=discord.Color.random())
        await i.respond(embed=an_embed, delete_after=5)
    elif voice_client.is_playing():
        await i.channel.send("Bot is already playing", delete_after=5)
        return
    else:
        await i.channel.send("Bot is not playing", delete_after=5)
        return
    
#Event for handling the "Pause" button click
@bot.on_click(custom_id='Pause')
async def pause(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:Pause")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return  
    if voice_client.is_playing():
        voice_client.pause()
        an_embed = discord.Embed(title='Music playing', description='Pause', color=discord.Color.random())
        await i.respond(embed=an_embed, delete_after=5)
    elif voice_client.is_paused():
        await i.channel.send("Bot is already paused", delete_after=5)
        return
    else:
        await i.channel.send("Bot is not playing", delete_after=5)
        return
    
#Event for handling the "Stop" button click
@bot.on_click(custom_id='Stop')
async def stop(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:stop")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return  
    if voice_client.is_playing():
        voice_client.stop()
        an_embed = discord.Embed(title='Music playing', description='Stop', color=discord.Color.random())
        await i.respond(embed=an_embed, delete_after=5)
    elif voice_client.is_paused():
        await i.channel.send("Bot is already stopped", delete_after=5)
        return
    else:
        await i.channel.send("Bot is not playing", delete_after=5)
        return
    
#Event for handling the "Skip" button click
@bot.on_click(custom_id='Skip')
async def skip(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:skip")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return  
    if voice_client.is_playing():
        voice_client.stop()
        an_embed = discord.Embed(title='Music playing', description='{} : Skip'.format(i.member), color=discord.Color.random())
        await i.respond(embed=an_embed, delete_after=5)  
    elif voice_client.is_paused():
        await i.channel.send("Bot is already stopped", delete_after=5)
        return
    else:
        await i.channel.send("Bot is not playing", delete_after=5)
        return
    
#Event for handling the "List" button click
@bot.on_click(custom_id='List')
async def list(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:list")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return  
    await songsInstance.queueList(i.channel)
    
#Event for handling the "Now playing" button click
@bot.on_click(custom_id='np')
async def np(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:np")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return  
    await songsInstance.now_playing_(i.channel)
    
#Event for handling the "Disconnect" button click
@bot.on_click(custom_id='Disconnect')
async def Disconnect(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:Disconnect")
    voice_client = get(bot.voice_clients, guild=i.guild)
    if voice_client == None:
        await i.channel.send("Bot is not connected to vc", delete_after=5)
        return  

    await voice_client.disconnect()
    await i.respond("Bot Disconnect", delete_after=5)
    
#Event for handling the "help" button click
@bot.on_click(custom_id='Help')
async def Help(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:help") 
    emBed = discord.Embed(title="Bot help", description="All available bot commands", color=0x42f5a7)
    emBed.add_field(name="!help", value="Get help command", inline=True)
    emBed.add_field(name="!test พิมพ์ไรก็ได้", value="Respond message that you've send", inline=True)
    emBed.add_field(name="!play ชื่อหรือลิ้งค์เพลง", value="play music", inline=True)
    emBed.add_field(name="!stop", value="stop music", inline=True)
    emBed.add_field(name="!resume", value="resume music", inline=True)
    emBed.add_field(name="!pause", value="pause music", inline=True)
    emBed.add_field(name="!skip", value="skip music", inline=True)
    emBed.add_field(name="!List", value="List msic", inline=True)
    emBed.add_field(name="!np", value="Now music", inline=True)
    emBed.add_field(name="!vol ค่าความดัง", value="change volume", inline=True)
    emBed.add_field(name="!leave", value="Bot leave", inline=False)

    await i.respond(embed=emBed, delete_after=20)

#Event for handling the "Connect" button click
@bot.on_click(custom_id='Connect')
async def Connect(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:Connect")
    voice_client = get(bot.voice_clients, guild=i.guild)

    if voice_client == None:
        voice_client = await i.member.voice.channel.connect()
        await i.respond("Bot Connect", delete_after=5)
    else:
        await i.respond("Bot is already connected to vc", delete_after=5)

#Event for handling the "Volume Up" button click
@bot.on_click(custom_id='Volume Up')
async def Volume_Up(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:Volume UP")
    voice_client = get(bot.voice_clients, guild=i.guild)

    if voice_client == None or not voice_client.is_connected():
        await i.channel.send("Bot is not connected to vc", delete_after=10)
        return

    if voice_client.source.volume >= 1:
        return await i.send('Volume is already at 100%', delete_after=10)
    elif voice_client.source.volume <= 0:
        return await i.send('Volume is already at 0%', delete_after=10)
    
    if voice_client.is_playing() or voice_client.is_paused() or voice_client.is_stopped():
        voice_client.source.volume += 0.05
        await i.respond('Volume is now at {}%'.format(int(voice_client.source.volume * 100)), delete_after=10)
    else:
        await i.respond('No music is playing', delete_after=10)

#Event for handling the "Volume Down" button click
@bot.on_click(custom_id='Volume Down')
async def Volume_Down(i: discord.Interaction, button):
    await i.defer()
    print(f"{i.member}:Volume DOWN")
    voice_client = get(bot.voice_clients, guild=i.guild)

    if voice_client == None or not voice_client.is_connected():
        await i.channel.send("Bot is not connected to vc", delete_after=10)
        return
    
    if voice_client.source.volume <= 0:
        return await i.send('Volume is already at 0%', delete_after=10)
    elif voice_client.source.volume >= 1:
        return await i.send('Volume is already at 100%', delete_after=10)

    if voice_client.is_playing() or voice_client.is_paused() or voice_client.is_stopped():
        voice_client.source.volume -= 0.05
        await i.respond('Volume is now at {}%'.format(int(voice_client.source.volume * 100)), delete_after=10)
    else:
        await i.respond('No music is playing', delete_after=10)


@bot.command()
async def stop(ctx):
    await songsInstance.stop(ctx)

@bot.command()
async def pause(ctx):
    await songsInstance.pause(ctx)

@bot.command()
async def resume(ctx):
    await songsInstance.resume(ctx)

@bot.command()
async def leave(ctx):
    await songsInstance.leave(ctx)

@bot.command()
async def List(ctx):
    await songsInstance.queueList(ctx)

@bot.command()
async def skip(ctx):
    await songsInstance.skip(ctx) 

@bot.command()
async def np(ctx):
    await songsInstance.now_playing_(ctx) 

@bot.command()
async def vol(ctx, *, vol: int):
    await songsInstance.volume(ctx, vol)

@bot.command()
async def move(ctx, *, channel: discord.VoiceChannel):
    await songsInstance.move(ctx, channel)

@bot.command()
async def remove(ctx, *, index: int):
    await songsInstance.deletemessage(ctx, index)

@bot.command()
async def removeall(ctx):
    await songsInstance.deleteall(ctx)

@bot.command()
async def move_user(ctx, member: discord.Member,*, channel: discord.VoiceChannel):
    await songsInstance.move_user(ctx, member, channel)

@bot.command()
async def move_all(ctx, channel: discord.VoiceChannel):
    await songsInstance.move_all(ctx, channel)

@bot.command()
async def countmess(ctx):
    await songsInstance.countmessage(ctx)

@bot.command()
async def countuser(ctx):
    await songsInstance.countuser(ctx)

@bot.command()
async def volc(ctx):
    await songsInstance.vol_c(ctx)

#Running the bot
if __name__ == '__main__':
    try:
        print('Start')
        bot.run(Token)
        print('Finish')
    except KeyboardInterrupt:
        print('exit')
