import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

class Scheduler(commands.Cog):
    """Scheduler for events and reminders"""
    
    def __init__(self, bot: Red) -> None:
        self.bot = bot

    @commands.command(name='test')
    async def test(self, ctx):
        await ctx.send('test')
