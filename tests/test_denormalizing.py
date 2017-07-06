import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from osm_denorm.core import OSMHandler
test_osm_file = "./tests/dc_sample.pbf"

class GeomHandler(object):
  def __init__(self):
    self.geometries = []

  def completed_geometry(self, geom):
    self.geometries.append(geom)

  def run_complete(self):
    return None

def test_can_collect_completed_geometries():
  geom_handler = GeomHandler()
  OSMHandler.run(test_osm_file, geom_handler)
  assert len(geom_handler.geometries) == 381
