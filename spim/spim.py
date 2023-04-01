from typing import Literal
from time import strftime
from json import load
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

import boto3
import botocore

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Spim(commands.Cog):
    """
    Cogs for Red-DiscordBot V3 for use in Gear Getaway
    """

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

        self.task = None

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)


    ####################
    # HELPER FUNCTIONS #
    ####################

    # Get the list of all EC2 instances names, DNS names, and statuses with the given filters
    #       Default to no filters
    def get_server_list(self, filters=[]):
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

    # Start the EC2 instance with the specified instance id
    def start_instance(self, inst_id):
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

    # Sets the bots status to "Streaming servers running" (it's a bit weird, but that's Discord for you)
    #       Checks every 5 minutes if servers are still running, unsets the status if they aren't
    async def set_status(self, ctx, *server_names):
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

        running = True
        while running:
            await asyncio.sleep(SLEEP_DURATION)
            running = False
            servers = self.get_server_list(filters=Filters)
            for _, _, status, _ in servers:
                if status == 'running':
                    running = True
                    break

        await self.bot.change_presence(activity=None)
        await ctx.send("Servers no longer running")


    ############
    # COMMANDS #
    ############

    # Repeats a message "times" times
    @commands.command(name='count', help='<number> - Counts from 1 to <number> with messages every 5 seconds')
    async def count(self, ctx, number):
        number = int(number)
        for i in range(number):
            await ctx.send(str(i+1))
            await asyncio.sleep(5)

    # Print the dns url for the given service, stored in an external json file on the server running the bot
    @commands.command(name='print-url', help='<name> - the name of the service to print the url for')
    async def print_url(self, ctx, name):
        server_dns = ''
        for i in self.data['urls']:
            if i['name'] == name:
                server_dns = i['url']
                break
        await ctx.channel.send(content=server_dns)

    # Print the region used for boto3 config
    @commands.command(name='print-region', help='<name> - the name of the region used in boto3 config')
    async def print_region(self, ctx):
        await ctx.channel.send(content=self.data['region'])

    # Lists the status and URL for each server with the 'Spim-Managed' Tag set to true
    @commands.command(name='server-list', help=' - Lists active and inactive servers')
    async def server_list(self, ctx, *server_names):
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
        while timer < 10:
            try:
                server_dns = ''
                for i in self.data['urls']:
                    if i['name'] == 'minecraft':
                        server_dns = i['url']
                        break
                text = 'Last Updated: {} UTC\n**NEW:** Try accessing the server by using `' + server_dns + '`\n'
                servers = self.get_server_list(filters=Filters)
                if servers:
                    for _, name, status, url in servers:
                        if not url: url = '—————'
                        text += f'```Server: {name}\nStatus: {status}\nURL:\n{url}```'
                elif len(server_names) > 1:
                    text += f'```No servers found with names:\n' + '\n'.join(server_names) + '```'
                elif len(server_names) == 1:
                    text += f'```No server found with name:\n' + '\n'.join(server_names) + '```'
                else:
                    text += '```No servers found.```'

                if not message:
                    message = await ctx.channel.send(text.format(strftime("%H:%M")))
                else:
                    await message.edit(content=text.format(strftime("%H:%M")))
                timer += 1
                await asyncio.sleep(6)
            except Exception as e:
                raise e

    # Starts the server with the specified name.
    #       Prints the status if the server is already started.
    #       Keeps users updated of server status for a few minutes afterward.
    @commands.command(name='server-start', help='[server names...] - Starts the specified server')
    async def server_start(self, ctx, *server_names):
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
                await self.server_list(ctx, *server_names)
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
            
    @commands.group(name='grouptest', help='test command groups')
    async def grouptest():
        pass

    @commands.command(name='message', parent=grouptest, help='<message> - message to send as a subcommand of the grouptest command')
    async def grouptest_message(self, ctx, message):
        await ctx.send(message)