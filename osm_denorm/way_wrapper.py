import util
import shapely.geometry as shapely

class WayWrapper(object):
  def __init__(self, way):
    self.id = way.id
    self.linestring = util.linestring(way)
    self.tags = util.tags_dict(way)
    try:
      self.geometry = shapely.LineString(self.linestring)
    except ValueError:
      self.geometry = None
      print('Way with invalid geometry: %d' % self.id)
      print(self.linestring)

  def has_valid_geometry(self):
    return self.geometry != None

  def is_building(self):
    return 'building' in self.tags

  def is_polygon(self):
    return self.geometry and self.geometry.is_valid and self.geometry.is_closed
