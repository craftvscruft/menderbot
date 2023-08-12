#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

STARTING_DIR=`git rev-parse --show-toplevel`
cd "$STARTING_DIR"

echo "# Python"
# Has one-line functions
menderbot plumbing functions vendor/grammars-v4/python/python/examples/funcdef.py

menderbot plumbing functions vendor/grammars-v4/python/python/examples/class_or_func_def_stmt.py

echo "# Cpp"

# Currently empty because there's no body
menderbot plumbing functions vendor/grammars-v4/cpp/examples/function_definitions_and_integers.cpp

menderbot plumbing functions vendor/grammars-v4/cpp/examples/avrc_api.cc