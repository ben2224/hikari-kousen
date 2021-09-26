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

__all__: list[str] = ["Colour", "Color"]


class Colour:
    MAGENTA: int = 0xe91e63
    DARK_MAGENTA: int = 0xad1457

    PURPLE: int = 0x9b59b6
    DARK_PURPLE: int = 0x71368a

    LIGHT_BLUE: int = 0x00ccff
    BLUE: int = 0x3498db
    DARK_BLUE: int = 0x206694

    LIGHT_TEAL: int = 0x66ffff
    TEAL: int = 0x00e6e6
    DARK_TEAL: int = 0x009999

    LIGHT_GREEN: int = 0x66ff66
    GREEN: int = 0x00cc00
    DARK_GREEN: int = 0x006600

    LIGHT_YELLOW: int = 0xffff66
    YELLOW: int = 0xffff00

    GOLD: int = 0xffd700

    LIGHT_ORANGE: int = 0xffc966
    ORANGE: int = 0xffa500
    DARK_ORANGE: int = 0x996300

    LIGHT_RED: int = 0xff6666
    RED: int = 0xff0000
    DARK_RED: int = 0x990000

    WHITE: int = 0xffffff
    LIGHT_GREY: int = 0xB0B0B0
    GREY: int = 0x808080
    DARK_GREY: int = 0x505050
    DARKER_GREY: int = 0x282828
    BLACK: int = 0x00000
    DARK_GRAY = DARK_GREY
    LIGHT_GRAY = LIGHT_GREY
    DARKER_GRAY = DARKER_GREY

    ORIGINAL_BLURPLE: int = 0x7289da
    BLURPLE: int = 0x5865F2
    DISCORD_RED: int = 0xed4245
    DISCORD_GREEN: int = 0x57f287
    DISCORD_YELLOW: int = 0xFEE75C
    DISCORD_FUCHSIA: int = 0xeb459e
    DISCORD_BACKGROUND: int = 0x36393e
    """Discord's dark theme background. For 'colourless' pointy corners on embeds."""
    EMBED_BACKGROUND: int = 0x2f3136
    """Discord's embed background. For 'colourless' rounded corners on embeds."""


Color = Colour
"""An alias of :obj:`kousen.colours.Colour`"""
