import pymongo

from collections import Counter
from pprint import pprint, pformat
from datetime import datetime

from utils import *


def get_field_types(field_name, collection):
    return list(collection.aggregate([
        {'$project': {'field_type': {'$type': '${}'.format(field_name)}}},
        {'$group': {
            '_id': '$field_type',
            'count': {'$sum': 1}
        }},
    ]))


def get_most_used_fields(collection):
    return Counter(
        tuple(record.keys()) for record in collection.find({})
    ).most_common()[0][0]


def print_field_types(field_name, field_types):
    logging.debug(
        '{field} | {types}'.format(
            field=field_name,
            types=', '.join(['{}: {}'.format(f['_id'], f['count']) for f in field_types])
        )
    )


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

logging.info('Validity: Verify that dates are all in a possible range (2004-2018)')
pipeline = [
    {'$match': {'timestamp': {
        '$lt': datetime(2004, 1, 1),
        '$gt': datetime(2018, 1, 1),
    }}},
    {'$project': {'timestamp': 1}},
]
impossible_dates = []
for collection_name in collection_names:
    impossible_dates += [record for record in db[collection_name].aggregate(pipeline)]
logging.info('{} impossible dates: {}'.format(len(impossible_dates), impossible_dates))

logging.info("Validity: Verify node_ref ids (in 'way' collection) are all in 'node' collection")
pipeline = [
    {'$unwind': '$node_ref'},
    {'$group': {
        '_id': '$node_ref',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
]
node_list = [record['_id'] for record in db.way.aggregate(pipeline)]

pipeline = [
    {'$group': {
        '_id': '$id',
    }},
]
reference_node_list = [record['_id'] for record in db.node.aggregate(pipeline)]

orphan_nodes = list(set(node_list) - set(reference_node_list))
logging.info('{} orphan nodes: {}'.format(len(orphan_nodes), orphan_nodes))

logging.debug('Accuracy: verify that data is the same as a reference dataset (on a subset)')
logging.debug('No check performed here')

logging.debug(
    'Completeness: count number of missing data compared to the reference dataset (on a subset)')
logging.debug('No check performed here')


logging.debug('Consistency: check which data are conflicting with one another')
logging.debug('No check performed here')

logging.debug('Consistency: decide which dataset is more reliable')
logging.debug('No check performed here')

logging.info('Uniformity: verify types of records (e.g.: string instead of date) or units used')
logging.debug('Most used fields per collection:')
for collection_name in collection_names:
    collection = db[collection_name]
    fields = get_most_used_fields(collection)
    logging.debug('{} || {}'.format(collection_name, ' | '.join(fields)))
    for field_name in fields:
        field_types = get_field_types(field_name, collection)
        if len(field_types) > 1:
            print_field_types(field_name, field_types)

logging.info(
    "Uniformity: Audit field 'id' in 'node' collection: some are 'int' and others are 'long'")

pipeline = [
    {'$addFields': {'id_type': {'$type': '$id'}}},
    {'$match': {'id_type': 'int'}},
    {'$project': {'id': 1}},
    {'$sort': {'id': -1}},
    {'$limit': 1},
]
max_int_id = list(db.node.aggregate(pipeline))[0]['id']

pipeline = [
    {'$addFields': {'id_type': {'$type': '$id'}}},
    {'$match': {'id_type': 'long'}},
    {'$project': {'id': 1}},
    {'$sort': {'id': 1}},
    {'$limit': 1},
]
min_long_id = list(db.node.aggregate(pipeline))[0]['id']

max_int32_theoretical_value = 2147483647

logging.info('max int id              : {}'.format(max_int_id))
logging.info('max int 32-bits (theory): {}'.format(max_int32_theoretical_value))
logging.info('min long id             : {}'.format(min_long_id))

logging.info('''
The analysis shows that mongoDB adapts the data type when inserting integers. the 'int' type is used
for integers smaller than the 32-bits integer max size and the 'long' type is used for integers
above this max size. When we read the mongoDB documentation, we understand that it's normal:
- 'int' stands for 32-bit integer
- 'long' stands for 64-bit integer
(relevant documentation: https://docs.mongodb.com/manual/reference/operator/query/type/)
''')

logging.info('Nothing to be done here.')

logging.info(
    "Uniformity: Audit field 'ref:FR:FANTOIR': some of them are 'int', others are 'string', etc.")

logging.debug("Examples of 'int'")
pipeline = [
    {'$addFields': {'field_type': {'$type': '$ref:FR:FANTOIR'}}},
    {'$match': {'field_type': 'int'}},
    {'$project': {'ref:FR:FANTOIR': 1}},
    {'$limit': 5},
]
logging.debug(pformat(list(db.relation.aggregate(pipeline))))

logging.debug("Examples of 'string'")
pipeline = [
    {'$addFields': {'field_type': {'$type': '$ref:FR:FANTOIR'}}},
    {'$match': {'field_type': 'string'}},
    {'$project': {'ref:FR:FANTOIR': 1}},
    {'$limit': 5},
]
logging.debug(pformat(list(db.relation.aggregate(pipeline))))

logging.debug('Record for ref:FR:FANTOIR = 116:')
pipeline = [
    {'$match': {'ref:FR:FANTOIR': 116}},
]
logging.debug(pformat(list(db.relation.aggregate(pipeline))))

logging.info('''
We understand that the data seems to have been correctly parsed by looking at the orginal data
(the ref:FR:FANTOIR is correct). Also the data seems to be compliant with the data specification
(which says that it is possible to use a short code of four alphanumeric caracters, which may begin
with zeroes, instead of a long code ending with a letter). However we understand that the conversion
in integer of the code has stripped the zeroes, which renders the audit less easy. It is better to
change the parser to avoid conversion in int for this specific field.

Relevant data specification (which is in french, sorry...): http://wiki.openstreetmap.org/wiki/FR:Key:ref:FR:FANTOIR
Original data of this record available here: https://www.openstreetmap.org/api/0.6/relation/1732473
''')

logging.info('Nothing to do here (except a small improvement in the parser)')
