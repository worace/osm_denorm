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
#include <osmium/index/map/dense_file_array.hpp>
#include <osmium/index/map/sparse_file_array.hpp>
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
#include "rapidjson/filewritestream.h"
#include <rapidjson/stringbuffer.h>
#include <osmium/geom/rapid_geojson.hpp>
#include <cstdio>


class CustomRelHandler : public osmium::relations::RelationsManager<CustomRelHandler, false, true, false> {
    const osmium::area::Assembler::config_type m_assembler_config;
    osmium::TagsFilter m_filter = osmium::TagsFilter{false};

public: explicit CustomRelHandler(){
    std::vector<std::string> top_level_tags = {"aeroway", "amenity", "building",
                                               "religion", "shop", "sport", "leisure"};
    std::vector<std::string> highway_tags = {"motorway", "trunk", "primary", "secondary",
                                             "tertiary", "unclassified", "residential",
                                             "motorway_link", "trunk_link", "primary_link"};
    for (const auto& tag : top_level_tags) {
        m_filter.add_rule(true, osmium::TagMatcher{tag});
    }
    for (const auto& tag : highway_tags) {
        m_filter.add_rule(true, osmium::TagMatcher{"highway", tag});
    }
}
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
        if (osmium::tags::match_any_of(way.tags(), m_filter)) {
            this->buffer().add_item(way);
            this->possibly_flush();
        }
    }

};


class GeoJSONStreamHandler : public osmium::handler::Handler {
    FILE* m_fp = stdout;
    char m_write_buffer[65536];
    rapidjson::FileWriteStream m_outstream{m_fp, m_write_buffer, sizeof(m_write_buffer)};
    rapidjson::Writer<rapidjson::FileWriteStream> m_writer{m_outstream};
    osmium::geom::RapidGeoJSONFactory<rapidjson::Writer<rapidjson::FileWriteStream>> m_factory{m_writer};
public:
    void start_feature() {
        m_writer.StartObject();
        m_writer.String("type");
        m_writer.String("Feature");
        // m_writer.String("geometry");
    }

    void end_feature() {
        m_writer.EndObject();
        m_outstream.Put('\n');
        m_writer.Reset(m_outstream);
    }

    void write_properties(osmium::OSMObject& entity) {
        m_writer.String("properties");
        m_writer.StartObject();

        m_writer.String("id");
        m_writer.Int(entity.id());

        m_writer.String("tags");
        m_writer.StartObject();
        for (const auto& tag : entity.tags()) {
            m_writer.String(tag.key());
            m_writer.String(tag.value());
        }
        m_writer.EndObject(); // end tags

        m_writer.EndObject(); //end properties
    }

    void area(osmium::Area& area) {
        try {
            start_feature();
            m_factory.create_multipolygon(area);
            write_properties(area);
            end_feature();
        } catch (const osmium::geometry_error& e) {
            std::cerr << "GEOMETRY ERROR: " << e.what() << "\n";
        }
    }

    void way(osmium::Way& way) {
        try {
            start_feature();
            if (way.is_closed()) {
                m_factory.create_polygon(way);
            } else {
                m_factory.create_linestring(way);
            }
            write_properties(way);
            end_feature();
        } catch (const osmium::geometry_error& e) {
            std::cerr << "GEOMETRY ERROR: " << e.what() << "\n";
        }
    }
};

void process_with_multipolys(std::string input_path) {
    // const int fd = ::open("/tmp/osm_index", O_RDWR | O_CREAT | O_TRUNC, 0666);
    // if (fd == -1) {
    //     std::cerr << "Can not open location cache file " << std::strerror(errno) << "\n";
    //     std::exit(1);
    // }

    // using index_type = osmium::index::map::SparseMemArray<osmium::unsigned_object_id_type, osmium::Location>;
    using index_type = osmium::index::map::FlexMem<osmium::unsigned_object_id_type, osmium::Location>;
    // using index_type = osmium::index::map::DenseFileArray<osmium::unsigned_object_id_type, osmium::Location>;
    // using index_type = osmium::index::map::SparseFileArray<osmium::unsigned_object_id_type, osmium::Location>;
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

    GeoJSONStreamHandler handler;
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
    std::string input;
    if (argc < 2) {
        input = "../tests/dc_sample.pbf";
    } else {
        input = argv[1];
    }
    std::cerr << "Read File:" << input << "\n";

    process_with_multipolys(input);
    return 0;
}
