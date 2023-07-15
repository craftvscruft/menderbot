from tree_sitter import Language

if __name__ == "__main__":
    Language.build_library(
        # Store the library in the `build` directory
        "build/my-languages.so",
        # Include one or more languages
        [
            "vendor/tree-sitter-cpp",
            "vendor/tree-sitter-java",
            "vendor/tree-sitter-python",
        ],
    )
