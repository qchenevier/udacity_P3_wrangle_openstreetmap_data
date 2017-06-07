import re
import pymongo
import requests
import logging

from collections import Counter
from pprint import pprint, pformat
from datetime import datetime

from utils import *


def get_postcodes(collection):
    pipeline = [
        {'$unwind': '$addr:postcode'},
        {'$match': {'addr:postcode': {
            '$exists': 1,
        }}},
        {'$project': {'addr:postcode': 1}},
    ]
    return set(rec['addr:postcode'] for rec in collection.aggregate(pipeline))


def get_bad_postcodes(addr_postcode, filter=31):
    bad_postcode = [postcode for postcode in addr_postcode if int(str(postcode)[0:2]) != 31]
    if not bad_postcode:
        logging.info('no bad postcode found')
    else:
        logging.warning('found {} bad postcode'.format(len(bad_postcode)))
        logging.debug('bad postcodes: {}'.format(bad_postcode))
    return bad_postcode


def print_websites_statistics(collection):
    pipeline = [
        {'$match': {'website': {'$exists': 1}}},
    ]
    results = list(collection.aggregate(pipeline))
    logging.info('{} websites'.format(len(results)))


def get_websites_records(collection):
    pipeline = [
        {'$match': {'website': {'$exists': 1}}},
        {'$project': {'website': 1}},
    ]
    records = list(collection.aggregate(pipeline))
    return records


def check_urls(website_records):
    logging.info('Accuracy: Checking if {} websites are valid'.format(len(website_records)))
    count = 0
    bad_website_records = []
    for record in website_records:
        website = record['website']
        try:
            request = requests.head(website, timeout=5)
            code = request.status_code
            if code not in [200, 301, 302]:
                logging.debug('{:03d} | bad code: {}: {}'.format(count, code, website))
                bad_website_records.append(record)
            else:
                pass
        except Exception as e:
            logging.debug('{:03d} | request failed: {}: {}'.format(count, website, e))
            bad_website_records.append(record)
        count += 1
    if bad_website_records:
        logging.warning('found {} bad websites'.format(len(bad_website_records)))
    else:
        logging.info('no bad websites')
    return bad_website_records


# suppress logging from requests library
logging.getLogger("requests").setLevel(logging.WARNING)

# connection to database
client = pymongo.MongoClient()
db = client['osm']


# postcode audit and correction
addr_postcode = get_postcodes(db.node)
logging.debug('all postcodes found:{}'.format(addr_postcode))
bad_postcode = get_bad_postcodes(addr_postcode, filter=31)

logging.info('deletion of all bad postcodes in database')
db.node.update(
    {'addr:postcode': {'$in': bad_postcode}},
    {'$unset': {'addr:postcode': ''}},
    multi=True,
)

addr_postcode = get_postcodes(db.node)
bad_postcode = get_bad_postcodes(addr_postcode, filter=31)


# opening hours
def get_opening_hours(collection):
    pipeline = [
        {'$unwind': '$opening_hours'},
        {'$match': {'opening_hours': {
            '$exists': 1,
        }}},
        {'$project': {'opening_hours': 1}},
    ]
    return list(rec['opening_hours'] for rec in collection.aggregate(pipeline))


def get_bad_opening_hours(opening_hours):
    opening_hours_words = [
        'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su',
        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
        '\ ', '24/7', ':', '\d{1,2}', ';', '-', ',', 'off', 'PH', '\+',
    ]
    pattern = '^({})*$'.format('|'.join(opening_hours_words))
    bad_opening_hours = [s for s in opening_hours if not re.search(pattern, s)]
    if bad_opening_hours:
        logging.warning('found {} bad opening hours'.format(len(bad_opening_hours)))
        logging.debug('bad opening hours: {}'.format(pformat(bad_opening_hours)))
    else:
        logging.info('no bad opening hours found')
    return bad_opening_hours


opening_hours = get_opening_hours(db.node)
bad_opening_hours = get_bad_opening_hours(opening_hours)

logging.info('deletion of all bad opening_hours in database')
db.node.update(
    {'opening_hours': {'$in': bad_opening_hours}},
    {'$unset': {'opening_hours': ''}},
    multi=True,
)

opening_hours = get_opening_hours(db.node)
bad_opening_hours = get_bad_opening_hours(opening_hours)

# restaurants
print_websites_statistics(db.node)

# check urls
records = get_websites_records(db.node)
bad_records = check_urls(records)

logging.info('Correction of bad urls in database')
# get records and ids
pipeline = [
    {'$match': {'website': {'$exists': 1}}},
    {'$match': {'website': {'$not': re.compile('^http[s]{0,1}://')}}},
    {'$project': {'website': 1}},
]
bad_url_records = list(db.node.aggregate(pipeline))

# update records in db
for record in bad_url_records:
    db.node.update_one(
        {'_id': record['_id']},
        {'$set': {'website': 'http://' + record['website']}},
    )

# get updated records from ids
bad_url_ids = [record['_id'] for record in bad_url_records]
pipeline = [
    {'$match': {'_id': {'$in': bad_url_ids}}},
    {'$project': {'website': 1}},
]
bad_url_records_after = list(db.node.aggregate(pipeline))
logging.info('{} URLs corrected'.format(len(bad_url_records)))
for before, after in zip(bad_url_records, bad_url_records_after):
    logging.debug('{} --> {}'.format(before['website'], after['website']))

# re-check urls
records = get_websites_records(db.node)
bad_records = check_urls(records)

logging.info('Deletion of remaining bad urls in database')
bad_ids = [record['_id'] for record in bad_records]
db.node.update(
    {'_id': {'$in': bad_ids}},
    {'$unset': {'website': ''}},
    multi=True,
)

# re-check urls
records = get_websites_records(db.node)
bad_records = check_urls(records)
