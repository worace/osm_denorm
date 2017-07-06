import osm_denorm.util as util
import json
import osmium as o
import IPython

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
    if tags.get('building') and tags.get('type') == 'multipolygon' and rel.id not in self.pending_multipolys:
      cache_entry = self.cache_entry(rel)
      self.pending_multipolys[rel.id] = cache_entry
      for way_id in cache_entry['ways']:
        self.ways_to_rels[way_id] = rel.id
      return True
    else:
      return False

  def is_rel_complete(self, rel):
    return all(map(lambda w: w['way'], rel['ways'].values()))

  def outer_ways(self, rel):
    return [w for w in rel['ways'].values() if w['role'] == 'outer']

  def inner_ways(self, rel):
    return [w for w in rel['ways'].values() if w['role'] == 'inner']

  def join_outer_rings(self, rel):
    ways = self.outer_ways(rel)
    outer_ring = [] #2d array of geoms
    # TODO: Prune overlapping points when appending a ring section
    for w in ways:
      inserted = False
      lr = util.linear_ring(w['way'])
      for index, geom in enumerate(outer_ring):
        if geom[-1] == lr[0]:
          outer_ring.insert(index + 1, lr)
          inserted = True
        elif lr[-1] == geom[0]:
          outer_ring.insert(index, lr)
          inserted = True

      if not inserted:
        outer_ring.append(lr)

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

        if len(self.outer_ways(rel)) > 1:
          # Rel has an outer ring composed of multiple ways, need to join them
          self.join_outer_rings(rel)
          # print(json.dumps(util.geojson_rep(rel)))
        else:
          print(json.dumps(util.geojson_rep(rel)))
      return True
    else:
      return False
