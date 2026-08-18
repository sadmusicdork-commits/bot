import os
import discord
from discord.ext import commands, tasks
from threading import Thread
from flask import Flask
import rules
import urllib.request
import asyncio

# --- RENDER AWAKE LOOP FIX ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is online 24/7!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# 1. Background settings to let the bot read messages, members, and moderation logs
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.moderation = True  # Allows the bot to read server audit logs

bot = commands.Bot(command_prefix="!", intents=intents)

# 2. YOUR DISCORD SERVER ROLE IDS
ROLE_18_PLUS = 1538782704873644132    
ROLE_18_MINUS = 1538782755482107954   
ROLE_MALE = 1538782632052002906       
ROLE_FEMALE = 1538782590121541712     

# 3. YOUR CUSTOM EMOJI STRINGS
CUSTOM_EMOJI_18_PLUS = "<:adult:1538799437634084995>"
CUSTOM_EMOJI_18_MINUS = "<:minor:1538799431594287104>"
CUSTOM_EMOJI_MALE = "♂️"
CUSTOM_EMOJI_FEMALE = "♀️"

EMOJI_TO_ROLE = {
    CUSTOM_EMOJI_18_PLUS: ROLE_18_PLUS,
    CUSTOM_EMOJI_18_MINUS: ROLE_18_MINUS,
    CUSTOM_EMOJI_MALE: ROLE_MALE,
    CUSTOM_EMOJI_FEMALE: ROLE_FEMALE
}

# 🛡️ SYSTEM INTEGRATION CHANNELS AND FILTERS
LOG_CHANNEL_ID = 1538242821075632328  

# 👑 YOUR HARDCODED PERSONAL DISCORD USER ID SAVED BELOW
SERVER_OWNER_ID = 1232481355309387857  

# Heartbeat loop that pings itself every 5 minutes to stay awake
@tasks.loop(minutes=5)
async def self_ping():
    try:
        urllib.request.urlopen("http://127.0.0", timeout=10)
        print("Heartbeat ping sent successfully! Bot staying awake.")
    except Exception as e:
        print(f"Ping notice: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}! Your bot is online and ready.")
    if not self_ping.is_running():
        self_ping.start()

# 4. Command to send the clean reaction roles embed message
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    embed = discord.Embed(
        title="Role Selection",
        description="Pick your roles to personalize your experience within the server.",
        color=discord.Color.dark_theme()
    )
    embed.add_field(name="Age", value="• **18+**\n• **18-**", inline=False)
    embed.add_field(name="Gender", value="♂️ **Male**\n♀️ **Female**", inline=False)
    embed.add_field(
        name="Information", 
        value="• Choose **one** age role.\n• Gender roles are optional.\n• Roles can be changed at any time.", 
        inline=False
    )
    embed.set_footer(text="/admire • Role Selection")

    msg = await ctx.send(embed=embed)
    for emoji in EMOJI_TO_ROLE.keys():
        await msg.add_reaction(emoji)

# 5. AUTOMATIC CHAT RESPONDER
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if "pic perms" in message.content.lower():
        embed = discord.Embed(
            description="rep **/admire** in status or **boost** for pic perms",
            color=discord.Color.dark_theme()
        )
        embed.set_footer(text="꒰১ ໒꒱ • Media Access")
        await message.reply(embed=embed)

    await bot.process_commands(message)

# 6. CONNECTED PROFILE ALT MATCH SCANNER (EXACT REQUESTED FIELDS)
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    # A. Check for cloned profile images matching users already in the server
    if member.avatar:
        new_avatar_key = member.avatar.key
        
        for existing_member in member.guild.members:
            if existing_member.id == member.id or not existing_member.avatar:
                continue
                
            if existing_member.avatar.key == new_avatar_key:
                embed = discord.Embed(
                    title="⚠️ Security Alert: Connected Alt Account Logged",
                    description=f"**User who joined:** {member.mention} (`{member.id}`)\n"
                                f"**Suspected alt:** {existing_member.mention} (`{existing_member.id}`)\n\n"
                                f"**Match Signature:** Identical avatar data assets detected.",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)
                return

    # B. Secondary Check: Check for username clone pattern similarities 
    for existing_member in member.guild.members:
        if existing_member.id == member.id:
            continue
        if len(member.name) > 4 and member.name.lower() in existing_member.name.lower():
            embed = discord.Embed(
                title="⚠️ Security Alert: Connected Alt Account Logged",
                description=f"**User who joined:** {member.mention} (`{member.id}`)\n"
                            f"**Suspected alt:** {existing_member.mention} (`{existing_member.id}`)\n\n"
                            f"**Match Signature:** Cloned username character string similarity caught.",
                color=discord.Color.orange()
            )
            embed.set_footer(text="/admire")
            await channel.send(embed=embed)
            return

