import re
import pymongo
import requests
import logging

from collections import Counter
from pprint import pprint, pformat
from datetime import datetime

from utils import *


def print_restaurants_statistics(collection):
    pipeline = [
        {'$match': {'amenity': 'restaurant'}},
    ]
    results = list(collection.aggregate(pipeline))
    logging.info('{} restaurants in database'.format(len(results)))
    pipeline = [
        {'$match': {'amenity': 'restaurant'}},
        {'$match': {'website': {'$exists': 1}}},
    ]
    results = list(collection.aggregate(pipeline))
    logging.info('{} restaurants have a website'.format(len(results)))


def get_restaurant_records(collection):
    pipeline = [
        {'$match': {'amenity': 'restaurant'}},
        {'$match': {'website': {'$exists': 1}}},
        {'$project': {'website': 1}},
    ]
    records = list(collection.aggregate(pipeline))
    return records


def check_urls(records):
    logging.info('Accuracy: Checking if {} websites are valid'.format(len(records)))
    count = 0
    bad_records = []
    for record in records:
        website = record['website']
        try:
            request = requests.head(website, timeout=10)
            code = request.status_code
            if code not in [200, 301, 302]:
                logging.debug('{:03d} | bad code: {}: {}'.format(count, code, website))
                bad_records.append(record)
            else:
                pass
        except Exception as e:
            logging.debug('{:03d} | request failed: {}: {}'.format(count, website, e))
            bad_records.append(record)
        count += 1
    logging.info('{} bad websites'.format(len(bad_records)))
    return bad_records


# suppress logging from requests library
logging.getLogger("requests").setLevel(logging.WARNING)

# connection to database
client = pymongo.MongoClient()
db = client['osm']

print_restaurants_statistics(db.node)

# check urls
records = get_restaurant_records(db.node)
bad_records = check_urls(records)

logging.info('Correction of bad urls in database')
# get records and ids
pipeline = [
    {'$match': {'amenity': 'restaurant'}},
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
    {'$match': {'amenity': 'restaurant'}},
    {'$match': {'_id': {'$in': bad_url_ids}}},
    {'$project': {'website': 1}},
]
bad_url_records_after = list(db.node.aggregate(pipeline))
for before, after in zip(bad_url_records, bad_url_records_after):
    logging.debug('{} --> {}'.format(before['website'], after['website']))

# re-check urls
records = get_restaurant_records(db.node)
bad_records = check_urls(records)

logging.info('Deletion of remaining bad urls in database')
bad_ids = [record['_id'] for record in bad_records]
db.node.update(
    {'_id': {'$in': bad_ids}},
    {'$unset': {'website': ''}},
    multi=True,
)

# re-check urls
records = get_restaurant_records(db.node)
bad_records = check_urls(records)
