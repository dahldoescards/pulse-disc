import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import asyncio
import json
import time
import random
import traceback
import re

load_dotenv()
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
BETA_TESTER_ROLE_ID = 1473848523660460113
ADMIN_ROLE_ID = 1473848200489336968

# Cloud Hosting: Look for a persistent data directory, default to current dir
DATA_DIR = os.getenv('DATA_DIR', '.')
TICKET_DATA_FILE = os.path.join(DATA_DIR, "ticket_counter.json")
LEVELS_FILE = os.path.join(DATA_DIR, "levels.json")

# Helper for ticket persistence
def get_next_ticket_id():
    if not os.path.exists(TICKET_DATA_FILE): data = {"count": 1}
    else:
        with open(TICKET_DATA_FILE, "r") as f:
            try: data = json.load(f)
            except: data = {"count": 1}
    curr = data.get("count", 1)
    data["count"] = curr + 1
    with open(TICKET_DATA_FILE, "w") as f: json.dump(data, f)
    return f"{curr:03}"

# Helper for leveling
def get_user_data():
    if not os.path.exists(LEVELS_FILE): return {}
    with open(LEVELS_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_user_data(data):
    # Ensure data directory exists
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEVELS_FILE, "w") as f: json.dump(data, f)

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- TASKS ---
@tasks.loop(minutes=10)
async def update_stats():
    guild = bot.get_guild(GUILD_ID)
    if not guild: return
    cat = discord.utils.get(guild.categories, name="📊 SERVER PULSE")
    if not cat: cat = await guild.create_category("📊 SERVER PULSE", position=0)
    
    # Member Count
    m_count = guild.member_count
    chan_m = discord.utils.get(cat.voice_channels, name=lambda x: "Total Members" in x)
    if not chan_m: await guild.create_voice_channel(f"Total Members: {m_count}", category=cat, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
    else: await chan_m.edit(name=f"Total Members: {m_count}")

    # Diamond Count
    d_role = discord.utils.get(guild.roles, name="The Diamond")
    if d_role:
        d_count = len(d_role.members)
        chan_d = discord.utils.get(cat.voice_channels, name=lambda x: "Diamond Members" in x)
        if not chan_d: await guild.create_voice_channel(f"Diamond Members: {d_count}", category=cat, overwrites={guild.default_role: discord.PermissionOverwrite(connect=False)})
        else: await chan_d.edit(name=f"Diamond Members: {d_count}")

@bot.event
async def on_ready():
    print(f'ProspectPulse Admin Bot live as {bot.user}')
    if not update_stats.is_running(): update_stats.start()

# --- ERROR HANDLING ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions) or isinstance(error, commands.MissingRole):
        await ctx.send("❌ **Access Denied**: This command is reserved for ProspectPulse Administrators.", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ **Not Found**: I couldn't find that member.", delete_after=5)
    else:
        print(f"Command error: {error}")

# --- SECURITY & XP ---
@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # Link Guard
    if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
        if not message.author.guild_permissions.administrator:
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}, invite links are restricted.", delete_after=5)
            return

    # XP Logic
    uid = str(message.author.id)
    now = time.time()
    if not hasattr(bot, 'xp_cooldowns'): bot.xp_cooldowns = {}
    if now - bot.xp_cooldowns.get(uid, 0) > 30:
        data = get_user_data()
        u = data.get(uid, {"xp": 0, "lvl": 1})
        u["xp"] += random.randint(15, 25)
        next_xp = u["lvl"] * 150
        if u["xp"] >= next_xp:
            u["lvl"] += 1
            u["xp"] = 0
            if u["lvl"] == 50:
                role = discord.utils.get(message.guild.roles, name="The Diamond")
                if role: await message.author.add_roles(role)
        data[uid] = u
        save_user_data(data)
        bot.xp_cooldowns[uid] = now

    await bot.process_commands(message)

# --- ADMIN COMMANDS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def purge(ctx, amount: int):
    """Bulk delete messages."""
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Purged {amount} messages.", delete_after=3)

@bot.command()
@commands.has_permissions(administrator=True)
async def whois(ctx, member: discord.Member):
    """Deep User Intelligence."""
    data = get_user_data()
    u_data = data.get(str(member.id), {"xp": 0, "lvl": 1})
    embed = discord.Embed(title=f"🕵️ Intelligence: {member.display_name}", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Account Age", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Standing", value=f"Level {u_data['lvl']} ({u_data['xp']} XP)", inline=False)
    roles = [r.name for r in member.roles if r.name != "@everyone"]
    embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles) if roles else "None", inline=False)
    await ctx.send(embed=embed)

# --- REACTION LOGIC ---
@bot.event
async def on_raw_reaction_add(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return
    channel = bot.get_channel(payload.channel_id)
    if not channel: return
    emoji = payload.emoji.name

    if channel.name == "server-rules" and emoji == "✅":
        role = guild.get_role(BETA_TESTER_ROLE_ID)
        if role: await member.add_roles(role)

    if channel.name == "notifications":
        role_map = {
            "📢": "Announcements Ping", "🛠️": "Dev Updates Ping", "📉": "Market Alerts Ping",
            "🦁": "AL East", "🎸": "AL Central", "🌵": "AL West",
            "🏛️": "NL East", "🐻": "NL Central", "🌉": "NL West",
            "🧪": "Statcast Junkie", "👁️": "Eye Test Scout", "💎": "High-End Chrome",
            "📦": "Bulk Prospector", "🏷️": "Grading Flipper"
        }
        if emoji in role_map:
            role = discord.utils.get(guild.roles, name=role_map[emoji])
            if role: await member.add_roles(role)

    if channel.name == "support-tickets" and emoji in {"👤", "💻", "❓"}:
        msg = await channel.fetch_message(payload.message_id)
        await msg.remove_reaction(emoji, member)
        num = get_next_ticket_id()
        t_cat = discord.utils.get(guild.categories, name="🎟️ SUPPORT HUB")
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False), member: discord.PermissionOverwrite(view_channel=True, send_messages=True)}
        t_chan = await guild.create_text_channel(f"ticket-{num}", category=t_cat, overwrites=overwrites)
        t_msg = await t_chan.send(f"🎟️ Ticket #{num}\nHi {member.mention}, please describe your issue. React with 🔒 to close.")
        await t_msg.add_reaction("🔒")

    if emoji == "🔒" and channel.category and channel.category.name == "🎟️ SUPPORT HUB":
        try: await channel.delete()
        except: pass

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    member = guild.get_member(payload.user_id)
    if not member: return
    channel = bot.get_channel(payload.channel_id)
    if channel and channel.name == "notifications":
        role_map = {
            "📢": "Announcements Ping", "🛠️": "Dev Updates Ping", "📉": "Market Alerts Ping",
            "🦁": "AL East", "🎸": "AL Central", "🌵": "AL West",
            "🏛️": "NL East", "🐻": "NL Central", "🌉": "NL West",
            "🧪": "Statcast Junkie", "👁️": "Eye Test Scout", "💎": "High-End Chrome",
            "📦": "Bulk Prospector", "🏷️": "Grading Flipper"
        }
        if payload.emoji.name in role_map:
            role = discord.utils.get(guild.roles, name=role_map[payload.emoji.name])
            if role: await member.remove_roles(role)

bot.run(TOKEN)
