from operator import itemgetter

def tags_dict(entity):
  return {t.k: t.v for t in entity.tags}

def geometry(way):
  return [[n.lon, n.lat] for n in way.nodes]

def linear_ring(way):
  return [[n.lon, n.lat] for n in way.nodes]

def geojson_way(way):
  return {'type': 'Polygon',
          'coordinates': [linear_ring(way)]}

def geojson_rep(rel_dict):
  outer_to_inner = sorted(rel_dict['ways'].values(), key=itemgetter('role'), reverse=True)
  return {'type': 'Feature',
          'properties': rel_dict['tags'],
          'geometry': {
            'type': 'Polygon',
            'coordinates': [linear_ring(way_dict['way']) for way_dict in outer_to_inner]
          }}
