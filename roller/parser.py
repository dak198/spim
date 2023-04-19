
class Token:
    """Class for storing tokens parsed from an input string"""
    def __init__(self, type, value) -> None:
        self.type = type
        self.value = value

# TODO: implement inserting parentheses in the list to indicate order of operations

def tokenize(input: str):
    i = 0
    tokens = []

    while i < len(input):
        if input[i].iswhitespace():
            i += 1
        elif input[i].isnumeric() or (
            input[i] in '.-' and (len(tokens) == 0 or tokens[-1].type == "OP" or tokens[-1].value == '(')):
            num = input[i]
            j = i + 1
            while input[j].isnumeric() or input[j] == '.':
                num += input[j]
                j += 1
            tokens.append(Token('NUM', num))
            i = j
        elif input[i] in 'd*/+-':
            tokens.append(Token('OP', input[i]))
            i += 1
        elif input[i] in '()':
            tokens.append(Token('PAREN', '('))
            i += 1
        else:
            raise ValueError(f"Unrecognized character '{input[i]}' at index {i}")
