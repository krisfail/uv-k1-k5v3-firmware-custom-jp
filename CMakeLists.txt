cmake_minimum_required(VERSION 3.22)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS ON)


if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Debug")
endif()

set(CMAKE_PROJECT_NAME wrx-jp)

# Enable compile command to ease indexing with e.g. clangd
set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)

project(${CMAKE_PROJECT_NAME})
message("Build type: " ${CMAKE_BUILD_TYPE})

enable_language(C ASM)

# This repository distributes one firmware profile: Japanese, receive-only.
# Force the policy at the CMake boundary so an inherited cache or an ad-hoc
# -D option cannot re-enable RF transmit sources.
set(ENABLE_RX_ONLY ON CACHE BOOL "Build the receive-only Japanese profile" FORCE)
foreach(_rx_only_disabled_feature IN ITEMS
    ENABLE_AIRCOPY
    ENABLE_ALARM
    ENABLE_DTMF_CALLING
    ENABLE_NOAA
    ENABLE_VOICE
    ENABLE_VOX
    ENABLE_SPECTRUM
    ENABLE_FEAT_F4HWN_BEAM
    ENABLE_FEAT_F4HWN_FOXHUNT
    ENABLE_FEAT_F4HWN_GAME
    ENABLE_FEAT_F4HWN_K5VIEWER
    ENABLE_FEAT_F4HWN_SPECTRUM
    ENABLE_FEAT_F4HWN_CHARGING_C
    ENABLE_FEAT_F4HWN_RESCUE_OPS
    ENABLE_FEAT_F4HWN_VOL
    ENABLE_FEAT_F4HWN_PMR
    ENABLE_FEAT_F4HWN_GMRS_FRS_MURS
    ENABLE_FEAT_F4HWN_DEBUG
    ENABLE_FEAT_F4HWN_MEM
    ENABLE_FEAT_F4HWN_QRCODE
    ENABLE_FEAT_F4HWN_RXTX_LOG
    ENABLE_FEAT_F4HWN_RXTX_LOG_WRAP
    ENABLE_FEAT_F4HWN_RXTX_LOG_K5VIEWER
    ENABLE_FEAT_F4HWN_RX_TX_TIMER
    ENABLE_FEAT_F4HWN_CA
    ENABLE_REDUCE_LOW_MID_TX_POWER
    ENABLE_TX1750
    ENABLE_TX_WHEN_AM
)
    set(${_rx_only_disabled_feature} OFF CACHE BOOL
        "Disabled by the wrx-jp receive-only policy" FORCE)
endforeach()

# Keep an ad-hoc CMake invocation aligned with the only distributed profile.
set(ENABLE_FEAT_F4HWN ON CACHE BOOL "Enable the wrx-jp feature set" FORCE)
set(ENABLE_JAPANESE ON CACHE BOOL "Enable Japanese display paths" FORCE)
set(ENABLE_FMRADIO ON CACHE BOOL "Enable domestic FM broadcast reception" FORCE)
# K1 has enough flash for the independent RX audio profiles (FM/AM/USB).
set(ENABLE_FEAT_F4HWN_AUDIO ON CACHE BOOL "Enable receive audio profiles" FORCE)

find_package(Git QUIET)
set(BUILD_COMMIT "unknown")
if(GIT_FOUND AND EXISTS "${CMAKE_SOURCE_DIR}/.git")
    execute_process(
        COMMAND "${GIT_EXECUTABLE}" rev-parse --short HEAD
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        OUTPUT_VARIABLE BUILD_COMMIT
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET
    )
    if(NOT BUILD_COMMIT)
        set(BUILD_COMMIT "unknown")
    endif()
endif()

if(ENABLE_FEAT_F4HWN)
    if(NOT AUTHOR_STRING_1)
        set(AUTHOR_STRING_1 "EGZUMER")
    endif()
    if(NOT AUTHOR_STRING_2)
        set(AUTHOR_STRING_2 "Kris")
    endif()
    if(NOT VERSION_STRING_1)
        set(VERSION_STRING_1 "v0.22")
    endif()
    if(NOT VERSION_STRING_2)
        set(VERSION_STRING_2 "v5.9.0J1")
    endif()
    if(NOT EDITION_STRING)
        set(EDITION_STRING "JP-RX-Only")
    endif()
    if(NOT AUTHOR_STRING)
        set(AUTHOR_STRING "${AUTHOR_STRING_1}+${AUTHOR_STRING_2}")
    endif()
    if(NOT VERSION_STRING)
        set(VERSION_STRING ${VERSION_STRING_2})
    endif()
else()
    if(NOT AUTHOR_STRING)
        set(AUTHOR_STRING "EGZUMER")
    endif()
    if(NOT VERSION_STRING)
        set(VERSION_STRING "NOGIT")
    endif()
endif()

if(TARGET)
    set(EXE_NAME ${TARGET})
else()
    set(EXE_NAME "wrx-jp")
endif()

