cmake_minimum_required(VERSION 3.0)

project(pygenda_clipboard C)

find_package(PkgConfig REQUIRED)
pkg_check_modules(GTK REQUIRED gtk+-3.0)

add_compile_options(-Wall)
#add_compile_options(-Werror)

# Target: pygenda_clipboard

add_library(pygenda_clipboard SHARED pygenda_clipboard.c)

target_include_directories(pygenda_clipboard PUBLIC ${GTK_INCLUDE_DIRS})

if(UNIX)
    # We want to strip the library, so add as a custom post-build command
    add_custom_command(TARGET pygenda_clipboard
        POST_BUILD
        COMMENT "Stripping debug info from library..."
        COMMAND strip $<TARGET_FILE:pygenda_clipboard>
    )
endif()

# Target: cp

add_custom_target(cp DEPENDS pygenda_clipboard
    COMMENT "Copying library to pygenda directory..."
    COMMAND cp $<TARGET_FILE:pygenda_clipboard> ../pygenda/
)
