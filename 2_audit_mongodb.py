import pymongo

from collections import Counter
from pprint import pprint


def get_field_types(field_name, collection):
    return list(collection.aggregate([
        {'$project': {'fieldType': {'$type': '${}'.format(field_name)}}},
        {'$group': {
            '_id': '$fieldType',
            'count': {'$sum': 1}
        }},
    ]))


def get_most_used_fields(collection):
    return Counter(
        tuple(record.keys()) for record in collection.find({})
    ).most_common()[0][0]


def print_field_types(collection_name, field_name, field_types):
    print('collec: {}'.format(collection_name))
    print('field : {}'.format(field_name))
    print(
        'types : {}'.format(
            ' | '.join(['{}: {}'.format(f['_id'], f['count']) for f in field_types])
        )
    )


'''
Measures of data quality:
- Validity: conforms to a schema
- Accuracy: conforms to gold standard
- Completeness: all records ?
- Consistency: matches other data
- Uniformity: Same units
'''

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
    for field_name in get_most_used_fields(collection):
        field_types = get_field_types(field_name, collection)
        if len(field_types) > 1:
            print_field_types(collection_name, field_name, field_types)
