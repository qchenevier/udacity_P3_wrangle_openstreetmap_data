import xml.etree.cElementTree as ET

from builtins import * # python 2 compatibility
from pprint import pprint
from collections import Counter


def get_cursor(file_handler):
    return ET.iterparse(file_handler, events=('start','end'))


def get_tags(filename, levels=False):
    with open(filename) as f:
        cursor = get_cursor(f)
        level = -1
        tags = []
        for event, element in cursor:
            if event == 'start':
                level += 1
                if levels:
                    tags.append((element.tag, level))
                else:
                    tags.append(element.tag)
            elif event == 'end':
                level -= 1
    return tags


FILENAME = 'toulouse_small.osm'

Counter(get_tags(FILENAME))
Counter(get_tags(FILENAME, levels=True))
