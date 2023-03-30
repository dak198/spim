from typing import Literal
from time import sleep, strftime
from datetime import datetime

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config as BotoConfig

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Spim(commands.Cog):
    """
    Cogs for Red-DiscordBot V3 for use in Gear Getaway
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=107557231326683136,
            force_registration=True,
        )

        self.boto_config = BotoConfig(
            region_name = 'us-east-1'
        )


    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    # Get the list of all EC2 instances names, DNS names, and statuses with the given filters
    #       Default to no filters
    def get_server_list(self, filters=[]):
        ec2 = boto3.client('ec2', config=self.boto_config)

        try:
            ec2.describe_instances(Filters=filters, DryRun=True)
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                raise e
        # Dry run succeeded, call describe_instances without dryrun
        try:
            response = ec2.describe_instances(Filters=filters, DryRun=False)
        except ClientError as e:
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
    def start_instance(inst_id):
        ec2 = boto3.client('ec2')

        try:
            ec2.start_instances(InstanceIds=[inst_id], DryRun=True)
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                raise e
        # Dry run succeeded, call start_instances without dryrun
        try:
            response = ec2.start_instances(InstanceIds=[inst_id], DryRun=False)
        except ClientError as e:
            raise e

        return response


    ## COMMANDS

    # Check version of spim cog
    @commands.command(name='spim-version')
    async def version(self, ctx):
        await ctx.send("Spim cog version: 0.1.0")

    # Lists the status and URL for each server with the 'mc-server' Project Tag
    @commands.command(name='server-list', help=' - Lists active and inactive servers')
    async def server_status(self, ctx):
        timer = 0
        message = None
        while timer < 10:
            try:
                text = 'Last Updated: {} UTC\n'
                servers = self.get_server_list(filters = [ {
                        'Name': 'tag:Project',
                        'Values': [ 'mc-server' ] } ])
                if servers:
                    for _, name, status, url in servers:
                        if not url: url = '—————'
                        text += f'```Server: {name}\nStatus: {status}\nURL:\n{url}```'
                else:
                    text += '```No servers running.```'

                if not message:
                    message = await ctx.channel.send(text.format(strftime("%H:%M")))
                else:
                    await message.edit(content=text.format(strftime("%H:%M")))
                timer += 1
                sleep(1)
            except Exception as e:
                raise e


    # Starts the server with the specified name.
    #       Prints the status if the server is already started.
    #       Keeps users updated of server status for a few minutes afterward.
    @commands.command(name='server-start', help='<server name> - Starts the specified server')
    async def server_start(self, ctx, server_name):
        Filters = [ {
            'Name': 'tag:Project',
            'Values': [ 'mc-server' ]
        }, {
            'Name': 'tag:Name',
            'Values': [ server_name ]
        } ]

        timer = 0
        message = None
        while timer < 10:
            try:
                text = 'Last Updated: {} UTC\n**NEW:** Try accessing the server by using `geargetaway.duckdns.org`\n'
                servers = self.get_server_list(filters=Filters)
                if servers:
                    for inst_id, name, status, url in servers:
                        if status == 'stopped':
                            self.start_instance(inst_id)
                        if not url: url = '—————'
                        text += f'```Server: {name}\nStatus: {status}\nURL:\n{url}```'
                else:
                    text += f'**ERROR: No servers found named `{server_name}`.**\nCommand usage:\n`{bot.command_prefix}server-start <server name>`\nUse `{bot.command_prefix}server-list` to list valid server names'

                if not message:
                    message = await ctx.channel.send(text.format(strftime("%H:%M")))
                else:
                    await message.edit(content=text.format(strftime("%H:%M")))
                timer += 1
                sleep(1)
            except Exception as e:
                raise e
    
    # Test for setting the activity status
    @commands.command(name='set-activity', help='<game> - set specified game as status')
    async def set_activity(self, ctx, game):
        try:
            await self.change_presence(status=discord.Status.idle, activity=discord.Game(game))
        except Exception as e:
            raise e