import pymongo

from collections import Counter
from pprint import pprint, pformat
from datetime import datetime

from utils import *


client = pymongo.MongoClient()
db = client['osm']

collection_names = ['node', 'way', 'relation']

logging.info("Some statistics:")
all_unique_users = set()
for collection_name in collection_names:
    unique_users = list(db[collection_name].aggregate([
        {'$group': {
            '_id': '$user',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
    ]))
    logging.info(
        "'{}' collection: unique users: {} ".format(collection_name, len(unique_users)))
    all_unique_users = all_unique_users | set(user['_id'] for user in unique_users)
    logging.info(
        "'{}' collection: 10 most active users: {}".format(
            collection_name, ', '.join([user['_id'] for user in unique_users[:10]])
        )
    )

logging.info("all collections: {} unique users".format(len(all_unique_users)))

n_records = 0
for collection_name in collection_names:
    n_records += db[collection_name].count()
    logging.info(
        "'{}' collection: {} records".format(collection_name, db[collection_name].count()))
logging.info("all collections: {} records".format(n_records))
