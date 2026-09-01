import os
import discord
from discord.ext import commands, tasks
from threading import Thread
from flask import Flask
import rules
import urllib.request
import asyncio
import re
import random
import json
from datetime import timedelta

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

# NOTE: single prefix — every command below (including !vc, !ping, etc.) uses "!"
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. YOUR DISCORD SERVER ROLE IDS
ROLE_18_PLUS = 1538782704873644132    
ROLE_18_MINUS = 1538782755482107954   
ROLE_MALE = 1538782632052002906       
ROLE_FEMALE = 1538782590121541712     

# 3. YOUR CUSTOM REACTION ROLE EMOJI STRINGS
CUSTOM_EMOJI_18_PLUS = "<:adult:1538799437634084995>"
CUSTOM_EMOJI_18_MINUS = "<:minor:1538799431594287104>"
CUSTOM_EMOJI_MALE = "♂️"
CUSTOM_EMOJI_FEMALE = "♀️"

# 🎛️ YOUR CUSTOM EXCLUSIVE VOICE PANEL EMOJI STRINGS INSTALLED
VC_EMOJI_LOCK = "<:lock:1539573895818911764>"
VC_EMOJI_UNLOCK = "<:unlock:1539573922192822322>"
VC_EMOJI_GHOST = "<:ghost:1539573948746825739>"
VC_EMOJI_REVEAL = "<:unghost:1539573974151860264>"
VC_EMOJI_CLAIM = "<:claim:1539573996520079440>"
VC_EMOJI_DISCONNECT = "<:disconnect:1539574024454148156>"
VC_EMOJI_ACTIVITY = "<:activity:1539574045966737458>"
VC_EMOJI_INFO = "<:info:1539574074832064602>"
VC_EMOJI_PLUS = "<:increase:1539574103047016478>"
VC_EMOJI_MINUS = "<:decrease:1539574123351515256>"

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

# 🔐 PERSISTENT SECURITY DATA (whitelist, blacklist, jail channel, anti-nuke toggle)
DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"whitelist": [], "blacklist": [], "jail_channel": None, "antinuke": True}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(bot_data, f, indent=2)

bot_data = load_data()

# In-memory anti-nuke tracking (resets on restart) and snipe cache
recent_actions = {}  # user_id -> list of recent destructive-action timestamps
DESTRUCTIVE_ACTIONS = {
    discord.AuditLogAction.channel_delete,
    discord.AuditLogAction.channel_create,
    discord.AuditLogAction.role_delete,
    discord.AuditLogAction.ban,
    discord.AuditLogAction.webhook_create,
}
ANTINUKE_THRESHOLD = 3       # number of actions...
ANTINUKE_WINDOW_SECONDS = 10 # ...within this many seconds triggers a response

deleted_messages = {}  # channel_id -> list of {"content", "author", "time"} for !snipe / !cs

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
    # Re-registers the voicepanel buttons as a persistent view so they keep
    # working on old panel messages after every bot restart/redeploy.
    if not getattr(bot, "_persistent_views_added", False):
        bot.add_view(VoiceControlView())
        bot._persistent_views_added = True

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
    embed.set_footer(text="꒰১ ໒꒱ • Role Selection")

    msg = await ctx.send(embed=embed)
    for emoji in EMOJI_TO_ROLE.keys():
        await msg.add_reaction(emoji)

# 5. AUTOMATIC CHAT RESPONDER
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

