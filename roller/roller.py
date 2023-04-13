import random
import re

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config


class Roller(commands.Cog):
    """Cogs for Red-DiscordBot V3 for use in Gear Getaway"""

    def __init__(self, bot: Red) -> None:
        self.bot = bot


    @commands.command(name="roll", help="output a random roll for a given combination of dice")
    async def roll(self, ctx, *input_string):
        a = input_string[0]
        b = input_string[2]
        op = input_string[1]
        expression = self.Expression(a, b, op)
        result = expression.evaluate()
        await ctx.send(f'{a} {op} {b} = {result}')

    class Expression:

        def __init__(self, a, b, op):
            if not isinstance(a, type(self)):
                raise TypeError(f"Invalid argument: {type(a)} is not instance of Expression")
            if not isinstance(b, type(self)):
                raise TypeError(f"Invalid argument: {type(b)} is not instance of Expression")
            self.op = op
            self.a = a
            self.b = b

        def __init__(self, const):
            self.const = const

        def evaluate(self):
            if self.const:
                return self.const
            else:
                a = self.a.evaluate()
                b = self.b.evaluate()
                if self.op == '+':
                    return a + b
                elif self.op == '-':
                    return a - b
                elif self.op == '*':
                    return a * b
                elif self.op == '/':
                    return a / b
                elif self.op == '^':
                    return pow(a, b)
                else:
                    raise ValueError(f"Unsupported op '{self.op}'")