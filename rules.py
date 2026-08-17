import discord
from discord.ext import commands

def add_rules_command(bot):
    # 1. Command for your rules channel
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setup_rules(ctx):
        embed = discord.Embed(
            title="rules",
            description="follow tos\nuse common sense\nno nsfw/gore\nno racial slurs\nno advertisement",
            color=discord.Color.dark_theme()
        )
        embed.set_footer(text="꒰১ ໒꒱ • Server Rules")
        await ctx.send(embed=embed)

    # 2. Command for your general channel
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setup_perms(ctx):
        embed = discord.Embed(
            title="Picture Permissions",
            description="rep **/admire** in status or **boost** for pic perms",
            color=discord.Color.dark_theme()
        )
        embed.set_footer(text="꒰১ ໒꒱ • Media Access")
        await ctx.send(embed=embed)
