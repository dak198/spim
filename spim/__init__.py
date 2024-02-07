import json
import discord
from pathlib import Path
from redbot.core.bot import Red
from .spim import Spim, spimify, poll

with open(Path(__file__).parent / "info.json") as fp:
    __red_end_user_data_statement__ = json.load(fp)["end_user_data_statement"]


async def setup(bot: Red) -> None:
    await bot.add_cog(Spim(bot))
    bot.tree.add_command(spimify)
    bot.tree.add_command(poll)

async def teardown(bot: Red):
    bot.tree.remove_command("Spimify", type=discord.AppCommandType.user)
    bot.tree.remove_command("Poll", type=discord.AppCommandType.user)