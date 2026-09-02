import discord
from discord.ext import commands

def add_rules_command(bot):
    # Command for your rules channel
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setup_rules(ctx):
        embed = discord.Embed(
            title="rules",
            description="follow tos\nuse common sense\nno nsfw/gore\nno racial slurs\nno advertisement",
            color=discord.Color.dark_theme()
        )
        embed.set_footer(text="• Server Rules")
        await ctx.send(embed=embed)
