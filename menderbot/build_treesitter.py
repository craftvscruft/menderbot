from os.path import dirname, join, pardir, abspath

from tree_sitter import Language

ABS_DIRNAME = dirname(abspath(__file__))
BUILD_DIR = abspath(join(ABS_DIRNAME, pardir, "build"))
VENDOR_DIR = abspath(join(ABS_DIRNAME, pardir, "vendor"))
TREE_SITTER_BINARY = join(BUILD_DIR, "my-languages.so")


if __name__ == "__main__":
    Language.build_library(
        # Store the library in the `build` directory
        TREE_SITTER_BINARY,
        # Include one or more languages
        [
            join(VENDOR_DIR, "tree-sitter-cpp"),
            join(VENDOR_DIR, "tree-sitter-java"),
            join(VENDOR_DIR, "tree-sitter-python"),
        ],
    )
