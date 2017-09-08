#include <stdio.h>
#include <stdlib.h>
#include <osmium/osm/types.hpp>
#include <osmium/osm/node.hpp>
#include <osmium/osm/way.hpp>
#include <osmium/osm/location.hpp>
#include <osmium/io/gzip_compression.hpp>
#include <osmium/io/pbf_input.hpp>
#include <osmium/index/map/sparse_mem_array.hpp>
#include <osmium/handler/node_locations_for_ways.hpp>
#include <osmium/handler.hpp>
#include <osmium/visitor.hpp>
#include <osmium/relations/relations_manager.hpp>
#include <osmium/geom/geojson.hpp>

class WayHandler : public osmium::handler::Handler {
public:
    void way(const osmium::Way& way) {
        int node_count = 0;
        for (const auto& n : way.nodes()) {
          node_count++;
          // std::cout << n.ref() << ": " << n.lon() << ", " << n.lat() << '\n';
        }
        std::cout << "way " << way.id() << " with " << node_count << " nodes" << '\n';
        osmium::geom::GeoJSONFactory<> factory{};
        if (way.is_closed()) {
          std::cout << "*** POLYGON ***" << '\n';
          std::string json = factory.create_polygon(way);
          std::cout << json << '\n';
        } else {
          std::string json = factory.create_linestring(way);
          std::cout << json << '\n';
        }

    }
};

class RelationManager : public osmium::relations::RelationsManager<RelationManager, false, true, false> {
public : void complete_relation(const osmium::Relation& relation) {
    // Iterate over all members
    for (const auto& member : relation.members()) {
      // member.ref() will be 0 for all members you are not interested
      // in. The objects for those members are not available.
      if (member.ref() != 0) {
        // Get the member object
        const osmium::OSMObject* obj = this->get_member_object(member);
        std::cout << "member type: " << obj->type() << "\n";

        // If you know which type you have you can also use any of these:
        // const osmium::Node* node         = this->get_member_node(member.ref());
        // const osmium::Way* way           = this->get_member_way(member.ref());
        // const osmium::Relation* relation = this->get_member_relation(member.ref());
      }
    }
  }

  void way_not_in_any_relation(const osmium::Way& way) {
    fprintf(stdout,"Way not in any relation %lld\n", way.id());
  }
};


void process_ways_with_handler(std::string input_path) {
  osmium::io::File input_file{input_path};

  auto otypes = osmium::osm_entity_bits::node | osmium::osm_entity_bits::way;

  osmium::io::Reader reader{input_file, otypes};

  // namespace map = osmium::index::map;
  using index_type = osmium::index::map::SparseMemArray<osmium::unsigned_object_id_type, osmium::Location>;
  using location_handler_type = osmium::handler::NodeLocationsForWays<index_type>;
  index_type index;
  location_handler_type location_handler{index};

  WayHandler handler;
  osmium::apply(reader, location_handler, handler);
  reader.close();
}

void print_counts() {
  osmium::io::File input_file{"../tests/dc_sample.pbf"};

  auto otypes = osmium::osm_entity_bits::node | osmium::osm_entity_bits::way;

  osmium::io::Reader reader{input_file, otypes};
  osmium::io::Header header = reader.header();

  int entities = 0;
  int buffers = 0;

  while (osmium::memory::Buffer buffer = reader.read()) {
    buffers++;
    for (auto& item : buffer) {
      entities++;
    }
  }
  reader.close();

  fprintf(stdout,"Read %d entities in %d buffers\n", entities, buffers);
}

void process_relations(std::string input_path) {
  osmium::io::File input_file{input_path};
  RelationManager mgr;
  osmium::relations::read_relations(input_file, mgr);
  osmium::io::Reader reader{input_file};
  osmium::apply(reader, mgr.handler());

  // osmium::memory::Buffer = manager.read();
  reader.close();
}

int main (int argc, char *argv[])
{
  std::string input = "../tests/dc_sample.pbf";
  process_ways_with_handler(input);
  // process_relations(input);
  return 0;
}