set(DISPLAY_VERSION_STRING_2 "${VERSION_STRING_2}")

message("EXE_NAME = " ${EXE_NAME})

add_executable(${EXE_NAME})

add_subdirectory(Drivers)
add_subdirectory(Middlewares)
add_subdirectory(Core)
add_subdirectory(App)

target_link_libraries(${EXE_NAME} Core App)

target_compile_definitions(${EXE_NAME} PRIVATE $<$<CONFIG:Debug>:DEBUG>)
target_link_libraries(${EXE_NAME} ${TOOLCHAIN_LINK_LIBRARIES})

if(ENABLE_LTO)
    target_compile_options(${EXE_NAME} PRIVATE -flto=auto)
endif()

# Generate map file
target_link_options(${EXE_NAME} PRIVATE "-Wl,-Map=${EXE_NAME}.map")

# Add the map file to the list of files to be removed with 'clean' target
set_target_properties(${EXE_NAME} PROPERTIES ADDITIONAL_CLEAN_FILES ${EXE_NAME}.map)

# Force linker to ignore RWX segment warning even if cache exists
target_link_options(${EXE_NAME} PRIVATE -Wl,--no-warn-rwx-segment)

# -----------------------------------
#  Font/bitmap inspection artifacts
#
# The JSON manifest is the source of truth for source selection and code-point
# annotations.  The C arrays remain firmware data; this target only renders
# inspection artifacts and never rewrites them.
find_package(Python3 COMPONENTS Interpreter QUIET)
set(FONT_ATLAS_DIR "${CMAKE_SOURCE_DIR}/docs/assets/font-atlas")
set(FONT_ATLAS_MANIFEST "${CMAKE_SOURCE_DIR}/tools/font_inventory.json")
set(FONT_ATLAS_MARKDOWN "${FONT_ATLAS_DIR}/font_inventory.generated.ja.md")
set(FONT_ATLAS_SOURCES
    "${CMAKE_SOURCE_DIR}/App/font.c"
    "${CMAKE_SOURCE_DIR}/App/japanese_font.c"
    "${CMAKE_SOURCE_DIR}/App/bitmaps.c"
)

if(Python3_Interpreter_FOUND)
    add_custom_target(font-atlas
        COMMAND ${CMAKE_COMMAND} -E make_directory "${FONT_ATLAS_DIR}"
        COMMAND ${Python3_EXECUTABLE} "${CMAKE_SOURCE_DIR}/tools/render_bitmap_atlas.py"
            --manifest "${FONT_ATLAS_MANIFEST}"
            --out "${FONT_ATLAS_DIR}"
            --markdown-out "${FONT_ATLAS_MARKDOWN}"
        WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
        DEPENDS
            "${CMAKE_SOURCE_DIR}/tools/render_bitmap_atlas.py"
            "${FONT_ATLAS_MANIFEST}"
            ${FONT_ATLAS_SOURCES}
        BYPRODUCTS
            "${FONT_ATLAS_DIR}/bitmap_atlas.svg"
            "${FONT_ATLAS_DIR}/bitmap_atlas_inventory.json"
            "${FONT_ATLAS_MARKDOWN}"
        COMMENT "Rendering the canonical font/bitmap inventory and atlas"
        VERBATIM
    )
else()
    add_custom_target(font-atlas
        COMMAND ${CMAKE_COMMAND} -E echo "Python 3 is required for the font-atlas target"
        COMMAND ${CMAKE_COMMAND} -E false
    )
endif()

add_custom_target(atlas DEPENDS font-atlas)
add_custom_target(inventory DEPENDS font-atlas)
add_custom_target(docs DEPENDS font-atlas)

# -----------------------------------
#  Post build processing
#

# Generate .bin file
add_custom_command(
    TARGET ${EXE_NAME}
    POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O binary ${EXE_NAME}.elf ${EXE_NAME}.bin
    COMMENT "Generating .bin file"
)

# Generate .hex file
add_custom_command(
    TARGET ${EXE_NAME}
    POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex ${EXE_NAME}.elf ${EXE_NAME}.hex
    COMMENT "Generating .hex file"
)

# Pack
# TODO: Incorparate venv?
# if(ENABLE_FEAT_F4HWN)
#     add_custom_command(
#         TARGET ${EXE_NAME}
#         POST_BUILD
#         COMMAND python ${CMAKE_SOURCE_DIR}/fw-pack.py ${TARGET_ELF} ${AUTHOR_STRING_2} ${VERSION_STRING_2} ${EXE_NAME}.packed.bin
#         COMMENT "Generating packed binary"
#     )
# else()
#     add_custom_command(
#         TARGET ${EXE_NAME}
#         POST_BUILD
#         COMMAND python ${CMAKE_SOURCE_DIR}/fw-pack.py ${TARGET_ELF} ${AUTHOR_STRING} ${VERSION_STRING} ${EXE_NAME}.packed.bin
#         COMMENT "Generating packed binary"
#     )
# endif()