# 7. AUTOMATIC STAFF LOG SYSTEM (COMPLETELY DYNAMIC LABELS PER EVENT)
@bot.event
async def on_audit_log_entry_create(entry):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    await asyncio.sleep(0.5)

    if entry.user.id == bot.user.id or entry.user.id == SERVER_OWNER_ID:
        return

    moderator = entry.user
    target = entry.target
    reason = entry.reason if entry.reason else "No reason provided."

    # BAN LOGS
    if entry.action == discord.AuditLogAction.ban:
        embed = discord.Embed(
            title="🔨 Staff Log: Member Banned",
            description=f"**User Who Did The Action:** {moderator.mention}\n**User Who Was Banned:** {target.mention} (`{target.id}`)\n**Reason:** {reason}",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="/admire")
        await channel.send(embed=embed)

    # KICK LOGS
    elif entry.action == discord.AuditLogAction.kick:
        embed = discord.Embed(
            title="👢 Staff Log: Member Kicked",
            description=f"**User Who Did The Action:** {moderator.mention}\n**User Who Was Kicked:** {target.mention} (`{target.id}`)\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        embed.set_footer(text="/admire")
        await channel.send(embed=embed)

    # TIMEOUT LOGS
    elif entry.action == discord.AuditLogAction.member_update:
        changes = entry.after
        if hasattr(changes, 'timed_out_until') and changes.timed_out_until is not None:
            embed = discord.Embed(
                title="🔇 Staff Log: Member Muted (Timeout)",
                description=f"**User Who Did The Action:** {moderator.mention}\n**User Who Was Muted:** {target.mention} (`{target.id}`)\n**Muted Until:** {changes.timed_out_until.strftime('%Y-%m-%d %H:%M:%S')} UTC",
                color=discord.Color.orange()
            )
            embed.set_footer(text="/admire")
            await channel.send(embed=embed)

    # ROLE LOGS
    elif entry.action == discord.AuditLogAction.member_role_update:
        if hasattr(entry.after, 'roles'):
            for role in entry.after.roles:
                embed = discord.Embed(
                    title="🛡️ Staff Log: Role Assigned",
                    description=f"**User Who Did The Action:** {moderator.mention}\n**User Who Received Role:** {target.mention} (`{target.id}`)\n**Role Added:** {role.mention}",
                    color=discord.Color.green()
                )
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)
        if hasattr(entry.before, 'roles'):
            for role in entry.before.roles:
                embed = discord.Embed(
                    title="🛡️ Staff Log: Role Removed",
                    description=f"**User Who Did The Action:** {moderator.mention}\n**User Who Lost Role:** {target.mention} (`{target.id}`)\n**Role Removed:** {role.mention}",
                    color=discord.Color.red()
                )
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)

    # CHANNEL PERMISSION OVERWRITE LOGS (DYNAMIC SETTING PERMISSIONS OPERATIONAL LABELS)
    elif entry.action in [discord.AuditLogAction.channel_overwrite_create, discord.AuditLogAction.channel_overwrite_update, discord.AuditLogAction.channel_overwrite_delete]:
        target_channel = entry.target
        
        if entry.action == discord.AuditLogAction.channel_overwrite_create:
            label_text = "**Permission added:** New role/user override locks activated."
            card_title = "⚙️ Staff Log: Channel Permission Added"
            card_color = discord.Color.green()
        elif entry.action == discord.AuditLogAction.channel_overwrite_delete:
            label_text = "**Permission removed:** Role/user override clears completely deleted."
            card_title = "⚙️ Staff Log: Channel Permission Removed"
            card_color = discord.Color.red()
        else:
            label_text = "**Permission changed:** View channel, text message, or attachment toggle flags updated."
            card_title = "⚙️ Staff Log: Channel Permission Changed"
            card_color = discord.Color.orange()

        embed = discord.Embed(
            title=card_title,
            description=f"**User Who Did The Action:** {moderator.mention}\n**Channel Modified:** {target_channel.mention if hasattr(target_channel, 'mention') else target_channel}\n{label_text}",
            color=card_color
        )
        embed.set_footer(text="/admire")
        await channel.send(embed=embed)

# 8. Gives the role even if the message isn't cached in memory
@bot.event 
async def on_raw_reaction_add(payload):
if payload.user_id == bot.user.id:
return
emoji_str = str(payload.emoji)
if emoji_str in EMOJI_TO_ROLE:
guild = bot.get_guild(payload.guild_id)
if not guild: return
member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
if role and member:
if emoji_str == CUSTOM_EMOJI_18_PLUS:
opposite = guild.get_role(ROLE_18_MINUS)
if opposite and opposite in member.roles: await member.remove_roles(opposite)
elif emoji_str == CUSTOM_EMOJI_18_MINUS:
opposite = guild.get_role(ROLE_18_PLUS)
if opposite and opposite in member.roles: await member.remove_roles(opposite)
await member.add_roles(role)

9. Removes the role even if the message isn't cached in memory
@bot.event
async def on_raw_reaction_remove(payload):
emoji_str = str(payload.emoji)
if emoji_str in EMOJI_TO_ROLE:
guild = bot.get_guild(payload.guild_id)
if not guild: return
member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
if role and member: await member.remove_roles(role)
keep_alive()
rules.add_rules_command(bot)
bot.run(os.environ.get("DISCORD_TOKEN"))
