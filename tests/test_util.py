import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import osm_denorm.util as util

class MockTag(object):
  def __init__(self, key, value):
    self.k = key
    self.v = value

class MockEntity(object):
  def __init__(self, tags):
    self.tags = tags

def test_collecting_labels():
  way = MockEntity([MockTag('building', 'residential')])
  assert util.tags_dict(way) == {'building': 'residential'}
