from operator import itemgetter
import osmium

def tags_dict(entity):
  return {t.k: t.v for t in entity.tags}

def linestring(way):
  coords = []
  for n in way.nodes:
    try:
      coords.append([n.lon, n.lat])
    except osmium._osmium.InvalidLocationError:
      print('invalid location for node: %d' % n.ref)
  return coords
  # return [[n.lon, n.lat] for n in way.nodes]

def geojson_way(way):
  return {'type': 'Polygon',
          'coordinates': [linestring(way)]}

def geojson_rel(rel_dict):
  outer_to_inner = sorted(rel_dict['ways'].values(), key=itemgetter('role'), reverse=True)
  return {'type': 'Polygon',
          'coordinates': [linestring(way_dict['way']) for way_dict in outer_to_inner]}
