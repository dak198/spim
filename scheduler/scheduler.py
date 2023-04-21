import datetime
import time
import sched
import asyncio
import uuid
from pytimeparse import parse
from iteration_utilities import grouper
from dateutil import parser
import json

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

# path to the json file containing the events list
FILE_PATH = 'home/ec2-user/events.json'

class Scheduler(commands.Cog):
    """Scheduler for events and reminders"""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.scheduler = sched.scheduler(time.time, asyncio.sleep)
        try:
            self.events = json.load(open(FILE_PATH))
        except FileNotFoundError:
            self.events = {}

    def parse_args(self, *args):
        args_dict = {}
        for group in grouper(args, 2, fillvalue=None):
            flag, arg = group
            if str(flag).startswith('--'):
                args_dict[flag] = arg
            else:
                raise SyntaxError(args)
        return args_dict
    
    async def add_event(self, ctx, name: str, event: dict):
        # add event to event list
        self.events[name] = event
        # update event list in external file
        with open(FILE_PATH, 'w') as json_file:
            json.dump(self.events, json_file, indent=4)
            json_file.close()

        # print event info to the chat
        message_string = f"Scheduling `{name}` at `{parser.parse(timestr=self.events[name]['time'], fuzzy=True).time().isoformat('auto')}`."
        if self.events[name]['repeat']:
            message_string += f" Repeating every `{self.events['repeat']}` seconds."
        if self.events[name]['remind']:
            message_string += f" Sending reminder `{self.events['remind']}` seconds before event."
        if self.events[name]['notify']:
            message_string += 'Notifying with `@everyone`'
        await ctx.send(message_string)

        # loop in case of repeated event
        while name in self.events:
            # calculate wait times
            event_delay = (parser.parse(timestr=self.events[name]['time'], fuzzy=True) - datetime.datetime.now()).total_seconds()
            remind_delay = event_delay - self.events[name]['remind']
            # skip waiting for the reminder if it is before the event time
            if remind_delay > 0:
                # sleep thread until reminder time
                await asyncio.sleep(remind_delay)
                # update events list from file in case of changes during sleep
                self.events = json.load(open(FILE_PATH))
                # make sure event is still exists when done waiting
                # validate id as well as name in case the event was cancelled and replaced with a new event with the same name
                if name in self.events and self.events[name]['id'] == event['id']:
                        # send reminder based on provided arguments
                        reminder_string = f"**{name}** at {parser.parse(timestr=self.events[name]['time'], fuzzy=True)}"
                        if self.events[name]['notify']:
                            reminder_string = '@everyone ' + reminder_string
                        # only generate new reminder message if there is not already one linked to this event
                        if not self.events[name]['message-id']:
                            message = await ctx.send(reminder_string)
                            # save reminder message id to event data and output to json file
                            message_id = message.id
                            self.events[name]['message-id'] = message_id
                            with open(FILE_PATH, 'w') as json_file:
                                json.dump(self.events, json_file, indent=4)
                                json_file.close()
                            # add reactions to reminder message for users to indicate 'attending' or 'absent'
                            await message.add_reaction('<:spimPog:772261869858848779>')
                            await message.add_reaction('<:spon:922922345134424116>')

            # sleep thread until event time
            await asyncio.sleep(self.events[name]['remind'])
            # make sure event still exists when done waiting
            if name in self.events:
                # announce start of event
                event_string = f'**{name}** starting now'
                await ctx.send(event_string)
                # unlink the old reminder message
                self.events[name]['message-id'] = None
                # if the event repeats, set the time to the next repeat interval
                if self.events[name]['repeat']:
                    self.events[name]['time'] = parser.parse(timestr=self.events[name]['time'], fuzzy=True) + datetime.timedelta(seconds=self.events[name]['repeat'])
                # if the event does not repeat, remove it from the events list and update the json file
                else:
                    self.events.pop(name, None)
                    with open(FILE_PATH, 'w') as json_file:
                        json.dump(self.events, json_file, indent=4)
                        json_file.close()

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

    @commands.command(name='schedule', parent=event, help='Schedule a new event')
    async def event_schedule(self, ctx, *args):
        # parse the provided arguments into a dict
        options = self.parse_args(*args)
        # check for if an event name was provided, return if not
        if '--name' in options:
            name = options['--name']
            # return if event name already exists
            if name in self.events:
                await ctx.send('Event with that name already exists')
                return
        else:
            await ctx.send('Must specify event name')
            return
        
        # create an empty event with default values and a unique id
        event = {
            'id': uuid.uuid4(),
            'message-id': None,
            'time': 'Saturday at 3:00pm',
            'repeat': None,
            'remind': None,
            'notify': False,
            'attending': {},
            'absent': {}
        }

        # configure the empty event with the provided arguments
        if '--time' in options:
            event['time'] = options['--time']
        else:
            await ctx.send('No time specified, defaulting to Saturday at 3:00pm')
        if '--repeat' in options:
            event['repeat'] = parse(options['--repeat'], granularity='minutes')
        if '--remind' in options:
            event['remind'] = parse(options['--remind'], granularity='minutes')
        if '--notify' in options and options['--notify'].lower() == 'true':
            event['notify'] = True
        # process the newly added event
        self.add_event(ctx, name, event)

    @commands.command(name='cancel', parent=event, help='Cancel a scheduled event')
    async def event_cancel(self, ctx, name):
        # attempt to remove event with given name from event list
        event = self.events.pop(name, None)
        # if event was successfully removed, update the json file
        if event:
            await ctx.send(f"Removed {name}")
            with open(FILE_PATH, 'w') as json_file:
                json.dump(self.events, json_file, indent=4)
                json_file.close()
        else:
            await ctx.send(f'{name} not found in events list')

    @commands.command(name='edit', parent=event, help='Edit an existing event')
    async def event_edit(self, ctx, *args):
        # parse the provided arguments into a dict
        options = self.parse_args(*args)
        # check for if an event name was provided, return if not
        if '--name' in options:
            name = options['--name']
        else:
            await ctx.send('Must specify event name')
            return
        # pop event from event list and ensure it exists
        event = self.events.pop(name, None)
        if event:
            # update the event with the parameters that were specified in options
            for flag in options:
                event[flag] = options[flag]
            # add the event back to the list
            self.add_event(ctx, name, event)
        else:
            await ctx.send('Event with that name does not exist')

    @commands.command(name='list', parent=event, help='List scheduled events')
    async def event_list(self, ctx, *event_names):
        if self.events:
            text = 'Currently scheduled events:'
            for name in self.events:
                event = self.events[name]
                attend_string = ""
                for user_id in event['attending']:
                    display_name = event['attending'][user_id]
                    attend_string += f"\n- {display_name}"
                absent_string = ""
                for user_id in event['absent']:
                    display_name = event['absent'][user_id]
                    absent_string += f"\n- {display_name}"
                text += f"```\n{name}\nTime: {event['time']}\nRepeats interval: {event['repeat']} seconds\nReminder: {event['remind']} seconds prior\nAttending: {attend_string}\nAbsent: {absent_string}```"
        else:
            text = '```No events scheduled```'
        await ctx.send(text)

    @commands.command(name='repeat-message')
    async def set_repeat_message(self, ctx, state):
        if state == 'start':
            self.repeat_message.start()
            await ctx.send('Started repeat message')
        elif state == 'stop':
            self.repeat_message.stop()
            await ctx.send('Stopped repeat message')

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        user = payload.member
        emoji = payload.emoji
        message_id = payload.message_id
        message = await self.bot.get_channel(payload.channel_id).fetch_message(message_id)
        if user.id != self.bot.user.id:
            for name in self.events:
                event = self.events[name]
                if 'message-id' in event:
                    if message_id == event['message-id']:
                        if emoji.name == 'spimPog':
                            if user.id in event['absent']:
                                event['absent'].pop(user.id)
                                await message.remove_reaction('<:spon:922922345134424116>', user)
                            if not user.id in event['attending']:
                                event['attending'][user.id] = user.display_name
                        elif emoji.name == 'spon':
                            if user.id in event['attending']:
                                event['attending'].pop(user.id)
                                await message.remove_reaction('<:spimPog:772261869858848779>', user)
                            if not user.id in event['absent']:
                                event['absent'][user.id] = user.display_name
                        with open(FILE_PATH, 'w') as json_file:
                                    json.dump(self.events, json_file, indent=4)
                                    json_file.close()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        user_id = payload.user_id
        emoji = payload.emoji
        message_id = payload.message_id
        if user_id != self.bot.user.id:
            for name in self.events:
                event = self.events[name]
                if 'message-id' in event:
                    if message_id == event['message-id']:
                        if emoji.name == 'spimPog':
                            event['attending'].pop(user_id, None)
                        elif emoji.name == 'spon':
                            event['absent'].pop(user_id, None)
                        with open(FILE_PATH, 'w') as json_file:
                                    json.dump(self.events, json_file, indent=4)
                                    json_file.close()

    @tasks.loop(seconds=15.0)
    async def repeat_message(self):
        channel = self.bot.get_channel(661373412400431104)
        await channel.send("Test")