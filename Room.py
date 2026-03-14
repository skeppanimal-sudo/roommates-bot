import discord
from discord.ext import commands, tasks
import json
import os
import aiohttp
import matplotlib.pyplot as plt
import datetime

TOKEN = os.getenv("TOKEN")  # Railway token variable
UNIVERSE_ID = 9798063312  # PUT YOUR ROBLOX UNIVERSE ID HERE

MOD_APP_CHANNEL = 1480025962375680182
TESTER_APP_CHANNEL = 1479230179242152019
CREATOR_APP_CHANNEL = 1482388933022056589

DATA_FILE = "invites.json"
CCU_FILE = "ccu_data.json"
PANEL_FILE = "panel.json"

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.invites = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

invite_cache = {}
panel_message = None


# ---------- FILE SETUP ----------

def ensure_file(file, default):
    if not os.path.exists(file):
        with open(file, "w") as f:
            json.dump(default, f)

ensure_file(DATA_FILE, {})
ensure_file(CCU_FILE, {"hours":[0]*24})
ensure_file(PANEL_FILE, {})


def load_json(file):
    with open(file, "r") as f:
        return json.load(f)


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


# ---------- ROBLOX CCU ----------

async def get_ccu():
    url = f"https://games.roblox.com/v1/games?universeIds={UNIVERSE_ID}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            data = await r.json()
            return data["data"][0]["playing"]


# ---------- GRAPH ----------

def generate_chart():

    data = load_json(CCU_FILE)

    hours = list(range(24))
    values = data["hours"]

    plt.figure(figsize=(9,3))
    plt.bar(hours, values)

    plt.xlabel("Hour of Day")
    plt.ylabel("Players")
    plt.title("Roommates Player Count Today")

    plt.xticks(hours)

    plt.tight_layout()

    plt.savefig("ccu.png")
    plt.close()


# ---------- EMBED ----------

def create_embed():

    embed = discord.Embed(
        description=(
            "**__RoomMates Frequently Asked Questions__**\n\n"

            "**How do I become a Moderator?**\n"
            f"> Go apply over in <#{MOD_APP_CHANNEL}> whenever they next open up.\n\n"

            "**How do I become a Tester?**\n"
            f"> Go apply over in <#{TESTER_APP_CHANNEL}> whenever they open up usually every few months.\n\n"

            "**How do I become a Content Creator?**\n"
            f"> Go apply over in <#{CREATOR_APP_CHANNEL}> these applications are always open and we actively pick new creators.\n\n"

            "**How do I level up?**\n"
            "> To level up actively participate in conversations.\n\n"

            "**How do I check the player count in roommates?**\n"
            "> View the chart below it updates every 30 seconds."
        ),
        color=discord.Color.from_rgb(255,255,255)
    )

    embed.set_image(url="attachment://ccu.png")

    return embed


# ---------- CCU UPDATE LOOP ----------

@tasks.loop(seconds=30)
async def update_chart():

    global panel_message

    ccu = await get_ccu()

    data = load_json(CCU_FILE)

    hour = datetime.datetime.now().hour

    data["hours"][hour] = max(data["hours"][hour], ccu)

    save_json(CCU_FILE, data)

    generate_chart()

    if panel_message:

        embed = create_embed()
        file = discord.File("ccu.png", filename="ccu.png")

        await panel_message.edit(embed=embed, attachments=[file])


# ---------- EVENTS ----------

@bot.event
async def on_ready():

    global panel_message

    print(f"Logged in as {bot.user}")

    await bot.change_presence(status=discord.Status.idle)

    for guild in bot.guilds:
        invite_cache[guild.id] = await guild.invites()

    await bot.tree.sync()

    panel_data = load_json(PANEL_FILE)

    if panel_data:
        channel = bot.get_channel(panel_data["channel"])
        if channel:
            try:
                panel_message = await channel.fetch_message(panel_data["message"])
            except:
                pass

    generate_chart()

    update_chart.start()


@bot.event
async def on_member_join(member):

    guild = member.guild

    new_invites = await guild.invites()
    old_invites = invite_cache.get(guild.id)

    data = load_json(DATA_FILE)

    if old_invites is None:
        invite_cache[guild.id] = new_invites
        return

    for invite in new_invites:
        for old in old_invites:

            if invite.code == old.code and invite.uses > old.uses:

                inviter = str(invite.inviter.id)

                if inviter not in data:
                    data[inviter] = 0

                data[inviter] += 1

                save_json(DATA_FILE, data)

    invite_cache[guild.id] = new_invites


# ---------- INVITES COMMAND ----------

@bot.tree.command(name="invites", description="Check invite count")
async def invites(interaction: discord.Interaction, user: discord.Member = None):

    data = load_json(DATA_FILE)

    target = user if user else interaction.user

    invites = data.get(str(target.id), 0)

    embed = discord.Embed(
        description=f"**{target.display_name}**\nYou currently have **{invites} invites**.",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="Invites",
        value=f"**{invites}** regular\n**0** left",
        inline=False
    )

    embed.set_thumbnail(url=target.display_avatar.url)

    await interaction.response.send_message(embed=embed)


# ---------- FAQ PANEL ----------

@bot.tree.command(name="faqpanel", description="Send FAQ panel")
async def faqpanel(interaction: discord.Interaction):

    global panel_message

    await interaction.response.send_message("Panel created.", ephemeral=True)

    generate_chart()

    embed = create_embed()
    file = discord.File("ccu.png", filename="ccu.png")

    msg = await interaction.channel.send(embed=embed, file=file)

    panel_message = msg

    save_json(PANEL_FILE, {
        "channel": msg.channel.id,
        "message": msg.id
    })


bot.run(TOKEN)