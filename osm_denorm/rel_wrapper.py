import util
import IPython
import shapely.geometry as shapely
from shapely.ops import linemerge

WAY_TYPE = 'w'

class WayMember(object):
  def __init__(self, pending_way):
    self.id = pending_way.ref
    self.role = pending_way.role
    self.way = None

  def is_complete(self):
    return self.way != None

  def is_outer(self):
    return self.role == 'outer'

  def is_inner(self):
    return self.role == 'inner'

class RelWrapper(object):
  def __init__(self, rel):
    self.way_members = [WayMember(m) for m in rel.members if m.type == WAY_TYPE]
    self.members_index = {m.id: m for m in self.way_members}
    self.ways = []
    self.tags = util.tags_dict(rel)
    self.id = rel.id

  def has_ways(self):
    return len(self.outer_ways()) > 0

  def is_building(self):
    return 'building' in self.tags

  def is_multipolygon(self):
    return self.tags.get('type') == 'multipolygon'

  def is_complete(self):
    return all([w.is_complete() for w in self.way_members])

  def outer_ways(self):
    return [w for w in self.way_members if w.is_outer()]

  def inner_ways(self):
    return [w for w in self.way_members if w.is_inner()]

  def add_way_to_member(self, way):
    self.members_index[way.id].way = way

  def joined_outer_ring(self):
    outer_ring = [] #2d array of geoms
    # TODO: Prune overlapping points when appending a ring section
    # or: add shapely for combining geometries
    for w in self.outer_ways():
      inserted = False
      new_segment = w.way.linestring
      if len(new_segment) == 0:
        continue
      for index in range(len(outer_ring)):
        linestring = outer_ring[index]
        if linestring[-1] == new_segment[0]:
          outer_ring.insert(index + 1, new_segment)
          inserted = True
        elif new_segment[-1] == linestring[0]:
          outer_ring.insert(index, new_segment)
          inserted = True
      if not inserted:
        outer_ring.append(new_segment)
    merged = linemerge([shapely.LineString(segment) for segment in outer_ring])
    if merged.is_closed and merged.is_valid:
      return shapely.LinearRing(merged)
    else:
      # IPython.embed()
      # could be multipolygon with 2 non-touching outer rings
      # TODO: Split those
      print('found rel with multiple closed outer rings: %d' % self.id)
      return None

  def outer_ring_contains_multiple_ways(self):
    return len(self.outer_ways()) > 1

  def outer_ring(self):
    try:
      if self.outer_ring_contains_multiple_ways():
        return self.joined_outer_ring()
      else:
        way = self.outer_ways()[0].way
        if way.is_polygon():
          return way.geometry
        else:
          print('Non-polygonal Outer Way %d for rel %d' % (way.id, self.id))
          return None
    except IndexError:
      print('found way with missing nodes??')
      return None

  def inner_rings(self):
    return [member.way.geometry for member in self.inner_ways() if member.way.is_polygon()]

  def geometry(self):
    outer = self.outer_ring()
    inner = self.inner_rings()
    if outer == None:
      return None
    else:
      return shapely.Polygon(outer, inner)

  def as_dict(self):
    return {'type': 'polygon',
            'osm_entity': 'rel',
            'osm_id': self.id,
            'tags': self.tags,
            'geometry': shapely.mapping(self.geometry())}
