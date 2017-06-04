import pymongo

from collections import Counter
from pprint import pprint
from datetime import datetime


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
    print(
        '{field} | {types}'.format(
            field=field_name,
            types=', '.join(['{}: {}'.format(f['_id'], f['count']) for f in field_types])
        )
    )


client = pymongo.MongoClient()
db = client['osm']

pprint(list(db.node.aggregate([
    {'$group': {
        '_id': '$user',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
    {'$limit': 50},
])))

pprint(list(db.node.aggregate([
    {'$group': {
        '_id': '$timestamp',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
    {'$limit': 50},
])))

collection_names = ['node', 'way', 'relation']
for collection_name in collection_names:
    collection = db[collection_name]
    fields = get_most_used_fields(collection)
    print()
    print('{} || {}'.format(collection_name, ' | '.join(fields)))
    for field_name in fields:
        field_types = get_field_types(field_name, collection)
        if len(field_types) > 1:
            print_field_types(field_name, field_types)

'''
Measures of data quality:
- Validity: conforms to a schema
- Accuracy: conforms to gold standard
- Completeness: all records ?
- Consistency: matches other data
- Uniformity: Same units
'''


'''
Auditing Validity:
- range, unicity (e.g.: date within range)
- foreign key constraints (e.g.: 'node' keys in 'way' table must be in 'node' table)
- cross-field constraints (e.g.: start date must be before end date)
- datatype (e.g.: date must be a date, user must be a string)
'''
# Verify that dates are all in a reasonable range

pipeline = [
    {'$match': {'timestamp': {
        '$lt': datetime(2004, 1, 1),
        '$gt': datetime(2018, 1, 1),
    }}},
    {'$project': {'timestamp': 1}},
]
impossible_dates = []
for collection_name in collection_names:
    pprint(list(db[collection_name].aggregate(pipeline + [{'$limit': 50}])))
    impossible_dates += [record for record in db[collection_name].aggregate(pipeline)]
print('{} impossible dates: {}'.format(len(impossible_dates), impossible_dates))

# Verify way.node_ref ids are all in node collection
pipeline = [
    {'$unwind': '$node_ref'},
    {'$group': {
        '_id': '$node_ref',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
]
pprint(list(db.way.aggregate(pipeline + [{'$limit': 50}])))
node_list = [record['_id'] for record in db.way.aggregate(pipeline)]

pipeline = [
    {'$group': {
        '_id': '$id',
    }},
]
pprint(list(db.node.aggregate(pipeline + [{'$limit': 50}])))
reference_node_list = [record['_id'] for record in db.node.aggregate(pipeline)]

orphan_nodes = list(set(node_list) - set(reference_node_list))
print('{} orphan nodes: {}'.format(len(orphan_nodes), orphan_nodes))


'''
Auditing Accuracy:
- verify that data is the same as a reference dataset (on a subset)
'''
# No check performed here

'''
Auditing Completeness:
- count number of missing data compared to the reference dataset (on a subset)
'''
# No check performed here


'''
Auditing Consistency:
- check which data are conflicting with one another
- decide which dataset is more reliable
'''
# No check performed here


'''
Auditing Uniformity:
- verify types of data for each field (e.g.: string instead of date, float instead of int)
'''

collection_name = 'node'
collection = db[collection_name]
fields = get_most_used_fields(collection)
print()
print('{} || {}'.format(collection_name, ' | '.join(fields)))
for field_name in fields:
    field_types = get_field_types(field_name, collection)
    if len(field_types) > 1:
        print_field_types(field_name, field_types)

# check node ids which are int and long
max_int32_theoretical_value = 2147483647

pipeline = [
    {'$addFields': {'id_type': {'$type': '$id'}}},
    {'$match': {'id_type': 'int'}},
    {'$project': {'id': 1}},
    {'$sort': {'id': -1}},
    {'$limit': 1},
]
pprint(list(db.node.aggregate(pipeline)))
max_int_id = list(db.node.aggregate(pipeline))[0]['id']

pipeline = [
    {'$addFields': {'id_type': {'$type': '$id'}}},
    {'$match': {'id_type': 'long'}},
    {'$project': {'id': 1}},
    {'$sort': {'id': 1}},
    {'$limit': 1},
]
pprint(list(db.node.aggregate(pipeline)))
min_long_id = list(db.node.aggregate(pipeline))[0]['id']

print(max_int_id, max_int32_theoretical_value, min_long_id)
