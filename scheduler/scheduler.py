import datetime
import time
import sched
import asyncio
import shlex
from pytimeparse import parse
from iteration_utilities import grouper
from dateutil import parser
import json

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

class Scheduler(commands.Cog):
    """Scheduler for events and reminders"""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.scheduler = sched.scheduler(time.time, asyncio.sleep)
        try:
            self.events = json.load(open('home/ec2-user/events.json'))
        except FileNotFoundError:
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

    def parse_args(self, *args):
        args_dict = {}
        for group in grouper(args, 2, fillvalue=None):
            flag, arg = group
            if str(flag).startswith('--'):
                args_dict[flag] = arg
            else:
                raise SyntaxError(args)
        return args_dict

    @commands.group(name='event', help='Commands for managing events and reminders')
    async def event(self, ctx):
        pass

    @commands.command(name='message', parent=event, help='Schedule a message to send at specified time using `HH:MM` format')
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

    @commands.command(name='schedule', parent=event, help='Schedule a new event')
    async def event_schedule(self, ctx, *args):
        options = self.parse_args(*args)
        if options['--name']:
            name = options['--name']
            if name in self.events:
                await ctx.send('Event with that name already exists')
                return
        else:
            await ctx.send('Must specify event name')
            return
        if options['--time']:
            event_time = options['--time']
        else:
            await ctx.send('No time specified, defaulting to Saturday at 3:00pm')
            event_time = 'Saturday at 3:00pm'
        if '--repeat' in options:
            repeat = parse(options['--repeat'], granularity='minutes')
        else:
            repeat = None
        if options['--remind']:
            remind = parse(options['--remind'], granularity='minutes')
        else:
            remind = None
        self.events[name] = {
            'time': event_time,
            'repeat': repeat,
            'remind': remind,
            'attending': [],
            'absent': []
        }
        with open('home/ec2-user/events.json', 'w') as json_file:
            json.dump(self.events, json_file, indent=4)
        message_string = f"Scheduling `{name}` at `{parser.parse(timestr=self.events[name]['time'], fuzzy=True).time().isoformat('auto')}`."
        if self.events[name]['repeat']:
            message_string += f' Repeating every `{repeat}` seconds.'
        if self.events[name]['remind']:
            message_string += f' Sending reminder `{remind}` seconds before event.'
        await ctx.send(message_string)

        while name in self.events:
            reminder_string = f"**{name}** at {parser.parse(timestr=self.events[name]['time'], fuzzy=True)}"
            event_string = f'**{name}** starting now'
            event_delay = (parser.parse(timestr=self.events[name]['time'], fuzzy=True) - datetime.datetime.now()).total_seconds()
            remind_delay = event_delay - self.events[name]['remind']
            await asyncio.sleep(remind_delay)
            if name in self.events:
                if remind_delay > 0:
                    message = await ctx.send(reminder_string)
                    message_id = message.id
                    self.events[name]['message-id'] = message_id
                    with open('home/ec2-user/events.json', 'w') as json_file:
                        json.dump(self.events, json_file, indent=4)
                    await message.add_reaction('<:spimPog:772261869858848779>')
                    await message.add_reaction('<:spon:922922345134424116>')
            await asyncio.sleep(self.events[name]['remind'])
            if name in self.events:
                await ctx.send(event_string)
                if self.events[name]['repeat']:
                    self.events[name]['time'] = parser.parse(timestr=self.events[name]['time'], fuzzy=True) + datetime.timedelta(seconds=self.events[name]['repeat'])
                else:
                    self.events.pop(name, None)
                    with open('home/ec2-user/events.json', 'w') as json_file:
                        json.dump(self.events, json_file, indent=4)

    @commands.command(name='cancel', parent=event, help='Cancel a scheduled event')
    async def cancel_event(self, ctx, name):
        event = self.events.pop(name, None)
        if event:
            await ctx.send(f"Removed {name}")
            with open('home/ec2-user/events.json', 'w') as json_file:
                json.dump(self.events, json_file, indent=4)
        else:
            await ctx.send(f'{name} not found in events list')

    @commands.command(name='list', parent=event, help='List scheduled events')
    async def event_list(self, ctx, *event_names):
        if self.events:
            text = 'Currently scheduled events:'
            for name in self.events:
                event = self.events[name]
                text += f"```\n{name}\nTime: {event['time']}\nRepeats interval: {event['repeat']} seconds\nReminder: {event['remind']} seconds prior```"
        else:
            text = '```No events scheduled```'
        await ctx.send(text)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        user = payload.member
        emoji = payload.emoji
        message_id = payload.message_id
        message = await self.bot.get_channel(payload.channel_id).fetch_message(message_id)
        # await message.channel.send(f"{emoji} added by {user} to message {message_id}")
        if user != self.bot.user:
            for name in self.events:
                # await message.channel.send(name)
                event = self.events[name]
                if message_id == event['message-id']:
                    # await message.channel.send('message-id matches')
                    if emoji.name == 'spimPog':
                        await message.channel.send('<:spimPog:772261869858848779>')
                        if user in event['absent']:
                            event['absent'].remove(user)
                            await message.remove_reaction('<:spon:922922345134424116>', user)
                        if not user in event['attending']:
                            event['attending'].append(user)
                    elif emoji.name == 'spon':
                        await message.channel.send('<:spon:922922345134424116>')
                        if user in event['attending']:
                            event['attending'].remove(user)
                            await message.remove_reaction('<:spon:922922345134424116>', user)
                        if not user in self.events['absent']:
                            event['absent'].append(user)
                    else:
                        await message.channel.send(f"`{emoji.name} != spimPog or spon`")
                    with open('home/ec2-user/events.json', 'w') as json_file:
                                json.dump(self.events, json_file, indent=4)
                # else:
                    # await message.channel.send(f"{message_id} != {event['message-id']}")