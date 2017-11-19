#!/usr/bin/env python3
from asciisketch import AsciiSketch


def stripes():
    source = 30*('\n'.join(
        (41*'rgbGGGkkKK   fff')[begin:640 + begin] for begin in range(16)
        ) + '\n')
    im = AsciiSketch(source).image()
    im.show()