# 🖥️ VOICE PANEL BUTTONS VIEW DEFINITION WITH INTERACTIVE LAYOUTS
class VoiceControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Keeps button interactions active permanently

    async def get_user_vc(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be connected to a voice channel to control it!", ephemeral=True)
            return None
        return interaction.user.voice.channel

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_LOCK, custom_id="vc_lock", row=0)
    async def lock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.connect = False
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message(f"🔒 Locked voice channel: {channel.mention}", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_UNLOCK, custom_id="vc_unlock", row=0)
    async def unlock_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.connect = True
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message(f"🔓 Unlocked voice channel: {channel.mention}", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_GHOST, custom_id="vc_ghost", row=0)
    async def ghost_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.view_channel = False
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message(f"👻 Hidden voice channel: {channel.mention}", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_REVEAL, custom_id="vc_reveal", row=0)
    async def reveal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            overwrite = channel.overwrites_for(interaction.guild.default_role)
            overwrite.view_channel = True
            await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
            await interaction.response.send_message(f"👁️ Revealed voice channel: {channel.mention}", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_CLAIM, custom_id="vc_claim", row=0)
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("👑 Checking channel ownership privileges...", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_DISCONNECT, custom_id="vc_disconnect", row=1)
    async def disconnect_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚫 Usage: Disconnect active profiles from your voice lounge.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_ACTIVITY, custom_id="vc_activity", row=1)
    async def activity_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎮 Discord activities session initialized.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_INFO, custom_id="vc_info", row=1)
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            await interaction.response.send_message(f"ℹ️ **Channel Info:** Name: `{channel.name}` | Limit: `{channel.user_limit if channel.user_limit else 'Unlimited'}` members.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_PLUS, custom_id="vc_increase", row=1)
    async def increase_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            new_limit = (channel.user_limit + 1) if channel.user_limit < 99 else 99
            await channel.edit(user_limit=new_limit)
            await interaction.response.send_message(f"➕ User limit increased to `{new_limit}`.", ephemeral=True)

    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji=VC_EMOJI_MINUS, custom_id="vc_decrease", row=1)
    async def decrease_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await self.get_user_vc(interaction)
        if channel:
            new_limit = (channel.user_limit - 1) if channel.user_limit > 1 else 1
            await channel.edit(user_limit=new_limit)
            await interaction.response.send_message(f"➖ User limit decreased to `{new_limit}`.", ephemeral=True)

# 📜 VOICE PANEL TRIGGER COMMAND — BUTTON INTERFACE
# Triggered by !voicepanel. Kept fully separate from the "!vc" text command group below.
@bot.command()
@commands.has_permissions(administrator=True)
async def voicepanel(ctx):
    panel_description = (
        "Use the buttons below to control your voice channel.\n\n"
        "**Button Usage**\n"
        f"{VC_EMOJI_LOCK} — **Lock** the voice channel\n"
        f"{VC_EMOJI_UNLOCK} — **Unlock** the voice channel\n"
        f"{VC_EMOJI_GHOST} — **Ghost** the voice channel\n"
        f"{VC_EMOJI_REVEAL} — **Reveal** the voice channel\n"
        f"{VC_EMOJI_CLAIM} — **Claim** the voice channel\n"
        f"{VC_EMOJI_DISCONNECT} — **Disconnect** a member\n"
        f"{VC_EMOJI_ACTIVITY} — **Start** an activity\n"
        f"{VC_EMOJI_INFO} — **View** channel information\n"
        f"{VC_EMOJI_PLUS} — **Increase** the user limit\n"
        f"{VC_EMOJI_MINUS} — **Decrease** the user limit"
    )

    embed = discord.Embed(
        description=panel_description,
        color=discord.Color.dark_theme()
    )

    view = VoiceControlView()
    await ctx.send(embed=embed, view=view)

# Alias so "!panel" also opens the button interface
@bot.command(name="panel")
@commands.has_permissions(administrator=True)
async def panel_alias(ctx):
    await voicepanel(ctx)

# 5b. !permit command — lets a specific member into your current voice channel
@bot.command()
async def permit(ctx, member: discord.Member = None):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You need to be in a voice channel to use this.")
        return

    if member is None:
        await ctx.send("❌ Usage: `!permit @user`")
        return

    channel = ctx.author.voice.channel

    overwrite = channel.overwrites_for(member)
    overwrite.connect = True
    overwrite.view_channel = True
    await channel.set_permissions(member, overwrite=overwrite)

    await ctx.send(f"✅ {member.mention} has been permitted into {channel.mention}.")

# 5c. !vc command group — separate text-command version, plain text (no embeds)
# This is intentionally independent from !voicepanel/!panel above.
@bot.group(invoke_without_command=True)
async def vc(ctx):
    await ctx.send("Usage: `!vc <lock|unlock|ghost|reveal|claim|disconnect|activity|info|increase|decrease|permit|reject>`")

async def _get_author_vc(ctx):
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You must be connected to a voice channel to control it!")
        return None
    return ctx.author.voice.channel

@vc.command(name="lock")
async def vc_lock(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"🔒 Locked voice channel: {channel.mention}")

@vc.command(name="unlock")
async def vc_unlock(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.connect = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"🔓 Unlocked voice channel: {channel.mention}")

@vc.command(name="ghost")
async def vc_ghost(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"👻 Hidden voice channel: {channel.mention}")

