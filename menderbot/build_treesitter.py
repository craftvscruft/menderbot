from os.path import abspath, dirname, exists, join, pardir

from setuptools.command.build_py import build_py  # type: ignore[import]
from tree_sitter import Language

ABS_DIRNAME = dirname(abspath(__file__))
BUILD_DIR = abspath(join(ABS_DIRNAME, "ext"))
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


def tree_sitter_binary_exists() -> bool:
    return exists(__TREE_SITTER_BINARY__)


class BuildPy(build_py):
    """Used in setuptools cmdclass"""

    def run(self):
        build_tree_sitter_binary()
        super().run()


try:
    from wheel.bdist_wheel import bdist_wheel  # type: ignore[import]

    class BdistWheel(bdist_wheel):
        def finalize_options(self):
            super().finalize_options()
            # Mark us as not a pure python package
            # pylint: disable-next=attribute-defined-outside-init
            self.root_is_pure = False

        # def get_tag(self):
        #     python, abi, plat = bdist_wheel.get_tag(self)
        #     # We don't contain any python source, nor any python extensions
        #     python, abi = 'py2.py3', 'none'
        #     return python, abi, plat

except ImportError:
    BdistWheel = None  # type: ignore


if __name__ == "__main__":
    build_tree_sitter_binary()
