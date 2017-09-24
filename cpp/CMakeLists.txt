cmake_minimum_required (VERSION 2.6)
project (osmdenorm)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")
find_package(Osmium REQUIRED COMPONENTS pbf io)

if(NOT OSMIUM_FOUND)
    message(WARNING "Libosmium not found!\n")
endif()

set (CMAKE_CXX_STANDARD 11)
set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -lpthread -lz")

include_directories(${OSMIUM_INCLUDE_DIRS})
# include_directories("/usr/include")
link_directories("/usr/lib/x86_64-linux-gnu")

add_executable(osmdenorm osm_denorm.cxx)

find_package( ZLIB REQUIRED )
if ( ZLIB_FOUND )
    include_directories( ${ZLIB_INCLUDE_DIRS} )
    target_link_libraries( osmdenorm ${ZLIB_LIBRARIES} )
endif( ZLIB_FOUND )

find_package (Threads)
target_link_libraries( osmdenorm ${CMAKE_THREAD_LIBS_INIT} )
