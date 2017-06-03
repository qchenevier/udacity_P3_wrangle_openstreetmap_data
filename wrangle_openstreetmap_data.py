import re
import arrow
import xml.etree.cElementTree as ET

from builtins import *  # python 2 compatibility
from pprint import pprint
from collections import Counter
from datetime import datetime


def _get_cursor(file_handler, events=('start', 'end')):
    return ET.iterparse(file_handler, events=events)


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
        cursor = _get_cursor(file_h)
        level = -1
        tags = []
        tag_stack = []
        for event, element in cursor:
            level = _update_level(event, level)
            tags = _append_tag(tags, element, event, level, tag_stack, **kwargs)
            tag_stack = _update_tag_stack(tag_stack, element, event)

    return tags


def _convert_type(data):
    try:
        return int(data)
    except Exception as e:
        try:
            return float(data)
        except Exception as e:
            try:
                format_string = '%Y-%m-%dT%H:%M:%S.%f%z'
                datetime.strptime(my_timestamp, format_string)
            except Exception as e:
                if re.findall('[Tt]rue', data):
                    return True
                elif re.findall('[Ff]alse', data):
                    return False
                elif data == '':
                    return None
                else:
                    return data


def _convert_values_type(data_dict):
    return {key: _convert_type(value) for key, value in data_dict.items()}


def parse_data(filename, filter_list=['node', 'way', 'relation']):
    def _append_data(data, element):
        record = _convert_values_type(element.attrib)

        if element.tag == 'nd':
            record = record['ref']
            element.tag = 'node_ref'

        if element.tag == 'tag':
            element.tag = record['k']
            record = record['v']

        for child in element.getchildren():
            record = _append_data(record, child)

        if element.tag in data.keys():
            if not isinstance(data[element.tag], list):
                data[element.tag] = [data[element.tag]]
            data[element.tag].append(record)
        else:
            data[element.tag] = record
            # data[element.tag] = [record]

        return data

    with open(filename) as file_h:
        cursor = _get_cursor(file_h, events=('start',))
        data = {}
        for event, element in cursor:
            if element.tag in filter_list:
                data = _append_data(data, element)

    return data


FILENAME = 'toulouse_extra_small.osm'

Counter(get_tags(FILENAME))
Counter(get_tags(FILENAME, with_level=True))
Counter(get_tags(FILENAME, with_parent=True))
Counter(get_tags(FILENAME, with_xpath=True))
Counter(get_tags(FILENAME, with_level=True, with_parent=True))

filter_list = ['node', 'way', 'relation']
osm = parse_data(FILENAME, filter_list=filter_list)

from pprint import pprint
import pymongo

client = pymongo.MongoClient()
client.database_names()

db = client['osm']
for category in filter_list:
    db[category].insert(osm[category])

pprint(list(db.node.aggregate([
    {'$group': {
        '_id': '$user',
        'count': {'$sum': 1}
    }},
])))
