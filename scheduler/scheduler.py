import datetime
import time
import sched
import asyncio

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
    async def schedule_message(self, ctx, message, time_string):
        send_time = time.strptime(time_string, '%H:%M')
        send_delay = time.mktime(send_time) - time.mktime(datetime.datetime.now().timetuple())
        await ctx.send(f"sending '{message}' at {send_time.__str__()} in {send_delay.__str__()} seconds")
        await asyncio.sleep(send_delay)
        await ctx.send(message)

    async def send_message(self, ctx, message):
        await ctx.send(message)

