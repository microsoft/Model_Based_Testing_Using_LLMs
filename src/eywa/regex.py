from typing import List
import re


class Regex(object):
    """
    A regular expression.
    """
    pass


class Empty(Regex):
    """
    A regular expression that matches the empty string.
    """

    def __str__(self) -> str:
        return ""


class Range(Regex):
    """
    A regular expression that matches a character range.
    """

    def __init__(self, low: str, high: str):
        if len(low) != 1 or len(high) != 1:
            raise ValueError("Range must be single characters")
        self.low = low
        self.high = high

    def __str__(self) -> str:
        return f'[{self.low}-{self.high}]'


class Choice(Regex):
    """
    A regular expression that matches a choice of regular expressions.
    """

    def __init__(self, *args: List[Regex]):
        if len(args) < 2:
            raise ValueError("Or must have at least two expressions")
        self.exprs = args

    def __str__(self) -> str:
        return f'({"|".join([str(e) for e in self.exprs])})'


class Seq(Regex):
    """
    A regular expression that matches a sequence of regular expressions.
    """

    def __init__(self, *args: List[Regex]):
        if len(args) < 2:
            raise ValueError("Seq must have at least two expressions")
        self.exprs = args

    def __str__(self) -> str:
        return f'({"".join([str(e) for e in self.exprs])})'


class Star(Regex):
    """
    A regular expression that matches zero or more iterations of a regular expression.
    """

    def __init__(self, r: Regex):
        self.expr = r

    def __str__(self) -> str:
        return f'({str(self.expr)})*'


def chars(low: str, high: str) -> Regex:
    """
    A regular that matches a character range.
    """
    return Range(low, high)


def text(s: str) -> Regex:
    """
    A regular that matches an exact string.
    """
    if s == "":
        return empty()
    elif len(s) == 1:
        return chars(s, s)
    else:
        return seq(*[chars(c, c) for c in s])


def choice(*args: List[Regex]) -> Regex:
    """
    A regular expression that matches a choice of regular expressions.
    """
    return Choice(*args)


def seq(*args: List[Regex]) -> Regex:
    """
    A regular expression that matches a sequence of regular expressions.
    """
    return Seq(*args)


def star(r: Regex) -> Regex:
    """
    A regular expression that matches zero or more iterations of a regular expression.
    """
    return Star(r)


def plus(r: Regex) -> Regex:
    """
    A regular expression that matches one or more iterations of a regular expression.
    """
    return seq(r, star(r))


def empty() -> Empty:
    """
    A regular expression that matches the empty string.
    """
    return Empty()


def ismatch(r: Regex, s: str) -> bool:
    """
    Determine if a string matches a regular expression.
    """
    regex = '^' + str(r) + '$'
    return re.match(regex, s) is not None
