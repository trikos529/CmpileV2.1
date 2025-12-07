import re

# Simple mapping of common headers to vcpkg package names
# This is non-exhaustive and will need updates.
HEADER_MAPPING = {
    "nlohmann/json.hpp": "nlohmann-json",
    "fmt/core.h": "fmt",
    "fmt/format.h": "fmt",
    "spdlog/spdlog.h": "spdlog",
    "sqlite3.h": "sqlite3",
    "curl/curl.h": "curl",
    "gtest/gtest.h": "gtest",
    "GL/glew.h": "glew",
    "GLFW/glfw3.h": "glfw3",
    "glm/glm.hpp": "glm",
    "zlib.h": "zlib",
    "openssl/ssl.h": "openssl",
    "boost/asio.hpp": "boost-asio", # Boost is modular in vcpkg
    # Add more as needed
}

def find_includes(file_path):
    """
    Scans a C/C++ file for #include directives.
    Returns a set of included files (strings).
    """
    includes = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Regex for #include <path> or #include "path"
                match = re.search(r'^\s*#include\s*[<"]([^>"]+)[>"]', line)
                if match:
                    includes.add(match.group(1))
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    return includes

def map_includes_to_packages(includes):
    """
    Maps a list of include paths to potential vcpkg package names.
    Returns a set of package names.
    """
    packages = set()
    for inc in includes:
        # Check exact match in mapping
        if inc in HEADER_MAPPING:
            packages.add(HEADER_MAPPING[inc])
            continue
        
        # Check heuristics
        # Logic: if include is "foo/bar.h", try mapping "foo" if it's not standard
        # Identifying standard libs is hard without a list, but we can try ignoring them?
        # For now, minimal heuristics to avoid false positives on std libs (iostream, vector, etc)
        # Assuming vcpkg packages usually live in subdirs or have known headers.
        
        # We can detect if it looks like a library (has a slash)
        if '/' in inc:
            parts = inc.split('/')
            root = parts[0]
            # Try to map the root folder if it matches a known pattern?
            # actually commonly libs match the folder name: generic usage
            # but let's be conservative and only use the explicit map for now unless requested otherwise.
            pass
            
    return packages
