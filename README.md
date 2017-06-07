# OpenStreetMap Data Case Study

## Map Area

Toulouse, France

- Here is a [Toulouse overview](https://www.openstreetmap.org/relation/35738)
- The part I extracted is around [this point in Toulouse](https://www.openstreetmap.org/export#map=15/43.6019/1.4340)
- Click on [this link](http://overpass-api.de/api/map?bbox=1.4015,43.5874,1.4661,43.6163) to download the same XML file.

This city is where I live. To discover a new database, I think it's easier to start with something I know in real life.


To parse the XML file and insert it in the mongoDB database, use the script `python 1_parse_openstreetmap_xml.py`


## Problems Encountered in the Map

I parsed the XML file `toulouse_medium.osm` with the script `python 1_parse_openstreetmap_xml.py`. After several queries, I noticed several small problems in the dataset:
- impossible postcodes: _68199_ whereas all postcodes in the region follow the pattern _31xxx_
- opening hours specified in french: _du lundi au vendredi le midi_
- website fields badly formed and referring to outdated sites

We perform several operations in each case. To do it, run the script `python 3_audit_and_correct_data.py`

### Impossible postcodes: _68199_ whereas all postcodes in the region follow the pattern _31xxx_
To check all the postcodes after parsing, I used the following query:

``` python
pipeline = [
    {'$unwind': '$addr:postcode'},
    {'$match': {'addr:postcode': {
        '$exists': 1,
    }}},
    {'$project': {'addr:postcode': 1}},
]
addr_postcode = set(rec['addr:postcode'] for rec in db.node.aggregate(pipeline))
print(addr_postcode)
```

Which gave me this result:
`{31200, 31300, 31076, 68199, 31400, 31015, 31500, 31000, 31100}`

The postcode **68199** is not compatible with the region. Our region has all postcodes beginning with **31**. In bash, I used a grep command to check that such record was existing in the XML file:

``` bash
grep -A 1 -B 1 -E '"68199"' toulouse_medium.osm
```

Which gave me:
``` XML
<tag k="addr:housenumber" v="14"/>
<tag k="addr:postcode" v="68199"/>
<tag k="addr:street" v="Boulevard de Bonrepos"/>
```

I deduce that the parser behaved correctly, the error is in the XML data. It is maybe a typing error by the user. However, it's difficult to deduce the correct data from this corrupt record. So I decide to drop it.

``` python
bad_postcode = [postcode for postcode in addr_postcode if int(str(postcode)[0:2]) != 31]
db.node.update(
    {'addr:postcode': {'$in': bad_postcode}},
    {'$unset': {'addr:postcode': ''}},
    multi=True,
)
```

### Opening hours specified in french: _du lundi au vendredi le midi_
Here is the query I used to check the opening hours:
``` python
pipeline = [
    {'$unwind': '$opening_hours'},
    {'$match': {'opening_hours': {
        '$exists': 1,
    }}},
    {'$project': {'opening_hours': 1}},
]
opening_hours = list(rec['opening_hours'] for rec in db.node.aggregate(pipeline))
```

By looking at the content of `opening_hours`, I quickly found that some fields had been filled with the french convention to note hours: **12h30** instead of **12:30** or in plain french text **du lundi au vendredi midi**.

After several tests and by [reading the OpenStreetMap specification](http://wiki.openstreetmap.org/wiki/Key:opening_hours) for this key, I have designed a small test to detect automatically most of the badly formatted opening hours:  

``` python
opening_hours_accepted_words = [
    'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su',
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    '\ ', '24/7', ':', '\d{1,2}', ';', '-', ',', 'off', 'PH', '\+',
]
pattern = '^({})*$'.format('|'.join(opening_hours_accepted_words))
bad_opening_hours = [s for s in opening_hours if not re.search(pattern, s)]
pprint(bad_opening_hours)
```

Which shows me the following invalid opening hours:
``` python
['Tu-Sat 09:00-12:30,14:00-19:00',
 'du lundi au vendredi le midi',
 'mo-sa 07:00-02:00',
 ' Sa midday off',
 "de 17h30 à 2h / jusqu'à 3h le samedi",
        ...
 ' Dec 25\xa0off',
 '10h-13h30, 15h30-19h00. Fermé dimanche et lundi',
 '19h30 à 22h00 en semaine, 19h30 23h00 en week-end',
 '7h30-13h  16h-20h']
 ```

After a quick thinking, I think it is too complicated to correct it programmatically: too much special cases. Either we drop it or we correct it by hand. The exercise is not about correcting data by hand, so I choose to drop it.

``` python
db.node.update(
    {'opening_hours': {'$in': bad_opening_hours}},
    {'$unset': {'opening_hours': ''}},
    multi=True,
)
```

### Website fields wrongly formatted and refering to outdated sites
This field has been (deliberately) chosen because it is hard to maintain: physical change of restaurants may be reflected quite quickly in the database by the community, but change in their website might not be easy to detect.

I use the following query to get all the restaurants websites info (in this case I get the (`_id`, `website`) fields for each record):

``` python
pipeline = [
    {'$match': {'website': {'$exists': 1}}},
    {'$project': {'website': 1}},
]
website_records = list(collection.aggregate(pipeline))
```
I get 741 websites.

#### Check the sites
To check the accuracy of the websites URL's, I simply do an HTTP request and decide if the URL is still accurate depending on the status code I get:

``` python
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
    logging.info('{} bad websites'.format(len(bad_website_records)))
    return bad_website_records
```

When I run this code `bad_records = check_urls(records)` and analyze its output, I understand that:
- some website URLs are badly formatted (e.g without `http://`)
- some website URLs are well formatted but the site is down

There are up to 112 websites which are incorrect, as per the check I performed.

> Warning: this figure may vary, if you rerun the test. To do a more robust test, it would be better to confirm that a site is unavailable for several days straight.

#### Correct malformed URLs
I try to correct the malformed URLs by adding a proper `http://` at the beginning:
``` python
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
```
36 URLs have been corrected in the collection.

#### Re-check URLs and delete websites which are still bad after correction
After correcting this, I re-run: `bad_records = check_urls(records)` and I still get 82 bad websites. I decide to drop the records and re-run the check.

``` python
bad_ids = [record['_id'] for record in bad_records]
db.node.update(
    {'_id': {'$in': bad_ids}},
    {'$unset': {'website': ''}},
    multi=True,
)
```

### Statistics:

Those statistics are given by running the script `python 2_statistics.py`

#### Unique users & number of records
I used the following queries to get the unique users per collection and for the whole database:
``` python
all_unique_users = set()
for collection_name in ['node', 'way', 'relation']:
    unique_users = list(db[collection_name].aggregate([
        {'$group': {
            '_id': '$user',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
    ]))
    print(collection_name, unique_users)
    all_unique_users = all_unique_users | set(user['_id'] for user in unique_users)
    print('all', unique_users)
```

And I used the following queries to get the number of records per collection and for the whole database:
``` python
n_records = 0
for collection_name in ['node', 'way', 'relation']:
    n_records += db[collection_name].count()
    print(collection_name, db[collection_name].count())
print('all', n_records)
```

The results are compiled in the following table:

||'node'|'way'|'relation'|all|
|--|--|--|--|--|
|unique users|472|324|121|583|
|number of records|243251|42001|1873|287125|

#### File sizes
- `toulouse_medium.osm`: 64MB (as per `ls -alh` in linux shell)
- mongoDB: 47 MB (as per `db.stats(1024*1024)` in mongo shell)

## Conclusion

The audit has shown that the database is quite robust on most fields (such as `date`, `id`, `user`). It seems that these fields are generated automatically by the OSM tools so it's not so surprising.

But, for fields which are filled by humans, the error rate goes up. It's worth taking the time to audit the data. However, for the cases we found it was not easy to solve programmatically the errors in the data, especially for 2 cases:
- either the input was too corrupted to deduce what was the correct data (e.g.: see the postcode section)
- or there is too much specific cases that it's quicker to correct the data by hand (e.g.: see the opening hours section). This case seems particularly true for the fields where it's tempting to put natural language (we don't have this problem with the postcode field).

However I'm happy for founding a way to correct automatically some data (e.g: the websites URLs).

Then, here are some proposal of improvements with their pros and cons.

### Improvement 1: better bad URLs detection
This solution of dropping URLs in database upon HTTP status code could be improved. Currently the data is dropped upon a single failed check, this leads to some false-positive detection of bad websites and wrongly deletions of the fields. I suggest instead to:
- add a field `website_failed_check_dates` recording the dates at which a test has been failed
- run the check each day and fill the `website_failed_check_dates` array
- every 2 or 3 months, run a job to drop the bad `website` URLs, based on a threshold on the number of failed checks during a given time period (i.e. using the `website_failed_checks` array).

Pros:
- less false-positive detection and wrong deletion.

Cons:
- confirmation time period delays the deletion of the bad records in the database, slightly detrimental to its accuracy. These records will appear as false-negatives (website is really down, but the URL is still in the database).
- additional work to chose the threshold and the time period, which maybe need to be adapted to local OSM communities, depending on their habits.


### Improvement 2: better HMI to input data
To diminish the number of human errors, I think that the tools of OpenStreetMap would really help users by displaying some examples about how to fill in the fields they are about to fill (e.g.: next to the form field). It would help people reminding themselves that the database is international and ruled by convention decided by the community.

Pros:
- less bad input due to human error 

Cons:
- HMI potentially hard to design: it might render the tools less user-friendly
- additional work to maintain a set of examples for each human-made field
- synchronize of the HMI with the examples database might render the OSM tools harder to maintain
