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
        message_string = result
        for die in result['rolls']:
            message_string += f"\n{die}: {' '.join(result['rolls'][die])}"
        await ctx.send(message_string)

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

def validate_parens(string: str):
    stack = []

    for c in string:
        if c == '(':
            stack.append('(')
        elif c == ')':
            if len(stack) > 0:
                stack.pop()
            else:
                return False

    return len(stack) == 0

class Expression:

    def __init__(self, expr_string: str):
        self.const = None

        # remove all leading and trailing parentheses from expression string
        while expr_string[0] == '(' and expr_string[-1] == ')' and validate_parens(expr_string[1:-1]):
            expr_string = expr_string[1:-1]

        # list of supported operators
        ops = ['+', '-', '*', '/', 'd']
        # loop through operations in order of precedence
        for op in ops:
            # find an instance of the operator that is not inside parentheses if possible
            op_index = expr_string.find(op)
            while inside_paren(expr_string, op_index) and op_index >= 0:
                op_index = expr_string.find(op, op_index + 1, len(expr_string) - 1)
            # if there is an instance of the operator outside parentheses, split the expression
            # into two new expressions that are linked by the operator
            if op_index >= 0:
                self.a = Expression(expr_string[:op_index])
                self.b = Expression(expr_string[op_index + 1:])
                self.op = op
                return
        # if no supported operators are found, attempt to process the expression as a constant
        if expr_string.replace('.', '').isdigit():
            if float(expr_string) == int(expr_string):
                self.const = int(expr_string)
            else:
                self.const = float(expr_string)
        # if there are no operators found and the expression is not a constant, raise an error
        else:
            raise ValueError(f"No operator or constant found in string '{expr_string}'")

    def __repr__(self):
        if self.const:
            return repr(self.const)
        else:
            return f"{repr(self.a)}{self.op}{repr(self.b)}"

    def evaluate(self):
        result = {
            'res': None,
            'rolls': {}
        }
        if self.const:
            result['res'] = self.const
        else:
            a = self.a.evaluate()
            b = self.b.evaluate()
            if self.op == '+':
                result['res'] = a + b
            elif self.op == '-':
                result['res'] = a - b
            elif self.op == '*':
                result = a * b
            elif self.op == '/':
                result['res'] = a / b
            elif self.op == '^':
                result['res'] = pow(a, b)
            elif self.op == 'd':
                result['res'] = 0
                for i in range(a):
                    roll = random.randint(1, b)
                    result['res'] += roll
                    if not b in result['rolls']:
                        die = 'd' + b
                        result['rolls'][die] = []
                    result['rolls'][die].append(roll)
            else:
                raise ValueError(f"Unsupported op '{self.op}'")
            
            # represent float as int if result is integer
            if result['res'] == math.ceil(result['res']):
                result['res'] = math.ceil(result['res'])
        return result