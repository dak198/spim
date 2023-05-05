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

from discord import Embed, AllowedMentions
from redbot.core import commands, data_manager
from redbot.core.bot import Red
from redbot.core.config import Config

# default time string for new events
DEFAULT_TIMESTR = 'Saturday at 3:00pm'

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

    def cog_unload(self):
        self.scheduler.shutdown()

    ####################
    # HELPER FUNCTIONS #
    ####################

    def new_event(self, **kwargs) -> dict[str]:
        if 'channel_id' in kwargs:
            channel_id = kwargs['channel_id']
        else:
            channel_id = 661373412400431104
        return {
            'id': uuid4().hex,
            'remind-id': uuid4().hex,
            'channel-id': channel_id,
            'message-id': None,
            'time': int(round(parser.parse(timestr=DEFAULT_TIMESTR, fuzzy=True).timestamp())),
            'repeat': None,
            'remind': None,
            'notify': False,
            'attending': {},
            'absent': {}
        }

    async def parse_args(self, ctx: commands.Context, *args) -> tuple[str, dict]:
        """Parse arguments from a given string and use them to generate an event
        
        Keyword arguments:
        ctx -- context passed from the command method that called parse_args
        *args -- tuple containing pairs of flags and values. Flags should be marked with leading '--' and immediately followed by their corresponding value.
        Return: tuple containing the event name and dict representing the event
        """
        
        # pair up the positional arguments into a dict
        args_dict = {}
        for group in grouper(args, 2, fillvalue=None):
            flag, arg = group
            if str(flag).startswith('--'):
                args_dict[flag[2:]] = arg
            else:
                await ctx.send(f"Error: Flag `{flag}` must start with `--`")
                return

        # extract event name from args, returning if no name was provided
        if not (name := str(args_dict.pop('name', None))):
            await ctx.send("Error: Must provide `--name`")
            return
        
        # attempt to get the event with the given name from events list, generating a new event if no such event exists
        if name in self.events:
            event = self.events[name]
        else:
            event = self.new_event(channel_id=ctx.channel.id)

        # check for invalid args
        for arg in args_dict:
            if arg not in event:
                await ctx.send(f"Error: Flag `--{arg}` not recognized")
                return

        # handle args that have a different internal representation than the provided string
        if 'channel-id' in args_dict:
            event['channel-id'] = int(args_dict['channel-id'])
        if 'time' in args_dict:
            args_dict['time'] = int(round(parser.parse(timestr=args_dict['time'], fuzzy=True).timestamp()))
        elif not name in self.events:
            await ctx.send(f"`--time` not provided, defaulting to <t:{int(round(parser.parse(timestr=DEFAULT_TIMESTR, fuzzy=True).timestamp()))}:F>")
        if 'repeat' in args_dict and (repeat := parse(args_dict['repeat'], granularity='minutes')) > 0:
            args_dict['repeat'] = repeat
        if 'remind' in args_dict and (remind := parse(args_dict['remind'], granularity='minutes')) > 0:
            args_dict['remind'] = remind
        if 'notify' in args_dict:
            notify = args_dict['notify'].tolower()
            if notify == 'true':
                args_dict['notify'] = True
            elif notify == 'false':
                args_dict['notify'] = False
            else:
                args_dict.pop('notify', None)

        # replace event attributes with the ones specified in args
        for arg in args_dict:
            event[arg] = args_dict[arg]

        return name, event

    async def send_reminder(self, name: str):
        event = self.events[name]
        # convert event time string to UTC timestamp
        timestamp = event['time']
        # add @everyone to the reminder string if enabled
        if event['notify']:
            notify = "@everyone "
            allowed_mentions = AllowedMentions(everyone=True)
        else:
            allowed_mentions = None
            notify=""
        # send reminder string
        reminder_string = f"{notify}**{name}** starting <t:{timestamp}:F>"
        message = await self.bot.get_channel(event['channel-id']).send(reminder_string, allowed_mentions=allowed_mentions)
        # save reminder message id to event data and output to json file
        message_id = message.id
        event['message-id'] = message_id
        with open(self.data_path, 'w') as json_file:
            dump(self.events, json_file, indent=4)
        # add reactions to reminder message for users to indicate 'attending' or 'absent'
        await message.add_reaction('<:spimPog:772261869858848779>')
        await message.add_reaction('<:spon:922922345134424116>')
        if event['repeat']:
            self.scheduler.add_job(self.send_reminder, 'date', run_date=datetime.fromtimestamp(event['time'] - event['remind'] + event['repeat']), args=[name], id=event['remind-id'])

    async def send_event(self, name: str):
        event = self.events[name]
        if event['notify']:
            notify = "@everyone "
            allowed_mentions = AllowedMentions(everyone=True)
        else:
            notify = ""
            allowed_mentions = None
        await self.bot.get_channel(event['channel-id']).send(f"{notify}**{name}** starting now", allowed_mentions=allowed_mentions)
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


    ##################
    # EVENT COMMANDS #
    ##################

    @commands.command(name='print-jobs', help='Print all jobs from the scheduler')
    async def print_jobs(self, ctx: commands.Context):
        await ctx.send(f"`{str(self.scheduler.get_jobs())}`")

    @commands.group(name='event', invoke_without_command=True, help='Schedule a new event or edit an existing one')
    async def event(self, ctx: commands.Context, *args):
        # create an event using provided arguments and add it to the event list
        name, event = await self.parse_args(ctx, *args)
        self.events[name] = event

        # update event list in external file
        with open(self.data_path, 'w') as json_file:
            dump(self.events, json_file, indent=4)

        # add jobs for sending event and reminder info, or reschedule them if they already exist
        if self.scheduler.get_job(event['remind-id']):
            if event['remind'] and (remind_time := event['time'] - event['remind']) > datetime.now().timestamp():
                self.scheduler.reschedule_job(event['remind-id'], trigger='date', run_date=datetime.fromtimestamp(remind_time))
            elif event['repeat']:
                self.scheduler.reschedule_job(event['remind-id'], trigger='date', run_date=datetime.fromtimestamp(remind_time + event['repeat']))
        else:
            if event['remind'] and (remind_time := event['time'] - event['remind']) > datetime.now().timestamp():
                self.scheduler.add_job(self.send_reminder, 'date', run_date=datetime.fromtimestamp(remind_time), args=[name], id=event['remind-id'])
            elif event['repeat']:
                self.scheduler.add_job(event['remind-id'], trigger='date', run_date=datetime.fromtimestamp(remind_time + event['repeat']))
        if self.scheduler.get_job(event['id']):
            self.scheduler.reschedule_job(event['id'], trigger='date', run_date=datetime.fromtimestamp(event['time']))
        else:
            self.scheduler.add_job(self.send_event, 'date', run_date=datetime.fromtimestamp(event['time']), args=[name], id=event['id'])

        # print event info to the chat
        await self.event_list(ctx, name)

    @commands.command(name='cancel', parent=event, help='Cancel a scheduled event')
    async def event_cancel(self, ctx, name):
        if self.remove_event(name):
            await ctx.send(f"Removed {name}")
        else:
            await ctx.send(f"`{name}` not found in events list")

    @commands.command(name='list', parent=event, help='List scheduled events')
    async def event_list(self, ctx: commands.Context, *event_names):
        embed_color = await self.bot.get_embed_color(ctx)
        embed = Embed(title='Scheduled Events', type='rich', color=embed_color, timestamp=datetime.utcnow())
        if event_names:
            events = event_names
        else:
            events = self.events
        if events:
            for name in events:
                if name in self.events:
                    event = self.events[name]
                    embed.add_field(name='Name', value=name)
                    embed.add_field(name='Time', value=f"<t:{event['time']}:F>")
                    embed.add_field(name='\u200b', value='\u200b')
                    embed.add_field(name='Repeat Interval', value=f"{event['repeat']} seconds")
                    embed.add_field(name='Reminder', value=f"{event['remind']} seconds prior")
                    if event['notify']:
                        embed.add_field(name='Notify', value='Yes')
                    else:
                        embed.add_field(name='Notify', value='No')
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
                else:
                    ctx.send(f"Error: `{name}` not found in events list")
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