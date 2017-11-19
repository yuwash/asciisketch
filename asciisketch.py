#!/usr/bin/env python3
from argparse import ArgumentParser
from PIL import Image
from ruamel.yaml import YAML


def _find_next(data, sub, start=0, end=None):
    if end is None:
        end = len(data)
    while start < end:
        pos = data.find(sub, start, end)
        if pos == -1:
            return
        yield pos
        start = pos + 1


class AsciiSketch():

    encoding = {
        ' ': 0x00000000,
        'f': 0xffffffff,
        'k': 0xff000000,
        'K': 0xff888888,
        'r': 0xff000088,
        'R': 0xff0000ff,
        'g': 0xff008800,
        'G': 0xff00ff00,
        'b': 0xff880000,
        'B': 0xffff0000,
        'c': 0xff888800,
        'C': 0xffffff00,
        'm': 0xff880088,
        'M': 0xffff00ff,
        'y': 0xff008888,
        'Y': 0xff00ffff,
    }

    def __init__(self, source):
        self.source = source
        height = 0
        width = 0
        startpos = 0
        metadata_block_start = -1
        metadata = {}
        yaml = YAML(typ='safe')
        for endlpos in _find_next(source, '\n'):
            if metadata_block_start >= 0:
                if source[startpos:startpos + 4] in ('---\n', '...\n'):
                    metadata.update(
                        yaml.load(source[metadata_block_start:startpos]))
                    metadata_block_start = -1
            elif source[startpos:startpos + 4] == '---\n':
                metadata_block_start = height + 4  # without this line
            else:
                height += 1
                width = max(width, endlpos - startpos)
            startpos = endlpos + 1  # start position of next line
        # last line might not have a '\n'
        if (
                startpos < len(source)
                and source[startpos:startpos + 3] not in ('---', '...')):
            height += 1
            width = max(width, len(source) - startpos)
        self.height = height
        self.width = width
        self.mode = metadata.get('mode') or 'RGBA'
        if 'background-color' in metadata:
            color = metadata['background-color']
            if isinstance(color, int):
                self.background_color = color
            else:
                self.background_color = sum(
                    x << 8*i for i, x
                    in enumerate(metadata['background-color']))
        else:
            self.background_color = 0
        self.encoding[' '] = self.background_color

    def rows(self):
        metadata_block = False
        for row in self.source.split('\n'):
            if metadata_block:
                if row in ('---', '...'):
                    metadata_block = False
                continue
            if row == '---':
                metadata_block = True
                continue
            yield row

    def image(self):
        im = Image.new(
            mode=self.mode,
            size=(self.width, self.height),
            color=self.background_color)
        for y, line in enumerate(self.rows()):
            for x, char in enumerate(line):
                im.putpixel((x, y), self.encoding[char])
        return im


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('-o', '--output')
    args = parser.parse_args()
    with open(args.file) as sketchfile:
        source = sketchfile.read()
    aske = AsciiSketch(source)
    im = aske.image()
    if isinstance(args.output, str):
        im.save(args.output)
    else:
        im.show()
