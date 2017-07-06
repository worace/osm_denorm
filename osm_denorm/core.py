import json
import osmium as o
import sys
import IPython
from osm_denorm.counters import Counters
from osm_denorm.pending_multipoly_cache import PendingMultipolyCache
import osm_denorm.util as util
import pprint


BUILDING_TAG='building'
# HIGHWAY_TAGS = [motorway trunk primary secondary tertiary
#                         unclassified residential motorway_link trunk_link primary_link]''

class OSMHandler(o.SimpleHandler):
  @staticmethod
  def run(osm_file, geometry_handler, index_type = 'sparse_mem_array'):
    print('index_type:')
    print(index_type)
    idx = o.index.create_map(index_type)
    lh = o.NodeLocationsForWays(idx)
    lh.ignore_errors()

    handler = OSMHandler(idx, geometry_handler)

    relations_pass_reader = o.io.Reader(osm_file, o.osm.osm_entity_bits.RELATION)
    o.apply(relations_pass_reader, lh, handler)
    relations_pass_reader.close()

    full_pass_reader = o.io.Reader(osm_file, o.osm.osm_entity_bits.ALL)
    o.apply(full_pass_reader, lh, handler)
    full_pass_reader.close()
    return handler

  def __init__(self, node_index, geometry_handler):
    self.geom_handler = geometry_handler
    self.idx = node_index
    super(OSMHandler, self).__init__()

    self.counters = Counters()
    self.mp_cache = PendingMultipolyCache()

  def area(self, a):
    print('got an area:')
    print(a)

  def node(self, n):
    nodes = self.counters.inc('nodes')
    if nodes % 100000 == 0:
      print("Processed %d nodes" % nodes)

  def relation(self, r):
    self.counters.inc('rels')
    if self.counters.get('rels') % 100000 == 0:
      print("Processed %d rels" % self.counters.get('rels'))
    if self.mp_cache.consider_rel(r):
      self.counters.inc('rels.multipolygon')

  def geom(self, way):
    return [[n.lon, n.lat] for n in way.nodes]

  def inspect_nodes(self, way):
    print("Way %d has %s nodes" %(way.id, len(way.nodes)))
    print(self.geom(way))

  def way(self, w):
    ways = self.counters.inc('ways')
    if ways % 100000 == 0:
      print("Processed %d ways" % ways)
    tags = util.tags_dict(w)
    if tags.get('building'):
      building_type = tags.get('building')
      self.counters.inc('building_counts.' + building_type)
    is_multipoly_member = self.mp_cache.consider_way(w)
    if not is_multipoly_member and w.is_closed() and tags.get('building'):
      self.geom_handler.completed_geometry(w)

class GeometryHandler(object):
  def completed_geometry(self, geom):
    # print(json.dumps(util.geojson_way(w)))
    print(geom)

  def run_complete(self):
    print('run complete')

if __name__ == "__main__":
  # input = sys.argv[1] or "/Users/horace/data/osm_california.pbf"
  if not sys.argv[1]:
    print("*** Error: Must provide path to OSM PBF file as argument ***")
    exit(1)
  handler = denormalize_osm_file(sys.argv[1])
  handler.counters.display()
  pp = pprint.PrettyPrinter(indent=4)
  way = handler.mp_cache.pending_multipolys[286293]['ways'][42341428]
  rel = handler.mp_cache.pending_multipolys[286293]

# Read 1
# For multipolygon relations:
#   record all member way ids (and types?) in memory or leveldb
# North America read multipolys:
# 914,700,000 Nodes
# Nodes Cache ~ 12 GB

# Read 2
# If way is a member of a multipoly
#   If there is a pending relation for that multipoly
#     insert way there
#   otherwise create one
# If that was final way for that multipoly
#   write it to output and remove its pending entry

# For normal ways, simply write them to output

# handler.counters.set('multipoly_way_ids_set.mb', sys.getsizeof(handler.ways_for_pending_multipolys) / 1000000)
# handler.counters.set('pending_multipolys.mb', sys.getsizeof(handler.pending_multipolys) / 1000000)
# IPython.embed()
# pp.pprint(handler.mp_cache.pending_multipolys)
# pp.pprint(handler.mp_cache.ways_to_rels)
