cmake_minimum_required (VERSION 2.6)
project (osmdenorm)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
find_package(Osmium REQUIRED COMPONENTS pbf io)

if(NOT OSMIUM_FOUND)
    message(WARNING "Libosmium not found!\n")
endif()

set (CMAKE_CXX_STANDARD 11)
set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -lpthread -lz")

# include_directories(${OSMIUM_INCLUDE_DIRS})
include_directories("/usr/include")

add_executable(osmdenorm osm_denorm.cxx)
# add_executable(osmium_example osmium_area_test.cpp)