@vc.command(name="reveal")
async def vc_reveal(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.view_channel = True
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"👁️ Revealed voice channel: {channel.mention}")

@vc.command(name="claim")
async def vc_claim(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        await ctx.send("👑 Checking channel ownership privileges...")

@vc.command(name="disconnect")
async def vc_disconnect(ctx, member: discord.Member = None):
    channel = await _get_author_vc(ctx)
    if not channel:
        return
    if member is None:
        await ctx.send("❌ Usage: `!vc disconnect @user`")
        return
    if not member.voice or member.voice.channel != channel:
        await ctx.send(f"❌ {member.mention} isn't in {channel.mention}.")
        return
    await member.move_to(None)
    await ctx.send(f"🚫 Disconnected {member.mention} from {channel.mention}.")

@vc.command(name="activity")
async def vc_activity(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        await ctx.send("🎮 Discord activities session initialized.")

@vc.command(name="info")
async def vc_info(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        await ctx.send(f"ℹ️ **Channel Info:** Name: `{channel.name}` | Limit: `{channel.user_limit if channel.user_limit else 'Unlimited'}` members.")

@vc.command(name="increase")
async def vc_increase(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        new_limit = (channel.user_limit + 1) if channel.user_limit < 99 else 99
        await channel.edit(user_limit=new_limit)
        await ctx.send(f"➕ User limit increased to `{new_limit}`.")

@vc.command(name="decrease")
async def vc_decrease(ctx):
    channel = await _get_author_vc(ctx)
    if channel:
        new_limit = (channel.user_limit - 1) if channel.user_limit > 1 else 1
        await channel.edit(user_limit=new_limit)
        await ctx.send(f"➖ User limit decreased to `{new_limit}`.")

@vc.command(name="permit")
async def vc_permit(ctx, member: discord.Member = None):
    channel = await _get_author_vc(ctx)
    if not channel:
        return
    if member is None:
        await ctx.send("❌ Usage: `!vc permit @user`")
        return
    overwrite = channel.overwrites_for(member)
    overwrite.connect = True
    overwrite.view_channel = True
    await channel.set_permissions(member, overwrite=overwrite)
    await ctx.send(f"✅ {member.mention} has been permitted into {channel.mention}.")

@vc.command(name="reject")
async def vc_reject(ctx, member: discord.Member = None):
    channel = await _get_author_vc(ctx)
    if not channel:
        return
    if member is None:
        await ctx.send("❌ Usage: `!vc reject @user`")
        return
    await channel.set_permissions(member, overwrite=None)
    await ctx.send(f"🚫 {member.mention}'s access to {channel.mention} has been revoked.")

# 5d. GENERAL / COMMUNITY COMMANDS

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! `{latency}ms`")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    joined = member.joined_at.strftime('%Y-%m-%d') if member.joined_at else "Unknown"
    created = member.created_at.strftime('%Y-%m-%d')
    await ctx.send(
        f"**User Info — {member}**\n"
        f"ID: `{member.id}`\n"
        f"Joined Server: {joined}\n"
        f"Account Created: {created}\n"
        f"Top Role: {member.top_role.mention}"
    )

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    owner = guild.owner.mention if guild.owner else "Unknown"
    await ctx.send(
        f"**{guild.name}**\n"
        f"Members: {guild.member_count}\n"
        f"Owner: {owner}\n"
        f"Created: {guild.created_at.strftime('%Y-%m-%d')}\n"
        f"Roles: {len(guild.roles)}\n"
        f"Channels: {len(guild.channels)}"
    )

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(f"**{member}'s Avatar**\n{member.display_avatar.url}")

@bot.command()
async def roleinfo(ctx, *, role: discord.Role):
    await ctx.send(
        f"**Role Info — {role.name}**\n"
        f"ID: `{role.id}`\n"
        f"Members: {len(role.members)}\n"
        f"Position: {role.position}\n"
        f"Mentionable: {role.mentionable}"
    )

@bot.command()
async def poll(ctx, *, question):
    msg = await ctx.send(f"📊 **Poll:** {question}\n*Started by {ctx.author}*")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
async def coinflip(ctx):
    await ctx.send(f"🪙 {random.choice(['Heads', 'Tails'])}")

@bot.command(name="8ball")
async def eight_ball(ctx, *, question=None):
    if not question:
        await ctx.send("❌ Usage: `!8ball <question>`")
        return
    responses = ["Yes.", "No.", "Maybe.", "Ask again later.", "Definitely.", "Unlikely.", "Absolutely not."]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted {len(deleted) - 1} messages.")
    await msg.delete(delay=3)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"👢 Kicked {member.mention}. Reason: {reason or 'No reason provided.'}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Banned {member.mention}. Reason: {reason or 'No reason provided.'}")

# 6. AUTOMATIC STAFF LOG SYSTEM
@bot.event
async def on_audit_log_entry_create(entry):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel: return
    await asyncio.sleep(0.5)

    if entry.user.id == bot.user.id or entry.user.id == SERVER_OWNER_ID: return

    if bot_data["antinuke"] and entry.action in DESTRUCTIVE_ACTIONS and entry.user.id not in bot_data["whitelist"]:
        now = asyncio.get_event_loop().time()
        timestamps = [t for t in recent_actions.get(entry.user.id, []) if now - t < ANTINUKE_WINDOW_SECONDS]
        timestamps.append(now)
        recent_actions[entry.user.id] = timestamps

        if len(timestamps) >= ANTINUKE_THRESHOLD:
            recent_actions[entry.user.id] = []
            actor = entry.guild.get_member(entry.user.id)
            if actor:
                try:
                    await actor.ban(reason="Anti-nuke: rapid destructive actions detected")
                except discord.Forbidden:
                    pass
            alert = discord.Embed(
                title="🚨 Anti-Nuke Triggered",
                description=f"{entry.user.mention} (`{entry.user.id}`) tripped anti-nuke protection and was banned.\n**Trigger action:** `{entry.action.name}`",
                color=discord.Color.dark_red()
            )
            await channel.send(embed=alert)

    raw_reason = entry.reason if entry.reason else ""
    if entry.user.bot:
        found_id = re.search(r'(\d{17,19})', raw_reason)
        moderator_text = f"<@{found_id.group(1)}>" if found_id else "Staff Member (via Command Bot)"
    else:
        moderator_text = entry.user.mention

    target = entry.target
    display_reason = raw_reason if raw_reason else "No reason provided."

    if entry.action == discord.AuditLogAction.ban:
        embed = discord.Embed(title="🔨 Staff Log: Member Banned", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Was Banned:** {target.mention} (`{target.id}`)\n**Reason:** {display_reason}", color=discord.Color.dark_red())
        await channel.send(embed=embed)

    elif entry.action == discord.AuditLogAction.kick:
        embed = discord.Embed(title="👢 Staff Log: Member Kicked", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Was Kicked:** {target.mention} (`{target.id}`)\n**Reason:** {display_reason}", color=discord.Color.red())
        await channel.send(embed=embed)

    elif entry.action == discord.AuditLogAction.member_update:
        changes = entry.after
        if hasattr(changes, 'timed_out_until') and changes.timed_out_until is not None:
            embed = discord.Embed(title="🔇 Staff Log: Member Muted (Timeout)", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Was Muted:** {target.mention} (`{target.id}`)\n**Muted Until:** {changes.timed_out_until.strftime('%Y-%m-%d %H:%M:%S')} UTC", color=discord.Color.orange())
            await channel.send(embed=embed)

    elif entry.action == discord.AuditLogAction.member_role_update:
        if hasattr(entry.after, 'roles'):
            for role in entry.after.roles:
                embed = discord.Embed(title="🛡️ Staff Log: Role Assigned", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Received Role:** {target.mention} (`{target.id}`)\n**Role Added:** {role.mention}", color=discord.Color.green())
                await channel.send(embed=embed)
        if hasattr(entry.before, 'roles'):
            for role in entry.before.roles:
                embed = discord.Embed(title="🛡️ Staff Log: Role Removed", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Lost Role:** {target.mention} (`{target.id}`)\n**Role Removed:** {role.mention}", color=discord.Color.red())
                await channel.send(embed=embed)

    elif entry.action in [discord.AuditLogAction.channel_overwrite_create, discord.AuditLogAction.channel_overwrite_update, discord.AuditLogAction.channel_overwrite_delete]:
        target_channel = entry.target
        if entry.action == discord.AuditLogAction.channel_overwrite_create:
            label_text, card_title, card_color = "**Permission added:** New role/user override locks activated.", "⚙️ Staff Log: Channel Permission Added", discord.Color.green()
        elif entry.action == discord.AuditLogAction.channel_overwrite_delete:
            label_text, card_title, card_color = "**Permission removed:** Role/user override clears completely deleted.", "⚙️ Staff Log: Channel Permission Removed", discord.Color.red()
        else:
            label_text, card_title, card_color = "**Permission changed:** View channel, text message, or attachment toggle flags updated.", "⚙️ Staff Log: Channel Permission Changed", discord.Color.orange()

        embed = discord.Embed(title=card_title, description=f"**User Who Did The Action:** {moderator_text}\n**Channel Modified:** {target_channel.mention if hasattr(target_channel, 'mention') else target_channel}\n{label_text}", color=card_color)
        await channel.send(embed=embed)

# 7. Gives the role even if the message isn't cached in memory
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id: return
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

# 8. Removes the role even if the message isn't cached in memory
@bot.event
async def on_raw_reaction_remove(payload):
    emoji_str = str(payload.emoji)
    if emoji_str in EMOJI_TO_ROLE:
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
        role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
        if role and member: await member.remove_roles(role)

# 9. SECURITY / ANTI-NUKE COMMANDS (administrator only)

@bot.group(name="antinuke", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def antinuke_group(ctx):
    status = "🟢 ON" if bot_data["antinuke"] else "🔴 OFF"
    await ctx.send(f"🛡️ Anti-nuke is currently **{status}**.\nUsage: `!antinuke on` / `!antinuke off`")

@antinuke_group.command(name="on")
@commands.has_permissions(administrator=True)
async def antinuke_on(ctx):
    bot_data["antinuke"] = True
    save_data()
    await ctx.send("🛡️ Anti-nuke protection **enabled**.")

@antinuke_group.command(name="off")
@commands.has_permissions(administrator=True)
async def antinuke_off(ctx):
    bot_data["antinuke"] = False
    save_data()
    await ctx.send("🛡️ Anti-nuke protection **disabled**.")

@bot.group(name="whitelist", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def whitelist_group(ctx):
    await ctx.send("❌ Usage: `!whitelist add @user` / `!whitelist remove @user`")

@whitelist_group.command(name="add")
@commands.has_permissions(administrator=True)
async def whitelist_add(ctx, member: discord.Member):
    if member.id not in bot_data["whitelist"]:
        bot_data["whitelist"].append(member.id)
        save_data()
    await ctx.send(f"✅ {member.mention} is now whitelisted from anti-nuke.")

@whitelist_group.command(name="remove")
@commands.has_permissions(administrator=True)
async def whitelist_remove(ctx, member: discord.Member):
    if member.id in bot_data["whitelist"]:
        bot_data["whitelist"].remove(member.id)
        save_data()
    await ctx.send(f"🗑️ {member.mention} removed from the anti-nuke whitelist.")

@bot.command()
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    old_channel = ctx.channel
    new_channel = await old_channel.clone(reason=f"Nuked by {ctx.author}")
    await new_channel.edit(position=old_channel.position)
    await old_channel.delete()
    await new_channel.send("💣 This channel has been nuked.")

@bot.group(name="blacklist", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def blacklist_group(ctx):
    await ctx.send("❌ Usage: `!blacklist add @user [reason]` / `!blacklist remove @user`")

@blacklist_group.command(name="add")
@commands.has_permissions(administrator=True)
async def blacklist_add(ctx, user: discord.User, *, reason=None):
    if user.id not in bot_data["blacklist"]:
        bot_data["blacklist"].append(user.id)
        save_data()
    try:
        await ctx.guild.ban(user, reason=f"Blacklisted: {reason or 'No reason provided'}")
    except discord.Forbidden:
        await ctx.send("⚠️ Added to blacklist, but I don't have permission to ban them.")
        return
    await ctx.send(f"⛔ {user.mention} (`{user.id}`) has been blacklisted and banned.")

@blacklist_group.command(name="remove")
@commands.has_permissions(administrator=True)
async def blacklist_remove(ctx, user: discord.User):
    if user.id in bot_data["blacklist"]:
        bot_data["blacklist"].remove(user.id)
        save_data()
    try:
        await ctx.guild.unban(user)
    except discord.NotFound:
        pass
    await ctx.send(f"✅ {user.mention} (`{user.id}`) removed from blacklist and unbanned.")

@bot.command(name="removeblacklist")
@commands.has_permissions(administrator=True)
async def removeblacklist(ctx, user: discord.User):
    await blacklist_remove(ctx, user)

@bot.event
async def on_member_join(member):
    if member.id in bot_data["blacklist"]:
        try:
            await member.ban(reason="Blacklisted user attempted to rejoin.")
        except discord.Forbidden:
            pass

# --- JAIL SYSTEM ---
JAIL_ROLE_NAME = "Jailed"

async def get_or_create_jail_role(guild):
    role = discord.utils.get(guild.roles, name=JAIL_ROLE_NAME)
    if role is None:
        role = await guild.create_role(name=JAIL_ROLE_NAME, reason="Jail system role")
        for ch in guild.channels:
            try:
                if isinstance(ch, discord.TextChannel):
                    await ch.set_permissions(role, send_messages=False, add_reactions=False)
                elif isinstance(ch, discord.VoiceChannel):
                    await ch.set_permissions(role, connect=False)
            except discord.Forbidden:
                pass
    return role

@bot.event
async def on_guild_channel_create(channel):
    role = discord.utils.get(channel.guild.roles, name=JAIL_ROLE_NAME)
    if role:
        try:
            if isinstance(channel, discord.TextChannel):
                await channel.set_permissions(role, send_messages=False, add_reactions=False)
            elif isinstance(channel, discord.VoiceChannel):
                await channel.set_permissions(role, connect=False)
        except discord.Forbidden:
            pass

@bot.command()
@commands.has_permissions(administrator=True)
async def jail(ctx, channel: discord.TextChannel):
    bot_data["jail_channel"] = channel.id
    save_data()
    role = await get_or_create_jail_role(ctx.guild)
    await channel.set_permissions(role, view_channel=True, send_messages=True)
    await ctx.send(f"⚙️ Jail channel set to {channel.mention}.")

@bot.command()
@commands.has_permissions(administrator=True)
async def jailuser(ctx, member: discord.Member, *, reason=None):
    if bot_data["jail_channel"] is None:
        await ctx.send("❌ No jail channel set yet. Use `!jail #channel` first.")
        return
    role = await get_or_create_jail_role(ctx.guild)
    await member.add_roles(role, reason=reason)
    if member.voice:
        try:
            await member.move_to(None)
        except discord.Forbidden:
            pass
    jail_channel = ctx.guild.get_channel(bot_data["jail_channel"])
    if jail_channel:
        await jail_channel.send(f"🔒 {member.mention} has been jailed. Reason: {reason or 'No reason provided.'}")
    await ctx.send(f"🔒 {member.mention} has been jailed.")

@bot.command()
@commands.has_permissions(administrator=True)
async def unjail(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name=JAIL_ROLE_NAME)
    if role and role in member.roles:
        await member.remove_roles(role)
    await ctx.send(f"🔓 {member.mention} has been unjailed.")

# --- PURGE / CS / SNIPE ---
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 100):
    amount = max(1, min(amount, 1000))  # safety cap; discord.py chunks this into <=100-message API calls
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Purged {len(deleted) - 1} messages.")
    await msg.delete(delay=3)

@bot.command(name="cs")
async def cs_cmd(ctx):
    cutoff = discord.utils.utcnow() - timedelta(minutes=5)
    entries = [e for e in deleted_messages.get(ctx.channel.id, []) if e["time"] >= cutoff]
    if not entries:
        await ctx.send("❌ No messages deleted in this channel in the last 5 minutes.")
        return

    lines = ["🗑️ **Recently Deleted Messages**"]
    for e in entries[-10:]:  # cap at 10
        ts = discord.utils.format_dt(e["time"], style="T")
        content = e["content"] or "*[no text content]*"
        lines.append(f"**{e['author']}** • {ts}\n{content}")
    await ctx.send("\n\n".join(lines))

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    entry = {
        "content": message.content,
        "author": message.author,
        "time": discord.utils.utcnow()
    }
    deleted_messages.setdefault(message.channel.id, []).append(entry)
    cutoff = discord.utils.utcnow() - timedelta(minutes=5)
    deleted_messages[message.channel.id] = [e for e in deleted_messages[message.channel.id] if e["time"] >= cutoff]

@bot.command()
async def snipe(ctx):
    entries = deleted_messages.get(ctx.channel.id)
    if not entries:
        await ctx.send("❌ Nothing to snipe here.")
        return
    data = entries[-1]
    content = data["content"] or "*[no text content]*"
    await ctx.send(f"**{data['author']}:** {content}")

keep_alive()
rules.add_rules_command(bot)
bot.run(os.environ.get("DISCORD_TOKEN"))
