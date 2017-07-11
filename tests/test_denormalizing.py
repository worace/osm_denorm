import os
import sys
import itertools
import operator
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

  def geoms_by_type(self):
    k = operator.itemgetter('osm_entity')
    s = sorted(self.geometries, key = k)
    return {k: list(g) for k, g in itertools.groupby(s, key = k)}

def test_can_collect_completed_geometries():
  geom_handler = GeomHandler()
  OSMHandler.run(test_osm_file, geom_handler)
  assert len(geom_handler.geometries) == 398
  assert len(geom_handler.geoms_by_type()['rel']) == 17
  assert len(geom_handler.geoms_by_type()['way']) == 381

def test_joining_multiple_outer_ways():
  rel_id = 6653142
  geom_handler = GeomHandler()
  OSMHandler.run(test_osm_file, geom_handler)
  rels = geom_handler.geoms_by_type()['rel']
  rel = [r for r in rels if r['osm_id'] == rel_id][0]
  assert(len(rel['geometry']['coordinates']) == 1)
