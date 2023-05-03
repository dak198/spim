from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.base import JobLookupError
import asyncio
from uuid import uuid4
from pytimeparse import parse
from pytz import timezone
from iteration_utilities import grouper
from dateutil import parser
from json import load, dump

from discord import Embed
from redbot.core import commands, data_manager
from redbot.core.bot import Red
from redbot.core.config import Config

# path to the json file containing the events list

class Scheduler(commands.Cog):
    """Scheduler for events and reminders"""

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.data_path = data_manager.cog_data_path(self) / 'events.json'
        try:
            with open(self.data_path) as data_file:
                self.events = load(data_file)
        except FileNotFoundError:
            self.events = {}
            with open(self.data_path, 'w') as data_file:
                dump(self.events, data_file)

        self.scheduler = AsyncIOScheduler(timezone=timezone('US/Eastern'))
        for name in self.events:
            event = self.events[name]
            if event['remind'] and not self.scheduler.get_job(event['remind-id']):
                if event['time'] - event['remind'] > datetime.utcnow().timestamp():
                    self.scheduler.add_job(self.send_reminder, 'date', run_date=datetime.fromtimestamp(event['time'] - event['remind']), args=[name], id=event['remind-id'])
                elif event['repeat']:
                    self.scheduler.add_job(self.send_reminder, 'date', run_date=datetime.fromtimestamp(event['time'] - event['remind'] + event['repeat']), args=[name], id=event['remind-id'])
            if not self.scheduler.get_job(event['id']):
                self.scheduler.add_job(self.send_event, 'date', run_date=datetime.fromtimestamp(event['time']), args=[name], id=event['id'])
        self.scheduler.start()


    ####################
    # HELPER FUNCTIONS #
    ####################

    def parse_args(self, *args):
        args_dict = {}
        for group in grouper(args, 2, fillvalue=None):
            flag, arg = group
            if str(flag).startswith('--'):
                args_dict[flag[2:]] = arg
            else:
                raise SyntaxError(args)
        return args_dict

    async def send_reminder(self, name: str):
        event = self.events[name]
        # convert event time string to UTC timestamp
        timestamp = event['time']
        # add @everyone to the reminder string if enabled
        if event['notify']:
            notify = "@everyone "
        else:
            notify=""
        # send reminder string
        reminder_string = f"{notify}**{name}** starting <t:{timestamp}:F>"
        message = await self.bot.get_channel(event['channel-id']).send(reminder_string)
        # save reminder message id to event data and output to json file
        message_id = message.id
        event['message-id'] = message_id
        with open(self.data_path, 'w') as json_file:
            dump(self.events, json_file, indent=4)
            json_file.close()
        # add reactions to reminder message for users to indicate 'attending' or 'absent'
        await message.add_reaction('<:spimPog:772261869858848779>')
        await message.add_reaction('<:spon:922922345134424116>')
        if event['repeat']:
            self.scheduler.add_job(self.send_reminder, 'date', run_date=datetime.fromtimestamp(event['time'] - event['remind'] + event['repeat']), args=[name], id=event['remind-id'])

    async def send_event(self, name: str):
        event = self.events[name]
        if event['notify']:
            notify = "@everyone "
        else:
            notify = ""
        await self.bot.get_channel(event['channel-id']).send(f"{notify}**{name}** starting now")
        if event['repeat']:
            event['time'] += event['repeat']
            self.scheduler.add_job(self.send_event, 'date', run_date=datetime.fromtimestamp(event['time']), args=[name], id=event['id'])
        else:
            self.remove_event(name)

    def remove_event(self, name: str):
        # attempt to remove event with given name from event list
        event = self.events.pop(name, None)
        if event:
            # update the json file
            with open(self.data_path, 'w') as json_file:
                dump(self.events, json_file, indent=4)
            # remove associated jobs from scheduler
            try:
                self.scheduler.remove_job(event['id'])
                if event['remind']:
                    self.scheduler.remove_job(event['remind-id'])
            except JobLookupError as e:
                raise e
            return True
        else:
            return False


    async def add_event(self, ctx, name: str, event: dict):
        # add event to event list
        self.events[name] = event
        # update event list in external file
        with open(self.data_path, 'w') as json_file:
            dump(self.events, json_file, indent=4)

        if event['remind']:
            self.scheduler.add_job(self.send_reminder, 'date', run_date=datetime.fromtimestamp(event['time'] - event['remind']), args=[name], id=event['remind-id'])
        self.scheduler.add_job(self.send_event, 'date', run_date=datetime.fromtimestamp(event['time']), args=[name], id=event['id'])

        # print event info to the chat
        message_string = f"Scheduling `{name}` for <t:{event['time']}:F>."
        if event['repeat']:
            message_string += f" Repeating every `{event['repeat']}` seconds."
        if event['remind']:
            message_string += f" Sending reminder `{event['remind']}` seconds before event."
        if event['notify']:
            message_string += ' Notifying with `@everyone`.'
        await ctx.send(message_string)


    ##################
    # EVENT COMMANDS #
    ##################

    @commands.group(name='event', help='Commands for managing events and reminders')
    async def event(self, ctx):
        pass

    @commands.command(name='add', parent=event, help='Schedule a new event')
    async def event_add(self, ctx: commands.Context, *args):
        # parse the provided arguments into a dict
        options = self.parse_args(*args)
        # check for if an event name was provided, return if not
        if 'name' in options:
            name = options['name']
            # return if event name already exists
            if name in self.events:
                await ctx.send('Event with that name already exists')
                return
        else:
            await ctx.send('Must specify event name')
            return
        
        # create an empty event with default values and a unique id
        event = {
            'id': uuid4().hex,
            'remind-id': uuid4().hex,
            'channel-id': ctx.channel.id,
            'message-id': None,
            'time': int(round(parser.parse(timestr="Saturday at 3:00pm", fuzzy=True).timestamp())),
            'repeat': None,
            'remind': None,
            'notify': False,
            'attending': {},
            'absent': {}
        }

        # configure the empty event with the provided arguments
        if 'time' in options:
            event['time'] = int(round(parser.parse(timestr=options['time'], fuzzy=True).timestamp()))
        else:
            await ctx.send(f"No time specified, defaulting to <t:{event['time']}:F>")
        if 'repeat' in options:
            event['repeat'] = parse(options['repeat'], granularity='minutes')
        if 'remind' in options:
            event['remind'] = parse(options['remind'], granularity='minutes')
        if 'notify' in options and options['notify'].lower() == 'true':
            event['notify'] = True
        # process the newly added event
        await self.add_event(ctx, name, event)

    @commands.command(name='cancel', parent=event, help='Cancel a scheduled event')
    async def event_cancel(self, ctx, name):
        if self.remove_event(name):
            await ctx.send(f"Removed {name}")
        else:
            await ctx.send(f'{name} not found in events list')

    @commands.command(name='edit', parent=event, help='Edit an existing event')
    async def event_edit(self, ctx: commands.Context, *args):
        # parse provided arguments into a dict
        options = self.parse_args(*args)
        if options['time']:
            options['time'] = int(round(parser.parse(timestr=options['time'], fuzzy=True).timestamp()))
        # check for if an event name was provided
        name = options.pop('name', None)
        if name:
            if name in self.events:
                event = self.events[name]
                # update event with parameters specified in options (excluding name)
                for flag in options:
                    event[flag] = options[flag]
                # reschedule associated jobs in scheduler
                self.scheduler.reschedule_job(event['id'], trigger='date', run_date=datetime.fromtimestamp(event['time']))
                if event['remind']:
                    self.scheduler.reschedule_job(event['remind-id'], trigger='date', run_date=datetime.fromtimestamp(event['remind']))
            else:
                await ctx.send('Event with that name does not exist')
        else:
            await ctx.send('Must specify event name')
            return

    @commands.command(name='list', parent=event, help='List scheduled events')
    async def event_list(self, ctx: commands.Context, *event_names):
        embed_color = await self.bot.get_embed_color(ctx)
        embed = Embed(title='Scheduled Events', type='rich', color=embed_color, timestamp=datetime.utcnow())
        if self.events:
            for name in self.events:
                event = self.events[name]
                embed.add_field(name='Name', value=name)
                embed.add_field(name='Time', value=f"<t:{event['time']}:F>")
                embed.add_field(name='\u200b', value='\u200b')
                embed.add_field(name='Repeat Interval', value=f"{event['repeat']} seconds")
                embed.add_field(name='Reminder', value=f"{event['remind']} seconds prior")
                embed.add_field(name='\u200b', value='\u200b')
                attend_string = ""
                for user_id in event['attending']:
                    display_name = event['attending'][user_id]
                    attend_string += f"\n> {display_name}"
                embed.add_field(name='Attending', value=attend_string)
                absent_string = ""
                for user_id in event['absent']:
                    display_name = event['absent'][user_id]
                    absent_string += f"\n> {display_name}"
                embed.add_field(name='Absent', value=absent_string)
                embed.add_field(name='\u200b', value='\u200b', inline=False)
            embed.remove_field(len(embed.fields) - 1)
        else:
            embed.description = 'No events scheduled'
        await ctx.send(embed=embed)

    @commands.command(name='message', parent=event, help='Schedule a message to send at specified time using `HH:MM` format')
    async def schedule_message(self, ctx, message, *time_string):
        send_time = parser.parse(timestr=' '.join(time_string), fuzzy=True)
        current_time = datetime.now()
        send_delay = (send_time - datetime.now()).total_seconds()
        await ctx.send(f"It is {current_time.time().isoformat('auto')}. Sending '{message}' at {send_time.time().isoformat('auto')} in {send_delay} seconds")
        await asyncio.sleep(send_delay)
        await ctx.send(message)


    ###################
    # EVENT LISTENERS #
    ###################
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
                        with open(self.data_path, 'w') as json_file:
                            dump(self.events, json_file, indent=4)

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
                        with open(self.data_path, 'w') as json_file:
                            dump(self.events, json_file, indent=4)