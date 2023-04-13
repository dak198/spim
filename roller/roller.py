import random

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config


class Roller(commands.Cog):
    """Cogs for Red-DiscordBot V3 for use in Gear Getaway"""

    def __init__(self, bot: Red) -> None:
        self.bot = bot


    @commands.command(name="roll", help="output a random roll for a given combination of dice")
    async def roll(self, ctx, input_string):
        await ctx.send("Command not yet implemented")