from os.path import abspath, dirname, exists, join, pardir

from tree_sitter import Language

ABS_DIRNAME = dirname(abspath(__file__))
BUILD_DIR = abspath(join(ABS_DIRNAME, pardir, "build"))
VENDOR_DIR = abspath(join(ABS_DIRNAME, pardir, "vendor"))
__TREE_SITTER_BINARY__ = join(BUILD_DIR, "my-languages.so")


def build_tree_sitter_binary() -> None:
    Language.build_library(
        # Store the library in the `build` directory
        __TREE_SITTER_BINARY__,
        # Include one or more languages
        [
            join(VENDOR_DIR, "tree-sitter-cpp"),
            join(VENDOR_DIR, "tree-sitter-java"),
            join(VENDOR_DIR, "tree-sitter-python"),
        ],
    )


def ensure_tree_sitter_binary() -> str:
    if not exists(__TREE_SITTER_BINARY__):
        print(
            f"Tree-Sitter binary not found at {__TREE_SITTER_BINARY__}. Attempting to build."
        )
        build_tree_sitter_binary()
    return __TREE_SITTER_BINARY__


if __name__ == "__main__":
    build_tree_sitter_binary()
