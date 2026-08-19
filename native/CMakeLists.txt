cmake_minimum_required(VERSION 3.20)
project(colossal_native LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Suppress CMP0148 policy warning for pybind11 find_package
if(POLICY CMP0148)
    cmake_policy(SET CMP0148 NEW)
endif()

# Find pybind11
find_package(pybind11 CONFIG REQUIRED)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Compiler warnings & flags (DXQE C++ Profile: -Wall -Wextra -Werror)
if(MSVC)
    # /wd4100 (unused parameter) mirrors -Wno-unused-parameter below, so the
    # same warning class doesn't turn into a hard error only on Windows.
    add_compile_options(/W4 /WX /wd4100)
else()
    add_compile_options(-Wall -Wextra -Werror -Wno-unused-parameter)
endif()

# Sanitizer options (DXQE requirement)
option(ENABLE_SANITIZERS "Enable AddressSanitizer and UndefinedBehaviorSanitizer" OFF)
if(ENABLE_SANITIZERS)
    if(NOT MSVC)
        add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
        add_link_options(-fsanitize=address,undefined)
    endif()
endif()

set(SOURCES
    src/discovery.cpp
    src/inspector.cpp
    src/win_argv_quote.cpp
    src/engines/native_image_engine.cpp
    src/engines/native_audio_engine.cpp
    src/engines/ffmpeg_engine.cpp
    src/engines/libreoffice_engine.cpp
    src/engines/poppler_engine.cpp
    src/engines/magick_engine.cpp
    src/engines/pandoc_engine.cpp
    src/runtime.cpp
    src/bindings.cpp
)

# Exactly one ProcessSupervisor backend is compiled per platform. Both
# implement the same contract declared in include/colossal/process.hpp.
if(WIN32)
    list(APPEND SOURCES src/process_windows.cpp)
elseif(APPLE OR UNIX)
    list(APPEND SOURCES src/process_posix.cpp)
else()
    message(FATAL_ERROR "colossal_native has no ProcessSupervisor backend for this platform")
endif()

pybind11_add_module(colossal_native ${SOURCES})

# Target properties
set_target_properties(colossal_native PROPERTIES
    PREFIX ""
    OUTPUT_NAME "colossal_native"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../src/colossal"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/../src/colossal"
)
