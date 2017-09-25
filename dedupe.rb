#!/usr/bin/env ruby

require "json"

# last = {"geometry" => {} "properties" => {"tags" => {}}}
last = nil

def get_ring(feature)
  return [] unless feature
  geometry = feature["geometry"]
  if geometry["type"] == "Polygon"
    geometry["coordinates"][0]
  elsif geometry["type"] == "LineString"
    geometry["coordinates"]
  else
    geometry["coordinates"][0][0]
  end
end

def get_tags(feature)
  return {} unless feature
  feature["properties"]["tags"]
end

$stdin.each_line do |line|
  begin
    data = JSON.parse(line.chomp)
    if get_tags(last) != get_tags(data)
      last = data
      puts data.to_json
    else
      # STDERR.puts("found dupe")
    end
  rescue
    STDERR.puts("error processing line: #{line}")
  end
end

# Possible Discrepancies
# * errors in my script cause invalid rows (~ 30)
# * official tool repeats some geometries that match both linear
#   and area tags (count unknown)
# * my tool outputs tags differently for same geometries (count unknown)

# Needs from official tool:
# * Include all Tags in properties
# * optional: Exclude points (not necessarily mandatory; could do this after)
# * optional: output single-ring geoms as polygons
