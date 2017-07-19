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

  def consider_rel(self, r):
    rel = RelWrapper(r)
    if rel.is_building() and rel.is_multipolygon() and rel.has_ways() and rel.id not in self.pending_multipolys:
      self.pending_multipolys[rel.id] = rel
      for member in rel.way_members:
        self.ways_to_rels[member.id] = rel.id
      return True
    else:
      return False

  def consider_way(self, way):
    if way.id in self.ways_to_rels:
      rel_id = self.ways_to_rels[way.id]
      rel = self.pending_multipolys[rel_id]
      rel.add_way_to_member(way)
      if rel.is_complete():
        return (True, rel)
      else:
        return (True, None)
    else:
      return (False, None)
