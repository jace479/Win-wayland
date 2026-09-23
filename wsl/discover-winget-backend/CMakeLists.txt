cmake_minimum_required(VERSION 3.16)
project(winget-backend)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ECM REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)

set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/lib")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Network)
find_package(KF6 REQUIRED COMPONENTS CoreAddons Config I18n)

set(CMAKE_AUTOMOC ON)

add_library(DiscoverCommon SHARED IMPORTED)
set_target_properties(DiscoverCommon PROPERTIES
    IMPORTED_LOCATION /usr/lib/x86_64-linux-gnu/plasma-discover/libDiscoverCommon.so
)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}
    /home/jace479/src/discover/libdiscover
)

set(winget-backend_SRCS
    WingetClient.cpp
    WingetResource.cpp
    WingetTransaction.cpp
    WingetSourcesBackend.cpp
    WingetBackend.cpp
)

kcoreaddons_add_plugin(winget-backend SOURCES ${winget-backend_SRCS} INSTALL_NAMESPACE "discover")
target_link_libraries(winget-backend
    Qt6::Core
    Qt6::Widgets
    Qt6::Network
    KF6::CoreAddons
    KF6::ConfigCore
    KF6::I18n
    DiscoverCommon
)

set_target_properties(winget-backend PROPERTIES
    INSTALL_RPATH "/usr/lib/x86_64-linux-gnu/plasma-discover"
)

install(TARGETS winget-backend DESTINATION /usr/lib/x86_64-linux-gnu/qt6/plugins/discover)
install(FILES winget-backend-categories.xml DESTINATION ${KDE_INSTALL_DATADIR}/libdiscover/categories)
