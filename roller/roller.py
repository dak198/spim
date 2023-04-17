import random
import re
import math

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
        # remove all whitespace from input string
        input_string = ''.join(input_string)
        expression = self.Expression(input_string)
        await ctx.send(expression)
        result = expression.evaluate()
        await ctx.send(result)

    class Expression:

        def __init__(self, expr_string: str):
            if expr_string.find('+') >= 0:
                expr = expr_string.split('+', 1)
                self.a = self.__init__(expr[0])
                self.b = self.__init__(expr[1])
                self.op = '+'
            elif expr_string.find('-') >= 0:
                expr = expr_string.split('-', 1)
                self.a = self.__init__(expr[0])
                self.b = self.__init__(expr[1])
                self.op = '-'
            elif expr_string.find('*') >= 0:
                expr = expr_string.split('*', 1)
                self.a = self.__init__(expr[0])
                self.b = self.__init__(expr[1])
                self.op = '*'
            elif expr_string.find('/') >= 0:
                expr = expr_string.split('/', 1)
                self.a = self.__init__(expr[0])
                self.b = self.__init__(expr[1])
                self.op = '/'
            elif expr_string.find('d') >= 0:
                expr = expr_string.split('d', 1)
                self.a = self.__init__(expr[0])
                self.b = self.__init__(expr[1])
                self.op = 'd'
            elif expr_string.replace('.', '').isdigit():
                if float(expr_string) == int(expr_string):
                    self.const = int(expr_string)
                else:
                    self.const = float(expr_string)
            else:
                raise ValueError(f"No operator or constant found in string '{expr_string}'")

            # if len(args) == 1:
            #     self.const = args[0]
            #     self.a = self.b = self.op = None
            # elif len(args) == 3:
            #     a = args[0]
            #     b = args[1]
            #     op = args[2]
            #     if not isinstance(a, type(self)):
            #         raise TypeError(f"Invalid argument: {type(a)} is not instance of Expression")
            #     if not isinstance(b, type(self)):
            #         raise TypeError(f"Invalid argument: {type(b)} is not instance of Expression")
            #     self.op = op
            #     self.a = a
            #     self.b = b
            #     self.const = None
            # else:
            #     raise TypeError(f"__init__() takes 1 or 3 arguments but {len(args)} were given")

        def __repr__(self):
            if self.const:
                return repr(self.const)
            else:
                return f"{repr(self.a)}{self.op}{repr(self.b)}"

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
                    result = a / b
                    if result == math.ceil(result):
                        return math.ceil(result)
                    else:
                        return result
                elif self.op == '^':
                    return pow(a, b)
                elif self.op == 'd':
                    result = 0
                    for i in range(a):
                        result += random.randint(1, b)
                    return result
                else:
                    raise ValueError(f"Unsupported op '{self.op}'")