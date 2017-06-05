import re
import xml.etree.cElementTree as ET
import pymongo
import logging

from collections import Counter
from datetime import datetime

from utils import *


def _get_cursor(file_handler, events=('start', 'end')):
    return ET.iterparse(file_handler, events=events)


def _convert_type(data):
    try:
        return int(data)
    except Exception as e:
        try:
            return float(data)
        except Exception as e:
            try:
                format_string = '%Y-%m-%dT%H:%M:%SZ'
                return datetime.strptime(data, format_string)
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


def _manage_tag_and_record_exceptions(tag, record):
    if tag == 'nd':
        tag = 'node_ref'
        record = record['ref']
    if tag == 'tag':
        tag = record['k']
        record = record['v']
    return tag, record


def _get_tag_and_record(element):
    tag = element.tag
    record = _convert_values_type(element.attrib)
    tag, record = _manage_tag_and_record_exceptions(tag, record)
    return tag, record


def _insert_record_in_data_dict(data, key, value):
    if key in data.keys():
        if not isinstance(data[key], list):
            data[key] = [data[key]]
        data[key].append(value)
    else:
        data[key] = value
    return data


def _add_record(data, element, recursive=True):
    tag, record = _get_tag_and_record(element)
    if recursive:
        for child in element.getchildren():
            record = _add_record(record, child)
    data = _insert_record_in_data_dict(data, tag, record)
    return data


def parse_data(filename, filter_list=['node', 'way', 'relation'], recursive=True):
    def _report_parsing_progress(cursor_tag, num_tags):
        logging.info(
            'Parsed {} / {} tags. ({:.1f} %)'
            .format(cursor_tag, num_tags, cursor_tag / num_tags * 100)
        )

    # this first part in only to count the number of tags to parse.
    # the performance penalty is important but this information is useful to show progress
    # when parsing very large files (more than 200 MB)
    with open(filename) as file_h:
        cursor = _get_cursor(file_h, events=('start',))
        logging.info('Counting tags to parse.')
        cursor_tag = 0
        for event, element in cursor:
            cursor_tag += 1
            if cursor_tag % 500000 == 0:
                logging.debug('{} tags read.'.format(cursor_tag))
            element.clear()
        num_tags = cursor_tag
        logging.info('{} tags to parse.'.format(num_tags))

    # here is the parsing part
    with open(filename) as file_h:
        cursor_tag = 0
        cursor = _get_cursor(file_h, events=('start',))
        data = {}
        for event, element in cursor:
            cursor_tag += 1
            if element.tag in filter_list:
                data = _add_record(data, element, recursive=recursive)
            if cursor_tag % 100000 == 0:
                _report_parsing_progress(cursor_tag, num_tags)
            element.clear()
    _report_parsing_progress(cursor_tag, num_tags)
    return data


logging.basicConfig(level=logging.DEBUG)
# FILENAME = 'toulouse_extra_small.osm'
FILENAME = 'toulouse_medium.osm'
# FILENAME = 'toulouse_large.osm'

collection_names = ['node', 'way', 'relation']
osm = parse_data(FILENAME, filter_list=collection_names)

client = pymongo.MongoClient()

logging.info('Dropping former database')
client.drop_database('osm')
db = client['osm']
for category in collection_names:
    logging.info("Inserting collection '{}' in mongoDB".format(category))
    db[category].insert(osm[category])
