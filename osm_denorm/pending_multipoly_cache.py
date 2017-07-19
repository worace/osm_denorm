import util
import json
import osmium as o
import IPython
import shapely.geometry as shapely
from shapely.ops import linemerge
from shapely.geometry import asShape
from rel_wrapper import RelWrapper

gj = o.geom.GeoJSONFactory()

WAY_TYPE = 'w'
class PendingMultipolyCache(object):
  def __init__(self):
    self.ways_to_rels = {}
    self.pending_multipolys = {}

  # def cache_entry(self, rel):
    # ways = filter(lambda m: m.type == WAY_TYPE, rel.members)
    # ways_dict = {}
    # for w in ways:
    #   ways_dict[w.ref] = {'ref': w.ref,
    #                       'role': w.role,
    #                       'way': None}
    # return RelWrapper(rel)
    # return {'id': rel.id, 'tags': util.tags_dict(rel), 'ways': ways_dict, 'rel': rel}

  def consider_rel(self, r):
    rel = RelWrapper(r)
    if rel.is_building() and rel.is_multipolygon() and rel.has_ways() and rel.id not in self.pending_multipolys:
      if rel.id == 4043910:
        print('*** Adding rel to pending index')
        print('has ways:')
        print(rel.has_ways())
      self.pending_multipolys[rel.id] = rel
      for member in rel.way_members:
        self.ways_to_rels[member.id] = rel.id
      return True
    else:
      return False

  # def is_rel_complete(self, rel):
  #   return all(map(lambda w: w['way'], rel['ways'].values()))

  # def outer_ways(self, rel):
  #   return [w for w in rel['ways'].values() if w['role'] == 'outer']

  # def inner_ways(self, rel):
  #   return [w for w in rel['ways'].values() if w['role'] == 'inner']

  # def joined_outer_rings(self, rel):
  #   ways = rel.outer_ways()
  #   outer_ring = [] #2d array of geoms
  #   # TODO: Prune overlapping points when appending a ring section
  #   # or: add shapely for combining geometries
  #   for w in ways:
  #     inserted = False
  #     lr = util.linestring(w['way'])
  #     for index, geom in enumerate(outer_ring):
  #       if geom[-1] == lr[0]:
  #         outer_ring.insert(index + 1, lr)
  #         inserted = True
  #       elif lr[-1] == geom[0]:
  #         outer_ring.insert(index, lr)
  #         inserted = True
  #     if not inserted:
  #       outer_ring.append(lr)
  #   merged = linemerge([shapely.LineString(r) for r in outer_ring])
  #   if merged.is_closed and merged.is_valid:
  #     return shapely.LinearRing(merged)
  #   else:
  #     # could be multipolygon with 2 non-touching outer rings
  #     raise Exception('invalid geometry', merged)

  # def outer_ring(self, rel):
  #   if len(self.outer_ways(rel)) > 1:
  #     return self.joined_outer_rings(rel)
  #   else:
  #     way = self.outer_ways(rel)[0]
  #     coords = util.linestring(way['way'])
  #     return shapely.LinearRing(coords)

  def consider_way(self, way):
    if way.id in self.ways_to_rels:
      try:
        rel_id = self.ways_to_rels[way.id]
        rel = self.pending_multipolys[rel_id]
        rel.add_way_to_member(way)
        if not rel.has_ways():
          print('bad rel: %d' % rel.id)
          return (False, None)
        else:
          print('good rel: %d' % rel.id)
        if rel.is_complete():
          return (True, rel)
        else:
          return (True, None)
      except IndexError:
        print('Index error on rel: %d' % rel.id)
        return (False, None)
    else:
      return (False, None)
