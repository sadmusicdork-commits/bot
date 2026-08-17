import os
import discord
from discord.ext import commands
from threading import Thread
from flask import Flask

# --- RENDER FREE TIER FIX: Background Web Server Loop ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is online!"

def run_web():
    # Render routes traffic through port 10000 by default
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# 1. Background settings to let the bot read messages and members
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# We will use '!' as the prefix to trigger your setup command
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. YOUR DISCORD SERVER ROLE IDS
ROLE_18_PLUS = 1538782704873644132    
ROLE_18_MINUS = 1538782755482107954   
ROLE_MALE = 1538782632052002906       
ROLE_FEMALE = 1538782590121541712     

# 3. YOUR CUSTOM EMOJI STRINGS
CUSTOM_EMOJI_18_PLUS = "<:emoji_16:1535248499459760178>"
CUSTOM_EMOJI_18_MINUS = "<:minor:1535242961426714684>"
CUSTOM_EMOJI_MALE = "♂️"
CUSTOM_EMOJI_FEMALE = "♀️"

# This maps the emojis underneath the message to the corresponding roles
EMOJI_TO_ROLE = {
    CUSTOM_EMOJI_18_PLUS: ROLE_18_PLUS,
    CUSTOM_EMOJI_18_MINUS: ROLE_18_MINUS,
    CUSTOM_EMOJI_MALE: ROLE_MALE,
    CUSTOM_EMOJI_FEMALE: ROLE_FEMALE
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}! Your bot is online and ready.")

# 4. Command to send the exact reaction roles embed message
@bot.command()
@commands.has_permissions(administrator=True)
async def setup_roles(ctx):
    embed = discord.Embed(
        title="Role Selection",
        description="Pick your roles to personalize your experience within the server.",
        color=discord.Color.dark_theme()

    )
    embed.add_field(name="Age", value=f"{CUSTOM_EMOJI_18_PLUS} **18+**\n{CUSTOM_EMOJI_18_MINUS} **18-**", inline=False)
    embed.add_field(name="Identity", value=f"{CUSTOM_EMOJI_MALE} **Male**\n{CUSTOM_EMOJI_FEMALE} **Female**", inline=False)
    embed.add_field(
        name="Information", 
        value="• Choose **one** age role.\n• Identity roles are optional.\n• Roles can be changed at any time.", 
        inline=False
    )
    embed.set_footer(text="꒰১ ໒꒱ • Role Selection")

    # Send the message
    msg = await ctx.send(embed=embed)
    
    # Automatically add the reaction numbers and symbols underneath it
    for emoji in EMOJI_TO_ROLE.keys():
        await msg.add_reaction(emoji)

# 5. Code that gives the role when a member clicks the reaction
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return  # Ignore the bot's own reactions

    emoji_str = str(payload.emoji)
    
    if emoji_str in EMOJI_TO_ROLE:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
        
        if role and member:
            # Enforce the rule: Remove the other age role if they select a new one
            if emoji_str == CUSTOM_EMOJI_18_PLUS:
                opposite = guild.get_role(ROLE_18_MINUS)
                if opposite in member.roles:
                    await member.remove_roles(opposite)
            elif emoji_str == CUSTOM_EMOJI_18_MINUS:
                opposite = guild.get_role(ROLE_18_PLUS)
                if opposite in member.roles:
                    await member.remove_roles(opposite)

            # Add the chosen role
            await member.add_roles(role)

# 6. Code that removes the role if a member unchecks the reaction
@bot.event
async def on_raw_reaction_remove(payload):
    emoji_str = str(payload.emoji)
    if emoji_str in EMOJI_TO_ROLE:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(EMOJI_TO_ROLE[emoji_str])
        
        if role and member:
            await member.remove_roles(role)

# Start the web handler loop before launching the bot connection
keep_alive()

# This line securely reads your token from Render's Environment Variables
bot.run(os.environ.get("DISCORD_TOKEN"))
