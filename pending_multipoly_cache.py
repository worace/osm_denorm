import util
import json
import osmium as o

gj = o.geom.GeoJSONFactory()

WAY_TYPE = 'w'
class PendingMultipolyCache(object):
  def __init__(self):
    self.ways_to_rels = {}
    self.pending_multipolys = {}

  def cache_entry(self, rel):
    members = [m for m in rel.members]
    ways = filter(lambda m: m.type == WAY_TYPE, rel.members)
    ways_dict = {}
    for w in ways:
      ways_dict[w.ref] = {'type': w.type, 'ref': w.ref, 'role': w.role, 'way': None}
    return {'id': rel.id, 'tags': util.tags_dict(rel), 'ways': ways_dict, 'rel': rel}

  def consider_rel(self, rel):
    tags = util.tags_dict(rel)
    if tags.get('type') == 'multipolygon' and rel.id not in self.pending_multipolys:
      cache_entry = self.cache_entry(rel)
      self.pending_multipolys[rel.id] = cache_entry
      for way_id in cache_entry['ways']:
        self.ways_to_rels[way_id] = rel.id
      return True
    else:
      return False

  def is_rel_complete(self, rel):
    return all(map(lambda w: w['way'], rel['ways'].values()))

  def has_nested_rings(self, rel):
    outer_count = 0
    for w in rel['ways'].values():
      if w['role'] == 'outer':
        outer_count += 1
    return outer_count == 1

  def consider_way(self, way):
    if way.id in self.ways_to_rels:
      rel_id = self.ways_to_rels[way.id]
      rel = self.pending_multipolys[rel_id]
      rel['ways'][way.id]['way'] = way
      if self.is_rel_complete(rel):
        # Either:
        # multiple outer ways representing a single linear ring
        # Or 1 outer and 1 or more inner representing a donut
        print('Way %d completed rel %d' % (way.id, rel_id))

        if self.has_nested_rings(rel):
          print(json.dumps(util.geojson_rep(rel)))
        else:
          print('rel is not a nested polygon, skipping')
      return True
    else:
      return False
