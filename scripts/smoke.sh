#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

STARTING_DIR=`git rev-parse --show-toplevel`
cd "$STARTING_DIR"

# Has one-line functions
menderbot plumbing functions vendor/grammars-v4/python/python/examples/funcdef.py

menderbot plumbing functions vendor/grammars-v4/python/python/examples/class_or_func_def_stmt.py