import math
import bisect
import os.path
import json
import requests
import xml.etree.cElementTree as bxml


# originalni adresa datasetu
dataset_whole_url = 'https://www.vodnimlyny.cz/en/?do=getEstates'

# nastavit True pro stahovani nove verze datasetu
dataset_disable_cache = False

result_filename = 'final.gpx'

# maximalni pocet polozek v GPX
result_limit_items = 99000

# minimalni vzdalenosti od ruznych bodu
minimal_distances = [
    ("Prague", 50.0755, 14.4378, 150),
    #("Neco", 50.0755, 14.4378, 50),
]


def get_dataset():
    dataset_name = 'dataset.json'
    dataset_str = None

    if not dataset_disable_cache and os.path.isfile(dataset_name):
        with open(dataset_name, 'rb') as f:
            bts = f.read()
            dataset_str = bts.decode('ascii')
        
    else:
        s = requests.Session()

        req = s.get(dataset_whole_url)

        if req.status_code != 200:
            raise 'Invalid response code `' + str(req.status_code) + '` from `' + dataset_whole_url + '`'
        else:
            dataset_str = req.content

            if not dataset_disable_cache:
                with open(dataset_name, 'wb') as f:
                    f.write(req.content)

    return json.loads(dataset_str)


def haversine(lat1, lon1, lat2, lon2):
    # Radius of the Earth in kilometers
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)

    # Differences in coordinates
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distance in kilometers
    distance = R * c

    return distance


def prepare_items():
    items = []

    for c in get_dataset():

        min_dist = -1
        is_valid = False
        lat = float(c["lat"])
        lon = float(c["lng"])

        for d in minimal_distances:
            dist = haversine(lat, lon, d[1], d[2])

            if dist <= d[3]:
                is_valid = True

            if min_dist < 0 or dist <= min_dist:
                min_dist = dist

        if is_valid:
            it = {
                "lat": lat,
                "lon": lon,
                "is_valid": is_valid,
                "min_dist": min_dist,
                "id": c["id"],
                "caption": str(c["name"]) + " #" + str(c["id"]),
                "name": str(c["name"]),
                "links": []
            }

            it["links"].append( ( "https://www.vodnimlyny.cz/en/?do=estateInfo&estateId=" + str(c["id"]), str(c["name"]) ) )
            it["links"].append( ( "https://www.vodnimlyny.cz/" + str(c["icon"]), "Image of " + str(c["name"]) ) )

            bisect.insort(items, it, key=lambda x: x["min_dist"])

    return items


def main():

    items = prepare_items()

    xmlns_uris = {
        'xmlns': 'http://www.topografix.com/GPX/1/1',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:schemaLocation': 'http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd'
    }

    gpx = bxml.Element("gpx", version="1.1", creator="kravinka", xmlns="http://www.topografix.com/GPX/1/1")

    for prefix, uri in xmlns_uris.items():
        gpx.attrib[prefix] = uri

    for it in items:
        wpt = bxml.SubElement(gpx, "wpt", lat=str(it["lat"]), lon=str(it["lon"]))

        bxml.SubElement(wpt, "name").text = it["caption"]

        for ln in it["links"]:
            lnk = bxml.SubElement(wpt, "link", href=ln[0])
            bxml.SubElement(lnk, "text").text = ln[1]

        if len(list(gpx)) >= result_limit_items:
            break

    bxml.ElementTree(gpx).write(result_filename)


if __name__ == '__main__':
    main()
