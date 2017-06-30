import osmium as o
import sys
import IPython
from counters import Counters

class WayHandler(o.SimpleHandler):
  def __init__(self, idx):
    self.embed = False
    self.counters = Counters()
    super(WayHandler, self).__init__()
    self.idx = idx

    self.ways_index = {}
    self.pending_multipolys = {}
    self.ways_for_pending_multipolys = set()

  def node(self, n):
    nodes = self.counters.inc('nodes')
    if nodes % 100000 == 0:
      print("Processed %d nodes" % nodes)

  def pending_multipoly(self, rel, tags):
    # For a rel, create a pending entry containing
    # {id,
    #  tags,
    #  ways: {
    #   id: {type: , role: , ref: }
    #  }
    members = [m for m in rel.members]
    ways_dict = {}
    for m in members:
      if not m.type == 'w':
        self.counters.inc('non_way_multipoly_member.' + m.type)
      else:
        ways_dict[m.ref] = {'type': m.type, 'ref': m.ref, 'role': m.role}

    return {'id': rel.id, 'tags': tags, 'ways': ways_dict}

  def relation(self, r):
    self.counters.inc('rels')
    if self.embed:
      IPython.embed()
    if self.counters.get('rels') % 100000 == 0:
      print("Processed %d rels" % self.counters.get('rels'))
    tags = self.tags(r)
    if tags.get('type') == 'multipolygon':
      pending_entry = self.pending_multipoly(r, tags)
      self.pending_multipolys[r.id] = pending_entry
      for way_id in pending_entry['ways']:
        self.ways_for_pending_multipolys.add(way_id)
      self.counters.inc('rels.multipolygon')

    # if tags.get('name') == 'International Monetary Fund':
    #   IPython.embed()

  def geom(self, way):
    return [[n.lon, n.lat] for n in way.nodes]

  def tags(self, entity):
    return {t.k: t.v for t in entity.tags}

  def inspect_nodes(self, way):
    print("Way %d has %s nodes" %(way.id, len(way.nodes)))
    print(self.geom(way))

  def way(self, w):
    ways = self.counters.inc('ways')
    if ways % 100000 == 0:
      self.inspect_nodes(w)
      print("Processed %d ways" % ways)
    tags = self.tags(w)
    self.ways_index[w.id] = w
    if tags.get('building'):
      building_type = tags.get('building')
      self.counters.inc('building_counts.' + building_type)
    if tags.get('role') == 'inner':
      self.counters.inc('ways.inner')
    if tags.get('role') == 'outer':
      self.counters.inc('ways.outer')


input = sys.argv[1] or "/Users/horace/data/osm_california.pbf"
reader = o.io.Reader(input, o.osm.osm_entity_bits.ALL)

idx = o.index.create_map("sparse_mem_array")

lh = o.NodeLocationsForWays(idx)
lh.ignore_errors()

handler = WayHandler(idx)
o.apply(reader, lh, handler)

reader.close()

# Read 1
# For multipolygon relations:
#   record all member way ids (and types?) in memory or leveldb
# North America read multipolys:

# Read 2
# If way is a member of a multipoly
#   If there is a pending relation for that multipoly
#     insert way there
#   otherwise create one
# If that was final way for that multipoly
#   write it to output and remove its pending entry

# For normal ways, simply write them to output

handler.counters.set('multipoly_way_ids_set.mb', sys.getsizeof(handler.ways_for_pending_multipolys) / 1000000)
handler.counters.set('pending_multipolys.mb', sys.getsizeof(handler.pending_multipolys) / 1000000)
handler.counters.display()
