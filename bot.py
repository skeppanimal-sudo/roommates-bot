import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import requests
import matplotlib.pyplot as plt
from datetime import datetime

TOKEN = os.getenv("TOKEN")

MOD_APP = 1480025962375680182
TESTER_APP = 1479230179242152019
CREATOR_APP = 1482388933022056589
INVITE_CHANNEL = 1476717008010870813

ROBLOX_GAME_ID = 9798063312  # PUT YOUR ROBLOX GAME ID HERE

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

invite_cache = {}
ccu_data = {}

if not os.path.exists("invites.json"):
    with open("invites.json","w") as f:
        json.dump({},f)

if not os.path.exists("ccu_data.json"):
    with open("ccu_data.json","w") as f:
        json.dump({},f)


def load_invites():
    with open("invites.json") as f:
        return json.load(f)


def save_invites(data):
    with open("invites.json","w") as f:
        json.dump(data,f,indent=4)


def load_ccu():
    with open("ccu_data.json") as f:
        return json.load(f)


def save_ccu(data):
    with open("ccu_data.json","w") as f:
        json.dump(data,f,indent=4)


def get_ccu():
    try:
        url=f"https://games.roblox.com/v1/games?universeIds={ROBLOX_GAME_ID}"
        r=requests.get(url).json()
        return r["data"][0]["playing"]
    except:
        return 0


def make_chart():
    data=load_ccu()
    hours=list(data.keys())
    values=list(data.values())

    plt.clf()
    plt.bar(hours,values)
    plt.xlabel("Hour")
    plt.ylabel("Players")
    plt.title("Roommates CCU Today")
    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig("ccu_chart.png")


@tasks.loop(seconds=30)
async def update_ccu():

    ccu=get_ccu()

    now=datetime.now().strftime("%H")

    data=load_ccu()
    data[now]=ccu

    save_ccu(data)

    make_chart()

    channel=bot.get_channel(INVITE_CHANNEL)

    if channel:

        embed=discord.Embed(
            title="RoomMates Frequently Asked Questions",
            color=discord.Color.from_rgb(255,255,255)
        )

        embed.add_field(
            name="How do I become a Moderator?",
            value=f"Go apply in <#{MOD_APP}> whenever they open.",
            inline=False
        )

        embed.add_field(
            name="How do I become a Tester?",
            value=f"Go apply in <#{TESTER_APP}> whenever they open.",
            inline=False
        )

        embed.add_field(
            name="How do I become a Content Creator?",
            value=f"Apply in <#{CREATOR_APP}>. These are always open.",
            inline=False
        )

        embed.add_field(
            name="How do I level up?",
            value="Participate in conversations.",
            inline=False
        )

        embed.add_field(
            name="How do I check the player count in roommates?",
            value="View the chart below it updates every 30 seconds.",
            inline=False
        )

        file=discord.File("ccu_chart.png")

        embed.set_image(url="attachment://ccu_chart.png")

        try:
            await channel.purge(limit=1)
        except:
            pass

        await channel.send(embed=embed,file=file)


@bot.event
async def on_ready():

    await bot.change_presence(status=discord.Status.idle)

    for guild in bot.guilds:
        invites=await guild.invites()
        invite_cache[guild.id]={i.code:i.uses for i in invites}

    await bot.tree.sync()

    update_ccu.start()

    print(f"Logged in as {bot.user}")


@bot.event
async def on_member_join(member):

    guild=member.guild
    invites=await guild.invites()

    used=None

    for invite in invites:
        if invite.uses > invite_cache[guild.id].get(invite.code,0):
            used=invite
            break

    invite_cache[guild.id]={i.code:i.uses for i in invites}

    data=load_invites()

    if used and used.inviter:

        inviter=str(used.inviter.id)

        if inviter not in data:
            data[inviter]=0

        data[inviter]+=1

        save_invites(data)

        channel=bot.get_channel(INVITE_CHANNEL)

        if channel:
            await channel.send(
                f"{member.mention} has been invited by {used.inviter.mention} he now has {data[inviter]} invites"
            )


@bot.tree.command(name="invites",description="Check invite count")
@app_commands.describe(user="User to check")
async def invites(interaction:discord.Interaction,user:discord.Member=None):

    if user is None:
        user=interaction.user

    data=load_invites()

    count=data.get(str(user.id),0)

    embed=discord.Embed(
        title=user.name,
        description=f"You currently have **{count} invites.**",
        color=discord.Color.from_rgb(255,255,255)
    )

    embed.set_thumbnail(url=user.display_avatar.url)

    embed.add_field(name="Invites",value=f"Regular: {count}\nLeft: 0")

    embed.set_footer(text=f"Requested by {interaction.user}")

    await interaction.response.send_message(embed=embed,ephemeral=False)


bot.run(TOKEN)
