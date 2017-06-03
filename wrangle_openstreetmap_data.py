import xml.etree.cElementTree as ET

from builtins import *  # python 2 compatibility
from pprint import pprint
from collections import Counter


def get_cursor(file_handler):
    return ET.iterparse(file_handler, events=('start', 'end'))


def get_tags(filename, **kwargs):
    def _update_level(event, level):
        level += 1 if event == 'start' else -1
        return level

    def _update_tag_stack(tag_stack, element, event):
        if event == 'start':
            tag_stack.append(element.tag)
        else:
            tag_stack.pop()
        return tag_stack

    def _append_tag(tags, element, event, level, tag_stack, with_level=False, with_parent=False,
                    with_xpath=False):
        if event == 'start':
            tag_and_properties = [element.tag]
            if with_level:
                tag_and_properties.append(level)
            if with_parent:
                parent = tag_stack[-1] if len(tag_stack) > 0 else None
                tag_and_properties.append(parent)
            if with_xpath:
                xpath = '/'.join(tag_stack + [element.tag])
                tag_and_properties.append(xpath)
            tags.append(tuple(tag_and_properties))
        return tags

    with open(filename) as file_h:
        cursor = get_cursor(file_h)
        level = -1
        tags = []
        tag_stack = []
        for event, element in cursor:
            level = _update_level(event, level)
            tags = _append_tag(tags, element, event, level, tag_stack, **kwargs)
            tag_stack = _update_tag_stack(tag_stack, element, event)

    return tags


FILENAME = 'toulouse_extra_small.osm'

Counter(get_tags(FILENAME))
Counter(get_tags(FILENAME, with_level=True))
Counter(get_tags(FILENAME, with_parent=True))
Counter(get_tags(FILENAME, with_xpath=True))
Counter(get_tags(FILENAME, with_level=True, with_parent=True))
