cmake_minimum_required(VERSION 3.10)
project(quickjs_wrapper LANGUAGES C)

# Set up to include the main quickjs directory
add_subdirectory(../../quickjs quickjs_build)

add_library(qjswrapper SHARED wrapper.c)
target_link_libraries(qjswrapper PRIVATE qjs)
