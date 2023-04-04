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
        self.events = {}

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
        message_string = 'React to this message with something'
        message = await ctx.send(message_string)

        def check(reaction, user):
            return str(reaction.emoji) == '<:spimPog:772261869858848779>' and reaction.message == message
        
        try:
            reaction, user = await self.bot.wait_for('reaction_add', check=check)
        finally:
            await ctx.send(f'{user} reacted to the message with {reaction}')
            await reaction.message.add_reaction('<:spimPog:772261869858848779>')
            # await ctx.send(f'{reaction.message}')
            # I am in your walls 😳

    @commands.command(name='event', parent=schedule, help='Schedule a new event')
    async def schedule_event(self, ctx, name, *time_string):
        self.events[name] = {
            'time': parser.parse(timestr=' '.join(time_string), fuzzy=True),
        }

        message = await ctx.send(f"Scheduling {name} at {self.events[name]['time'].time().isoformat('auto')}")
        await message.add_reaction('<:spimPog:772261869858848779>')
        await message.add_reaction('<:spimPause:987933390110089216>')

        send_delay = (self.events[name]['time'] - datetime.datetime.now()).total_seconds()

    @commands.command(name='cancel', parent=schedule, help='Cancel a scheduled event')
    async def cancel_event(self, ctx, name):
        event = self.events.pop(name, None)
        if event:
            await ctx.send(f"Removed {name}")
        else:
            await ctx.send(f'{name} not found in events list')

    async def on_reaction_add(self, ctx):
        await ctx.send('Reaction added')