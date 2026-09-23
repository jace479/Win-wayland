cmake_minimum_required(VERSION 3.22)

project(kwin_win VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC OFF)

if (MSVC)
    add_compile_options(
        /permissive-
        /Zc:__cplusplus
        /utf-8
        /EHsc
        /W4
        /wd4005
        /wd4100
    )
endif()

find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets)

set(SOURCES
    src/core/main.cpp
)

qt_add_executable(kwin_win
    MANUAL_FINALIZATION
    ${SOURCES}
)

target_link_libraries(kwin_win PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    user32
    shell32
    advapi32
    comctl32
)

set_target_properties(kwin_win PROPERTIES
    WIN32_EXECUTABLE TRUE
)

qt_finalize_executable(kwin_win)
