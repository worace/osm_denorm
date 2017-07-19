import util

WAY_TYPE = 'w'

class WayMember(object):
  def __init__(self, way, rel):
    self.pending_way = way
    self.rel = rel
    self.way = None

  def is_complete(self):
    return self.way != None

  @property
  def id(self):
    return self.pending_way.ref

  @property
  def role(self):
    return self.pending_way.role

  def is_outer(self):
    return self.role == 'outer'

  def is_inner(self):
    return self.role == 'inner'

class RelWrapper(object):
  def __init__(self, rel):
    self.rel = rel
    self.way_members = [WayMember(m, self) for m in self.rel.members if m.type == WAY_TYPE]
    self.members_index = {m.id: m for m in self.way_members}
    self.ways = []
    self.tags = util.tags_dict(self.rel)
    self.id = self.rel.id

  def add_way(self, way):
    self.ways.append(way)

  def way_members(self):
    return filter(lambda m: m.type == WAY_TYPE, self.rel.members)

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

  def outer_ring(self):
    "..."

  def inner_rings(self):
    "..."

  def geojson(self):
    "..."
