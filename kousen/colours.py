#  MIT License
#
#  Copyright (c) 2021 ben
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.

from hikari.internal.enums import Enum

__all__: list[str] = ["Colour", "Color"]


class Colour(int, Enum):
    MAGENTA = 0xe91e63
    DARK_MAGENTA = 0xad1457

    PURPLE = 0x9b59b6
    DARK_PURPLE = 0x71368a

    LIGHT_BLUE = 0x00ccff
    BLUE = 0x3498db
    DARK_BLUE = 0x206694

    LIGHT_TEAL = 0x66ffff
    TEAL = 0x00e6e6
    DARK_TEAL = 0x009999

    LIGHT_GREEN = 0x66ff66
    GREEN = 0x00cc00
    DARK_GREEN = 0x006600

    LIGHT_YELLOW = 0xffff66
    YELLOW = 0xffff00

    GOLD = 0xffd700

    LIGHT_ORANGE = 0xffc966
    ORANGE = 0xffa500
    DARK_ORANGE = 0x996300

    LIGHT_RED = 0xff6666
    RED = 0xff0000
    DARK_RED = 0x990000

    WHITE = 0xffffff
    LIGHT_GREY = 0xB0B0B0
    LIGHT_GRAY = LIGHT_GREY
    """An alias of `LIGHT_GREY`."""
    GREY = 0x808080
    GRAY = GREY
    """An alias of `GREY`."""
    DARK_GREY = 0x505050
    DARK_GRAY = DARK_GREY
    """An alias of `DARK_GREY`."""
    DARKER_GREY = 0x282828
    DARKER_GRAY = DARKER_GREY
    """An alias of `DARKER_GREY`."""
    BLACK = 0x00000

    ORIGINAL_BLURPLE = 0x7289da
    BLURPLE = 0x5865F2
    DISCORD_RED = 0xed4245
    DISCORD_GREEN = 0x57f287
    DISCORD_YELLOW = 0xFEE75C
    DISCORD_FUCHSIA = 0xeb459e
    DISCORD_BACKGROUND = 0x36393e
    """Discord's dark theme background. For 'colourless' pointy corners on embeds."""
    EMBED_BACKGROUND = 0x2f3136
    """Discord's embed background. For 'colourless' rounded corners on embeds."""


Color = Colour
"""An alias of :obj:`kousen.colours.Colour`"""
