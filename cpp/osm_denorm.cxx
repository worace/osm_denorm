#include <stdio.h>
#include <stdlib.h>
#include <osmium/osm/types.hpp>
#include <osmium/osm/node.hpp>
#include <osmium/index/map/flex_mem.hpp>
#include <osmium/osm/way.hpp>
#include <osmium/osm/location.hpp>
#include <osmium/io/gzip_compression.hpp>
#include <osmium/io/pbf_input.hpp>
#include <osmium/index/map/sparse_mem_array.hpp>
#include <osmium/handler/node_locations_for_ways.hpp>
#include <osmium/handler.hpp>
#include <osmium/visitor.hpp>
#include <osmium/osm/relation.hpp>
#include <osmium/relations/relations_manager.hpp>
#include <osmium/relations/manager_util.hpp>
#include <osmium/relations/members_database.hpp>
#include <osmium/relations/relations_database.hpp>
#include <osmium/geom/factory.hpp>
#include <osmium/geom/geojson.hpp>
#include <osmium/area/assembler.hpp>
#include <osmium/area/multipolygon_manager.hpp>
// For the WKT factory
#include <osmium/geom/wkt.hpp>

//rapidjson
#include <rapidjson/writer.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/document.h>
#include <osmium/geom/rapid_geojson.hpp>
#include <osmium/geom/rapid_geojson_document.hpp>

class WayHandler : public osmium::handler::Handler {
public:
    void way(const osmium::Way& way) {
        int node_count = 0;
        for (const auto& n : way.nodes()) {
            node_count++;
            // std::cout << n.ref() << ": " << n.lon() << ", " << n.lat() << '\n';
        }
        std::cout << "way " << way.id() << " with " << node_count << " nodes" << '\n';
        // osmium::geom::GeoJSONFactory<> factory{};
        if (way.is_closed()) {
            std::cout << "*** POLYGON ***" << '\n';
            // std::string json = factory.create_polygon(way);
            // std::cout << json << '\n';
        } else {
            std::cout << "*** LineString ***" << '\n';
            // std::string json = factory.create_linestring(way);
            // std::cout << json << '\n';
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

class CustomRelHandler : public osmium::relations::RelationsManager<CustomRelHandler, false, true, false> {
    const osmium::area::Assembler::config_type m_assembler_config;
    const osmium::TagsFilter m_filter = osmium::TagsFilter{true};
public: explicit CustomRelHandler(){}
    bool new_relation(const osmium::Relation& relation) const {
        const char* type = relation.tags().get_value_by_key("type");

        // ignore relations without "type" tag
        if (type == nullptr) {
            return false;
        }

        if (((!std::strcmp(type, "multipolygon")) || (!std::strcmp(type, "boundary"))) && osmium::tags::match_any_of(relation.tags(), m_filter)) {
            return std::any_of(relation.members().cbegin(), relation.members().cend(), [](const osmium::RelationMember& member) {
                    return member.type() == osmium::item_type::way;
                });
        }

        return false;
    }

    void complete_relation(const osmium::Relation& relation) {
        std::vector<const osmium::Way*> ways;
        ways.reserve(relation.members().size());
        for (const auto& member : relation.members()) {
            if (member.ref() != 0) {
                ways.push_back(this->get_member_way(member.ref()));
                assert(ways.back() != nullptr);
            }
        }

        try {
            osmium::area::Assembler assembler{m_assembler_config};
            assembler(relation, ways, this->buffer());
            // m_stats += assembler.stats();
        } catch (const osmium::invalid_location&) {
            // XXX ignore
        }
    }

    void after_way(const osmium::Way& way) {
        // you need at least 4 nodes to make up a polygon
        if (way.nodes().size() <= 3) {
            return;
        }

        try {
            if (!way.nodes().front().location() || !way.nodes().back().location()) {
                throw osmium::invalid_location{"invalid location"};
            }
            if (way.ends_have_same_location()) {
                if (way.tags().has_tag("area", "no")) {
                    return;
                }

                if (osmium::tags::match_none_of(way.tags(), m_filter)) {
                    return;
                }

                osmium::area::Assembler assembler{m_assembler_config};
                assembler(way, this->buffer());
                // m_stats += assembler.stats();
                this->possibly_flush();
            }
        } catch (const osmium::invalid_location&) {
            // XXX ignore
        }
    }

    void way_not_in_any_relation(const osmium::Way& way) {
        // TODO: tag filtering etc
        this->buffer().add_item(way);
        this->possibly_flush();
    }

};

class GeoJSONHandler : public osmium::handler::Handler {
    osmium::geom::RapidGeoJSONDocumentFactory<> m_factory;

public:
    std::string json_string(rapidjson::Document& document) {
        rapidjson::StringBuffer stream;
        rapidjson::Writer<rapidjson::StringBuffer> writer(stream);
        document.Accept(writer);
        return stream.GetString();
    }


    void area(const osmium::Area& area) {
        try {
            std::cerr << "*** Completed Area ***" << '\n';
            rapidjson::Document doc = m_factory.create_multipolygon(area);
            std::cout << json_string(doc) << "\n";
        } catch (const osmium::geometry_error& e) {
            std::cerr << "GEOMETRY ERROR: " << e.what() << "\n";
        }
    }

    void way(const osmium::Way& way) {
        try {
            if (way.is_closed()) {
                // TODO: Don't work for some reason:
                std::cerr << "*** Way Polygon ***" << '\n';
                rapidjson::Document doc = m_factory.create_polygon(way);
                std::cout << json_string(doc) << "\n";
            } else {
                std::cerr << "*** WAY LINESTRING ***" << '\n';
                rapidjson::Document doc = m_factory.create_linestring(way);
                std::cout << json_string(doc) << "\n";
            }
        } catch (const osmium::geometry_error& e) {
            std::cerr << "GEOMETRY ERROR: " << e.what() << "\n";
        }
    }
};

void process_with_multipolys(std::string input_path) {
    // using index_type = osmium::index::map::SparseMemArray<osmium::unsigned_object_id_type, osmium::Location>;
    using index_type = osmium::index::map::FlexMem<osmium::unsigned_object_id_type, osmium::Location>;
    using location_handler_type = osmium::handler::NodeLocationsForWays<index_type>;

    osmium::io::File input_file{input_path};
    osmium::area::Assembler::config_type assembler_config;

    // CustomMPHandler mp_manager{assembler_config};
    CustomRelHandler mp_manager;

    std::cerr << "Pass 1...\n";
    osmium::relations::read_relations(input_file, mp_manager);

    std::cerr << "Memory:\n";
    osmium::relations::print_used_memory(std::cerr, mp_manager.used_memory());

    std::cerr << "Pass 2...\n";
    index_type index;
    location_handler_type location_handler{index};
    location_handler.ignore_errors();

    GeoJSONHandler handler;
    osmium::io::Reader reader{input_file};
    osmium::apply(reader, location_handler,
                  mp_manager.handler([&handler](osmium::memory::Buffer&& buffer) {
                          osmium::apply(buffer, handler);
                      }));
    reader.close();
    std::cerr << "Pass 2 done\n";
}

int main (int argc, char *argv[])
{
    std::string input = "../tests/dc_sample.pbf";
    // process_ways_with_handler(input);
    // process_relations(input);
    process_with_multipolys(input);
    return 0;
}
