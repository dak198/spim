import datetime
import time
import sched
import asyncio
import shlex
from pytimeparse import parse
from iteration_utilities import grouper
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

    @commands.command(name='flags-test', help='Test parsing arguments with flags')
    async def flags_test(self, ctx, *, options: str):
        options = shlex.split(options)
        await ctx.send(options)

    @commands.command(name='args-test', help='Testing the effect of double quotes on argument separation')
    async def args_test(self, ctx, *args: str):
        for group in grouper(args, 2, fillvalue=None):
            flag, arg = group
            if flag.startswith('--'):
                await ctx.send(f'Flag: {flag}\nArguments: {arg}')
            else:
                await ctx.send('Invalid argument syntax')

    def parse_args(*args: str):
        args_dict = {}
        for group in grouper(args, 2, fillvalue=None):
            flag, arg = group
            if str(flag).startswith('--'):
                args_dict[str(flag)] = str(arg)
            else:
                raise SyntaxError
        return args_dict

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
    async def schedule_event(self, ctx, *args):
        options = self.parse_args(args)
        if options['--name']:
            name = options['--name']
            if self.events[name]:
                await ctx.send[f'Event with that name already exists']
                return
        else:
            await ctx.send('Must specify event name')
            return
        if options['--time']:
            event_time = options['--time']
        else:
            await ctx.send('No time specified, defaulting to Saturday at 3:00pm')
            event_time = 'Saturday at 3:00pm'
        if options['--repeat']:
            repeat = parse(options['--repeat'], granularity='minutes')
        else:
            repeat = None
        if options['--remind']:
            remind = parse(options['--remind'], granularity='minutes')
        else:
            remind = None
        self.events[name] = {
            'time': parser.parse(timestr=event_time, fuzzy=True),
            'repeat': repeat,
            'remind': remind
        }
        message_string = f"Scheduling {name} at {self.events[name]['time'].time().isoformat('auto')}."
        if self.events['repeat']:
            message_string += f' Repeating every {repeat} seconds.'
        if self.events['remind']:
            message_string += f' Sending reminder {remind} seconds before event.'
        message = await ctx.send(message_string)
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

    # @commands.Cog.listener()
    # async def on_raw_reaction_add(self, payload):
    #     channel = await self.bot.fetch_channel(payload.channel_id)
    #     await channel.send('Reaction was added')