import pprint

class Counters(object):
  def __init__(self):
    self.counters = {}

  def inc(self, tag):
    count = self.counters.get(tag, 0)
    self.counters[tag] = count + 1
    return count

  def get(self, tag):
    return self.counters.get(tag, 0)

  def set(self, tag, count):
    self.counters[tag] = count

  def display(self):
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(self.counters)
