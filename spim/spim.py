from typing import Literal
from datetime import datetime
from time import strftime
from json import load
from random import shuffle
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

import boto3
import botocore

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Spim(commands.Cog):
    """Cogs for Red-DiscordBot V3 for use in Gear Getaway"""

    def __init__(self, bot: Red) -> None:
        self.data = load(open('home/ec2-user/data.json'))
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=107557231326683136,
            force_registration=True,
        )

        self.boto_config = botocore.config.Config(
            region_name = self.data['region']
        )

        self.server_names = []

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)


    ####################
    # HELPER FUNCTIONS #
    ####################


    def get_server_list(self, filters=[]):
        """Get the list of all EC2 instances names, DNS names, and statuses with the given filters
        
        Keyword arguments:
        filters -- array of filters, defaults to no filters
        Return: list of servers
        """
        
        ec2 = boto3.client('ec2', config=self.boto_config)

        try:
            ec2.describe_instances(Filters=filters, DryRun=True)
        except botocore.exceptions.ClientError as e:
            if 'DryRunOperation' not in str(e):
                raise e
        # Dry run succeeded, call describe_instances without dryrun
        try:
            response = ec2.describe_instances(Filters=filters, DryRun=False)
        except botocore.exceptions.ClientError as e:
            raise e

        output = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        break
                name = tag['Value']
                status = instance['State']['Name']
                url = instance['PublicDnsName']
                inst_id = instance['InstanceId']
                output += [(inst_id, name, status, url)]

        return output

    def start_instance(self, inst_id):
        """Start the EC2 instance with the specified instance id
        
        Keyword arguments:
        inst_id -- the id of the instance to start
        Return: the response of ec2.start_instances for the given instance id
        """
        
        ec2 = boto3.client('ec2', config=self.boto_config)

        try:
            ec2.start_instances(InstanceIds=[inst_id], DryRun=True)
        except botocore.exceptions.ClientError as e:
            if 'DryRunOperation' not in str(e):
                raise e
        # Dry run succeeded, call start_instances without dryrun
        try:
            response = ec2.start_instances(InstanceIds=[inst_id], DryRun=False)
        except botocore.exceptions.ClientError as e:
            raise e

        return response

    async def set_status(self, ctx, *server_names):
        """Sets the bots status to "Streaming servers running" (it's a bit weird, but that's Discord for you)
            Checks every 5 minutes if servers are still running, unsets the status if they aren't
        
        Keyword arguments:
        server_names -- optional list of running servers to print to chat
        """
        
        SLEEP_DURATION = 5*60

        if server_names:
            Filters = [ {
                'Name': 'tag:Spim-Managed',
                'Values': ['true']
            }, {
                'Name': 'tag:Name',
                'Values': server_names
            } ]
        else:
            Filters = [ {
                'Name': 'tag:Spim-Managed',
                'Values': ['true']
            } ]

        # Set bot status to show that servers are running
        await self.bot.change_presence(activity=discord.Game('servers running'))

        # Print server list to chat
        await self.server_list(ctx, *server_names)

        running = True
        while running:
            running = False
            servers = self.get_server_list(filters=Filters)
            for _, _, status, _ in servers:
                if status == 'running':
                    running = True
                    break
            await asyncio.sleep(SLEEP_DURATION)

        await self.bot.change_presence(activity=None)
        embed = discord.Embed(description="Servers no longer running", timestamp=datetime.utcnow())
        await ctx.send(embed=embed)


    ####################
    # GENERAL COMMANDS #
    ####################

    @commands.command(name='spimify', help='Reacts with every Spim emote to a message you reply to with this command')
    async def spimify(self, ctx):
        """Reacts with every spim emote to a replied message"""
        
        spims = ['<:spimPog:772261869858848779>', '<:spimPogR:775434707231047680>', '<:spimBall:1066624826086793366>', '<:spimPride:988519886479327242>', '<:spimThink:949780590121607209>', '<:spinta:1041857241600507924>']
        shuffle(spims)
        channel = ctx.channel
        message = await channel.fetch_message(ctx.message.reference.message_id)
        await ctx.message.delete()
        for s in spims:
            await message.add_reaction(s)
    
    @commands.command(name='spimpoll', help='Creates a poll with <:spimPog:772261869858848779> <:spimPause:987933390110089216> <:spon:922922345134424116>')
    async def spimpoll(self, ctx, *poll_text):
        """Create a poll with the given text

        Keyword arguments:
        *poll_text -- text of the poll message
        """

        spims = ['<:spimPog:772261869858848779>', '<:spimPause:987933390110089216>', '<:spon:922922345134424116>']
        channel = ctx.channel
        if poll_text:
            await ctx.message.delete()
            poll_message = await ctx.send(' '.join(poll_text))
            for s in spims:
                await poll_message.add_reaction(s)

    @commands.command(name='say', help='Enter a message for Spim to say')
    async def say(self, ctx, *message_text):
        """Enter a message for the bot to say
        
        Keyword arguments:
        *message_text -- text of the message
        """
        
        await ctx.message.delete()
        if message_text:
            await ctx.send(' '.join(message_text))
        else:
            await ctx.send('<:spimPog:772261869858848779>')


    ###################
    # SERVER COMMANDS #
    ###################

    @commands.group(name='server', help='Commands for AWS server management')
    async def server(self, ctx):
        """Group for server commands"""
        pass

    @commands.command(name='url', parent=server, help='Print the url currently used for servers managed by Spim')
    async def print_url(self, ctx):
        """Print the dns url for the given service, stored in an external json file on the server running the bot"""
        server_dns = self.data['url']
        await ctx.channel.send(f'`{server_dns}`')

    @commands.command(name='region', parent=server, help='Print the name of the region used in boto3 config')
    async def print_region(self, ctx):
        """Print the region used for boto3 config"""
        await ctx.channel.send(content=self.data['region'])

    @commands.command(name='list', parent=server, help='List active and inactive servers')
    async def server_list(self, ctx: commands.Context, *server_names):
        """Lists the status and URL for each server with the 'Spim-Managed' Tag set to true
        
        Keyword arguments:
        server_names -- optional list of server names to list
        """
        
        SLEEP_DURATION = 20
        UPDATE_COUNT = 6

        if server_names:
            Filters = [ {
                'Name': 'tag:Spim-Managed',
                'Values': [ 'true' ]
            }, {
                'Name': 'tag:Name',
                'Values': server_names
            } ]
        else:
            Filters = [ {
                'Name': 'tag:Spim-Managed',
                'Values': [ 'true' ]
            } ]

        timer = 0
        message = None
        while timer < UPDATE_COUNT:
            try:
                server_dns =  self.data['url']
                embed_description = '**NEW:** Try accessing the server by using `' + server_dns + '`\n'
                embed_color = await self.bot.get_embed_color(ctx)
                embed = discord.Embed(title='Active Servers', type='rich', color=embed_color, description=embed_description, timestamp=datetime.utcnow())
                servers = self.get_server_list(filters=Filters)
                if servers:
                    for _, name, status, url in servers:
                        if not url: url = '—————'
                        text = f'```Status: {status}\nURL:\n{url}```'
                        embed.add_field(name=name, value=text)
                elif len(server_names) > 1:
                    text = 'No servers found with names:'
                    embed.add_field(name=text, value='\n'.join(server_names))
                elif len(server_names) == 1:
                    text = 'No server found with name:'
                    embed.add_field(name=text, value='\n'.join(server_names))
                else:
                    text += 'No servers found.'
                    embed.add_field(name=text)

                if not message:
                    message = await ctx.send(embed=embed)
                else:
                    await message.edit(embed=embed)
                timer += 1
                await asyncio.sleep(SLEEP_DURATION)
            except Exception as e:
                raise e

    @commands.command(name='start', parent=server, help='Start the specified servers')
    async def server_start(self, ctx, *server_names):
        """Starts the server with the specified name
            Prints the status if the server is already started.
            Keeps users updated of server status for a few minutes afterward.
        Keyword arguments:
        server_names -- optional list of server names to attempt to start
        """
        
        if not server_names:
            if self.server_names:
                server_names = self.server_names
            else:
                await ctx.send('You fool! No server names specified or in cache.')
                return

        Filters = [ {
            'Name': 'tag:Spim-Managed',
            'Values': [ 'true' ]
        }, {
            'Name': 'tag:Name',
            'Values': server_names
        } ]

        try:
            servers = self.get_server_list(filters=Filters)
            if servers:
                self.server_names = server_names
                for inst_id, _, status, _ in servers:
                    if status == 'stopped':
                        self.start_instance(inst_id)
                await self.set_status(ctx, *server_names)
            elif len(server_names) > 1:
                await ctx.send(f'```No servers found with names:\n' + '\n'.join(server_names) + '```')
            else:
                await ctx.send(f'```No server found with name:\n' + '\n'.join(server_names) + '```')
        except botocore.exceptions.ClientError as error:
            if error.response['Error']['Code'] == 'IncorrectSpotRequestState':
                ctx.send(f'```No Spot capacity available at the moment. Please try again in a few minutes.```')
            else:
                raise error