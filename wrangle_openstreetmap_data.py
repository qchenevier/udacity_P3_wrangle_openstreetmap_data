import xml.etree.cElementTree as ET

from builtins import *  # python 2 compatibility
from pprint import pprint
from collections import Counter


def get_cursor(file_handler):
    return ET.iterparse(file_handler, events=('start', 'end'))


def get_tags(filename, with_levels=False):
    def _update_level(event, level):
        level += 1 if event == 'start' else -1
        return level

    def _append_tag(tags, element, event, level, with_levels=False):
        if event == 'start':
            tags.append((element.tag, level) if with_levels else element.tag)
        return tags

    with open(filename) as file_h:
        cursor = get_cursor(file_h)
        level = -1
        tags = []
        for event, element in cursor:
            level = _update_level(event, level)
            tags = _append_tag(
                tags, element, event, level, with_levels=with_levels)
    return tags


FILENAME = 'toulouse_small.osm'

Counter(get_tags(FILENAME))
Counter(get_tags(FILENAME, with_levels=True))
