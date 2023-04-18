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
        expression = Expression(input_string)
        result = expression.evaluate()
        await ctx.send(result)

def inside_paren(expr_string: str, index: int):
    """Determines if a given index in a string is inside a set of parentheses
    
    Keyword arguments:
    expr_string -- string that may contain parentheses
    index -- index to check
    Return: True if index is inside at least one set of parentheses, False otherwise
    """
    
    leading = {
        # number of '(' characters before the index
        '(': expr_string.count('(', 0, index - 1),
        # number of ')' characters before the index
        ')': expr_string.count(')', 0, index - 1)
    }
    trailing = {
        # number of '(' characters after the index
        '(': expr_string.count('(', index + 1, len(expr_string) - 1),
        # number of ')' characters after the index
        ')': expr_string.count(')', index + 1, len(expr_string) -1)
    }
    # if there is at least 1 unpaired open paren before the index and at least one unpaired closing paren after the index, then the index is inside parentheses
    return leading['('] - leading[')'] >= 1 and trailing[')'] - trailing['('] >= 1

class Expression:

    def __init__(self, expr_string: str):
        self.const = None
        # remove all leading and trailing parentheses from expression string
        expr_string = expr_string.strip('()')
        ops = {
            '+': expr_string.find('+'),
            '-': expr_string.find('-'),
            '*': expr_string.find('*'),
            '/': expr_string.find('/'),
            'd': expr_string.find('d')
        }
        if ops['+'] >= 0 and not inside_paren(expr_string, ops['+']):
            expr = expr_string.split('+', 1)
            self.a = Expression(expr[0])
            self.b = Expression(expr[1])
            self.op = '+'
        elif ops['-'] >= 0 and not inside_paren(expr_string, ops['-']):
            expr = expr_string.split('-', 1)
            self.a = Expression(expr[0])
            self.b = Expression(expr[1])
            self.op = '-'
        elif ops['*'] >= 0 and not inside_paren(expr_string, ops['*']):
            expr = expr_string.split('*', 1)
            self.a = Expression(expr[0])
            self.b = Expression(expr[1])
            self.op = '*'
        elif ops['/'] >= 0 and not inside_paren(expr_string, ops['/']):
            expr = expr_string.split('/', 1)
            self.a = Expression(expr[0])
            self.b = Expression(expr[1])
            self.op = '/'
        elif ops['d'] >= 0 and not inside_paren(expr_string, ops['d']):
            expr = expr_string.split('d', 1)
            if expr[0] == '':
                expr[0] = '1'
            self.a = Expression(expr[0])
            self.b = Expression(expr[1])
            self.op = 'd'
        elif expr_string.replace('.', '').isdigit():
            if float(expr_string) == int(expr_string):
                self.const = int(expr_string)
            else:
                self.const = float(expr_string)
        else:
            raise ValueError(f"No operator or constant found in string '{expr_string}'")

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
                result = a + b
            elif self.op == '-':
                result = a - b
            elif self.op == '*':
                result = a * b
            elif self.op == '/':
                result = a / b
            elif self.op == '^':
                result = pow(a, b)
            elif self.op == 'd':
                result = 0
                for i in range(a):
                    result += random.randint(1, b)
            else:
                raise ValueError(f"Unsupported op '{self.op}'")
            
            # represent float as int if result is integer
            if result == math.ceil(result):
                    return math.ceil(result)
            else:
                return result