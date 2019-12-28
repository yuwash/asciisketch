#!/usr/bin/env python3
from argparse import ArgumentParser
from PIL import Image, ImageDraw
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
        self.fill_methods = [
            {
                'rectangle': fill_rectangle,
                'ellipse': fill_ellipse,
                'secchi': fill_secchi,
                'leaf': fill_leaf,
                'oscar': fill_oscar,
            }[fill_method]
            for fill_method in metadata.get('fill-methods', ['rectangle'])]
        self.depth = len(self.fill_methods)
        self.width //= self.depth
        self.encoding[' '] = self.background_color

    @classmethod
    def from_file(cls, path):
        """
        >>> from hashlib import sha1
        >>> aske = AsciiSketch.from_file('examples/camel.aske')
        >>> sha1(aske.image().tobytes()).hexdigest()
        '5fd38b80890fb9ef47681b1d3334c42e94ba9b52'
        """
        with open(path) as sketchfile:
            source = sketchfile.read()
        return cls(source)

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

    def image(self, scale_x=1, scale_y=None):
        if scale_y is None:
            scale_y = scale_x
        im = Image.new(
            mode=self.mode,
            size=(scale_x*self.width, scale_y*self.height),
            color=self.background_color)
        draw = ImageDraw.Draw(im)
        for i, fill_method in enumerate(self.fill_methods):
            for y, line in enumerate(self.rows()):
                for x, char in enumerate(
                        line[i:len(line):len(self.fill_methods)]):
                    fill_method(
                        draw,
                        (scale_x*x, scale_y*y,
                         scale_x*(x + 1) - 1, scale_y*(y + 1) - 1),
                        fill=self.encoding[char])
        return im


def fill_rectangle(imagedraw, xy, *args, **kwargs):
    return imagedraw.rectangle(xy, *args, **kwargs)


def fill_ellipse(imagedraw, xy, *args, **kwargs):
    return imagedraw.ellipse(xy, *args, **kwargs)


def fill_secchi(imagedraw, xy, *args, **kwargs):
    return [
        imagedraw.pieslice(xy, start, start + 90, *args, **kwargs)
        for start in (-90, 90)]


def fill_leaf(imagedraw, xy, *args, **kwargs):
    scale_x = xy[2] - xy[0]
    scale_y = xy[3] - xy[1]
    return [
        imagedraw.chord(
            scale_xy(shift_xy(xy, shift_x, shift_y), scale_x, scale_y),
            start, start + 90, *args, **kwargs)
        for start, shift_x, shift_y
        in [(-90, -scale_x, 0), (90, 0, -scale_y)]]


def fill_oscar(imagedraw, xy, *args, **kwargs):
    top_right = [xy[2], xy[1]]
    return imagedraw.polygon(list(xy) + top_right, *args, **kwargs)


def shift_xy(xy, shift_x, shift_y):
    return [x_or_y + shift for x_or_y, shift in zip(xy, 2*[shift_x, shift_y])]


def scale_xy(xy, add_x, add_y):
    return xy[:2] + [xy[2] + add_x, xy[3] + add_y]


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('-o', '--output')
    parser.add_argument('--scale', type=int, default=1)
    args = parser.parse_args()
    aske = AsciiSketch.from_file(args.file)
    im = aske.image(scale_x=args.scale)
    if isinstance(args.output, str):
        im.save(args.output)
    else:
        im.show()
