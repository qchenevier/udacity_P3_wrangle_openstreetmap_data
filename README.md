# Auditing data from openstreetmap

## Prerequisites
You'll need:
- python 3
- mongoDB

The following python 3 libraries:
- `pymongo`
- `colorlog` (optional)

## Usage
3 steps:

1. Parse XML file downloaded from [openstreetmap site](https://www.openstreetmap.org/export)
1. Audit validity & uniformity
1. Audit accuracy

All scripts output explanations & useful information in the console about the operations they perform, please read carefully.

> Use of the `colorlog` module is recommended for easier reading.

### Parse XML
Execute the script in console:

`python 1_parse_openstreetmap_xml.py`

This script will:
- parse the xml file and retrieve records of 3 types: `node`, `way` and `relation`
- delete the former database in mongoDB
- insert a database named `osm` in mongoDB with 3 collections: `node`, `way` and `relation`

> A running instance of mongodb is needed (on linux, run `sudo service mongod start`)

### Audit validity & uniformity
We decided to audit some of the most used fields in the database.

Execute the script in console:

`python 2_audit_mongodb.py`

This script will audit validity and uniformity for various fields:
- validity of `date` in all collections
- validity of `node_ref` in `way` collection
- uniformity of `id` in `node` collection
- uniformity of `ref:FR:FANTOIR` in `relation` collection

Nothing is changed in the database by this script. For the most used fields, the uniformity & validity of the data we parsed from the _openstreetmap_ database seems quite good.

### Audit accuracy
We have (deliberately) chosen to audit a field which is hard to maintain: the `website` for each restaurant. Change in restaurants may be reflected quite quickly in the database, but change in their website might not be easy to detect. Additionally, since this field is not widely used, errors might go unnoticed.

Execute the script in console:

`python 3_audit_restaurants_websites.py`

This script will:
- audit accuracy for the `website` field for each restaurant (i.e. each `node` record with `amenity` = `restaurant`) by interrogating each website and check the HTTP status code.
- correct `website` which may be malformed (e.g without `http://`) in the database
- re-audit accuracy
- delete `website` which are still incorrect after correction

As expected, lots of data needed to be corrected: roughly 20 %.
