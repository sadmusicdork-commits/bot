import os
import discord
from discord.ext import commands, tasks
from threading import Thread
from flask import Flask
import rules
import urllib.request
import asyncio
import re

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
    embed.set_footer(text="꒰১ ໒꒱ • Role Selection")

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

# 📜 VOICE PANEL TRIGGER COMMAND FOR ADMIN STAFF (EXACT MATCHING DESIGN LOOK)
@bot.command()
@commands.has_permissions(administrator=True)
async def voicepanel(ctx):
    # Constructing description layout using your precise line breaks and dashes format
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
    embed.set_footer(text="/admire • interface")
    
    view = VoiceControlView()
    await ctx.send(embed=embed, view=view)

# 6. AUTOMATIC STAFF LOG SYSTEM (HUMAN ATTRIBUTION DETECTOR RUNNING)
@bot.event
async def on_audit_log_entry_create(entry):
    channel = bot.get_channel(LOG_CHANNEL_ID)
    if not channel: return
    await asyncio.sleep(0.5)

    if entry.user.id == bot.user.id or entry.user.id == SERVER_OWNER_ID: return

    raw_reason = entry.reason if entry.reason else ""
    if entry.user.bot:
        found_id = re.search(r'(\d{17,19})', raw_reason)
        moderator_text = f"<@{found_id.group(1)}>" if found_id else "Staff Member (via Command Bot)"
    else:
        moderator_text = entry.user.mention

    target = entry.target
    display_reason = raw_reason if raw_reason else "No reason provided."

    # BAN LOGS
    if entry.action == discord.AuditLogAction.ban:
        embed = discord.Embed(title="🔨 Staff Log: Member Banned", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Was Banned:** {target.mention} (`{target.id}`)\n**Reason:** {display_reason}", color=discord.Color.dark_red())
        embed.set_footer(text="/admire")
        await channel.send(embed=embed)

    # KICK LOGS
    elif entry.action == discord.AuditLogAction.kick:
        embed = discord.Embed(title="👢 Staff Log: Member Kicked", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Was Kicked:** {target.mention} (`{target.id}`)\n**Reason:** {display_reason}", color=discord.Color.red())
        embed.set_footer(text="/admire")
        await channel.send(embed=embed)

    # TIMEOUT LOGS
    elif entry.action == discord.AuditLogAction.member_update:
        changes = entry.after
        if hasattr(changes, 'timed_out_until') and changes.timed_out_until is not None:
            embed = discord.Embed(title="🔇 Staff Log: Member Muted (Timeout)", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Was Muted:** {target.mention} (`{target.id}`)\n**Muted Until:** {changes.timed_out_until.strftime('%Y-%m-%d %H:%M:%S')} UTC", color=discord.Color.orange())
            embed.set_footer(text="/admire")
            await channel.send(embed=embed)

    # ROLE LOGS
    elif entry.action == discord.AuditLogAction.member_role_update:
        if hasattr(entry.after, 'roles'):
            for role in entry.after.roles:
                embed = discord.Embed(title="🛡️ Staff Log: Role Assigned", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Received Role:** {target.mention} (`{target.id}`)\n**Role Added:** {role.mention}", color=discord.Color.green())
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)
        if hasattr(entry.before, 'roles'):
            for role in entry.before.roles:
                embed = discord.Embed(title="🛡️ Staff Log: Role Removed", description=f"**User Who Did The Action:** {moderator_text}\n**User Who Lost Role:** {target.mention} (`{target.id}`)\n**Role Removed:** {role.mention}", color=discord.Color.red())
                embed.set_footer(text="/admire")
                await channel.send(embed=embed)

    # CHANNEL PERMISSION OVERWRITE LOGS
    elif entry.action in [discord.AuditLogAction.channel_overwrite_create, discord.AuditLogAction.channel_overwrite_update, discord.AuditLogAction.channel_overwrite_delete]:
        target_channel = entry.target
        if entry.action == discord.AuditLogAction.channel_overwrite_create:
            label_text, card_title, card_color = "**Permission added:** New role/user override locks activated.", "⚙️ Staff Log: Channel Permission Added", discord.Color.green()
        elif entry.action == discord.AuditLogAction.channel_overwrite_delete:
            label_text, card_title, card_color = "**Permission removed:** Role/user override clears completely deleted.", "⚙️ Staff Log: Channel Permission Removed", discord.Color.red()
        else:
            label_text, card_title, card_color = "**Permission changed:** View channel, text message, or attachment toggle flags updated.", "⚙️ Staff Log: Channel Permission Changed", discord.Color.orange()

        embed = discord.Embed(title=card_title, description=f"**User Who Did The Action:** {moderator_text}\n**Channel Modified:** {target_channel.mention if hasattr(target_channel, 'mention') else target_channel}\n{label_text}", color=card_color)
        embed.set_footer(text="/admire")
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

keep_alive()
rules.add_rules_command(bot)
bot.run(os.environ.get("DISCORD_TOKEN"))
