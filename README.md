# Auditing data from openstreetmap

## Prerequisites
Please install:
- python 3 with the following modules:
  - pymongo
  - colorlog (optional)
- mongoDB

## Usage
The audit is done in 3 steps, with a python script for each step:

1. Parse XML file downloaded from [openstreetmap site](https://www.openstreetmap.org/export)
1. Audit validity & uniformity
1. Audit accuracy

All scripts output explanations & useful information in the console about the operations they perform.

> Installation of the `colorlog` module is recommended for easier reading of the console output.

### Parse XML
The XML file which is parsed is `toulouse_medium.osm` (~ 60 MB). It is centered around [this point in Toulouse, France](https://www.openstreetmap.org/export#map=15/43.6019/1.4340). Click on [this link](http://overpass-api.de/api/map?bbox=1.4015,43.5874,1.4661,43.6163) to download the same XML file.


Execute the script in console:

`python 1_parse_openstreetmap_xml.py`

This script will:
- parse the xml file and retrieve records of 3 types: `node`, `way` and `relation`
- delete the former database in mongoDB
- insert a database named `osm` in mongoDB with 3 collections: `node`, `way` and `relation`

The file is 993077 lines long for 918435 tags.

> A running instance of mongoDB is needed (on linux, run `sudo service mongod start`)

### Audit validity & uniformity
We decided to audit some of the most used fields in the database.

Execute the script in console:

`python 2_audit_mongodb.py`

This script will audit validity and uniformity for various fields:
- compute some statistics about each collection
- audit validity of `date` in all collections
- audit validity of `node_ref` in `way` collection
- audit uniformity of `id` in `node` collection
- audit uniformity of `ref:FR:FANTOIR` in `relation` collection

> The database is not modified by this script. For the fields we audited, the uniformity & validity of the data we parsed from the _openstreetmap_ database seems quite good.

> However all the uniformity and validity checks have proven to be **very useful while debugging** the parser: thanks to that, I have been able to find very quickly what went wrong during the first phase.

#### Statistics:
||'node'|'way'|'relation'|all|
|--|--|--|--|--|
|unique users|472|324|121|583|
|number of records|243233|42001|1873|287107|

> mongoDB queries for theses statistics are available in the `2_audit_mongodb.py` script file.

#### Validity of `date` in all collections

We look for "impossible dates": i.e. we verify that `date` records are all in the range: from 2004-01-01 to 2018-01-01.

The audit didn't find any "impossible dates".

#### Validity of `node_ref` in `way` collection

We look for "orphan nodes": i.e. we verify that all `node_ref` ids in `way` collection are all in the `node` collection.

The audit didn't find any "orphan nodes".

#### Uniformity of `id` in `node` collection

We analyze why some `id` are _int_ type and others are _long_ type.

The analysis shows that mongoDB adapts the data type when inserting integers. the _int_ type is used for integers smaller than the 32-bits integer max size and the _long_ type is used for integers above this max size. When we read the mongoDB documentation, we understand that it's normal:
- _int_ stands for 32-bit integer
- _long_ stands for 64-bit integer

Relevant documentation:
- [mongoDB types]( https://docs.mongodb.com/manual/reference/operator/query/type/)

#### Uniformity of `ref:FR:FANTOIR` in `relation` collection

We analyze why some `ref:FR:FANTOIR` are _int_ type and others are _string_ type.

We understand that the data seems to have been correctly parsed by looking at the original data (the ref:FR:FANTOIR is correct). Also the data seems to be compliant with the data specification (which says that it is possible to use a short code of four alphanumeric characters, which may begin with zeros, instead of a long code ending with a letter).
However we understand that the conversion in integer of the code has stripped the zeros, which renders the audit less easy. It would be better to improve the parser to avoid conversion in _int_ for this specific field.

Relevant documentation:
- [OpenStreetMap data specification about `ref:FR:FANTOIR`]( http://wiki.openstreetmap.org/wiki/FR:Key:ref:FR:FANTOIR). It's in french, sorry :-(
- [Original data of a _bizarre_, yet normal record]( https://www.openstreetmap.org/api/0.6/relation/1732473)


### Audit accuracy
We have (deliberately) chosen to audit a field which is hard to maintain: the `website` for each restaurant. Physical change of restaurants may be reflected quite quickly in the database by the community, but change in their website might not be easy to detect. Additionally, since this field is not widely used, errors might go unnoticed.

Execute the script in console:

`python 3_audit_restaurants_websites.py`

This script will:
- audit accuracy for the `website` field for each restaurant (i.e. each `node` record with `amenity` = `restaurant`) by doing an HTTP request to each website and check the HTTP status code we get.
- correct `website` which may be malformed (e.g without `http://`) in the database
- re-audit accuracy
- delete `website` which are still incorrect after correction


There are 453 restaurants in the database, with 116 `website`:
- 26 seem to be inaccurate at first glance (22 %)
- 11 have been corrected (9 %)
- 18 were still inaccurate after this correction and have been deleted (16 %)

In the end, after trying to correct the fields, we deleted 16 % of the `website` fields due inaccuracy. After that, we had no more inaccuracies (as per our metrics).

> The number of detected inaccuracies might be different when you run the script. I had different results within a time frame of several hours. In a real life situation, to decide to data, we would need a more robust criteria, such as the unavailability of the site for several days.

## Synthesis

This exercise of parsing and cleaning data is quite tedious and it is not finished yet ! The audit has shown that the database is quite robust on its most used fields (such as `date`, `id`, `user`). It seems that these fields are generated automatically by the OSM tools so it's not so surprising. With more time, I think I would continue to audit the least used fields, such as `ref:FR:FANTOIR`, because they seem to be human-made. A good start would be the address fields: `addr:street`, `addr:city`, `addr:postcode`, `addr:country`, `addr:housenumber` and so on.

About data correction, I think that a good practice would be to keep the data and only label it as _inaccurate_. E.g. label site as _down_ and recheck automatically every several weeks if it's still true. Deleting permanently data on a single failed test seems pretty dangerous.
