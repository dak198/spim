import datetime
import time
import sched
import asyncio
from dateutil import parser

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

class Scheduler(commands.Cog):
    """Scheduler for events and reminders"""
    
    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.scheduler = sched.scheduler(time.time, asyncio.sleep)

    @commands.group(name='schedule', help='Commands for scheduling events and reminders')
    async def schedule(self, ctx):
        pass

    @commands.command(name='message', parent=schedule, help='Schedule a message to send at specified time using `HH:MM` format')
    async def schedule_message(self, ctx, message, *time_string):
        send_time = parser.parse(timestr=' '.join(time_string), fuzzy=True)
        current_time = datetime.datetime.now()
        send_delay = (send_time - datetime.datetime.now()).total_seconds()
        await ctx.send(f"It is {current_time.time().isoformat('auto')}. Sending '{message}' at {send_time.time().isoformat('auto')} in {send_delay} seconds")
        await asyncio.sleep(send_delay)
        await ctx.send(message)
        
    @commands.command(name='react-test', help='Send a message and print any reactions that are added')
    async def react_test(self, ctx):

        def check(reaction):
            return str(reaction.emoji == '👍')

        message = 'React to this message with something'
        await ctx.send(message)
        await self.bot.wait_for('reaction_add', check=check)
        await ctx.send('You reacted to the message')