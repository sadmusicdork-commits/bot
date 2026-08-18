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

# 6. AUTOMATIC STAFF LOG SYSTEM (Fixed absolute filter layout)
@bot.event
async def on_audit_log_entry_create(entry):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel:
        return

    # Wait a split second to make sure Discord registers log entry metadata
    await asyncio.sleep(0.5)

    # ABSOLUTE FILTER: If the user match your unique owner ID, skip logging completely
    if entry.user.id == SERVER_OWNER_ID:
        return

    # A. Tracks when a staff member updates someone's roles
    if entry.action == discord.AuditLogAction.member_role_update:
        target = entry.target
        moderator = entry.user
        
        # Look at what changed (Roles Added)
        changes = entry.after
        if hasattr(changes, 'roles'):
            for role in changes.roles:
                embed = discord.Embed(
                    title="🛡️ Staff Log: Member Roles Updated",
                    description=f"**User Who Received Role:** {target.mention} (`{target.id}`)\n**User Who Did The Action:** {moderator.mention}\n**Role Added:** {role.mention}",
                    color=discord.Color.green()
                )
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)
        
        # Double check for removed roles
        before_changes = entry.before
        if hasattr(before_changes, 'roles'):
            for role in before_changes.roles:
                embed = discord.Embed(
                    title="🛡️ Staff Log: Member Roles Updated",
                    description=f"**User Who Lost Role:** {target.mention} (`{target.id}`)\n**User Who Did The Action:** {moderator.mention}\n**Role Removed:** {role.mention}",
                    color=discord.Color.red()
                )
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)

    # B. Tracks when channel or server permissions are modified
    elif entry.action in [discord.AuditLogAction.channel_update, discord.AuditLogAction.channel_overwrite_update]:
        moderator = entry.user
        target_channel = entry.target
        embed = discord.Embed(
            title="⚙️ Staff Log: Permissions Changed",
            description=f"**User Who Did The Action:** {moderator.mention}\n**Channel:** {target_channel.mention if hasattr(target_channel, 'mention') else target_channel}\n**Action:** Modified channel overrides or settings.",
            color=discord.Color.orange()
        )
        embed.set_footer(text="/admire")
        await channel.send(embed=embed)

# 7. Gives the role even if the message isn't cached in memory
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    emoji_str = str(payload.emoji)
    
    if emoji_str in EMOJI_TO_ROLE:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return

        role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
        
        if role and member:
            if emoji_str == CUSTOM_EMOJI_18_PLUS:
                opposite = guild.get_role(ROLE_18_MINUS)
                if opposite and opposite in member.roles:
                    await member.remove_roles(opposite)
            elif emoji_str == CUSTOM_EMOJI_18_MINUS:
                opposite = guild.get_role(ROLE_18_PLUS)
                if opposite and opposite in member.roles:
                    await member.remove_roles(opposite)

            await member.add_roles(role)

# 8. Removes the role even if the message isn't cached in memory
@bot.event
async def on_raw_reaction_remove(payload):
    emoji_str = str(payload.emoji)
    
    if emoji_str in EMOJI_TO_ROLE:
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return

        role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
        
        if role and member:
            await member.remove_roles(role)

keep_alive()
rules.add_rules_command(bot)
bot.run(os.environ.get("DISCORD_TOKEN"))
