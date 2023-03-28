from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

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

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    @commands.command()
    async def foo(self, ctx):
        await ctx.send("Hello World!")

    @commands.command()
    async def bar(self, ctx):
        await ctx.send("Bepis gaming")