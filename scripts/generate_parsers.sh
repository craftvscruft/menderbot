#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

ANTLR_EXE="antlr"
STARTING_DIR=`git rev-parse --show-toplevel`
GEN_DIR="$STARTING_DIR"/menderbot/antlr_generated
TARGET="Python3"

## Util functions

function clean() {
    rm -rf gen/
    rm -f *.g4 *.g4.bak
}

function gen_parser() {
    NAME=$1
    GRAMMAR_DIR=$2
    WORK_DIR=$3
    echo "# Generating $NAME parser"
    echo $WORK_DIR
    cd "$WORK_DIR"
    clean
    cp "$GRAMMAR_DIR"/*.g4 .
    python transformGrammar.py

    echo "Generating $NAME parser with Antlr4 ($TARGET target)"
    $ANTLR_EXE -Dlanguage=$TARGET -o gen *.g4
    cp *Base.py gen/
    echo Moving generated files to $GEN_DIR
    mkdir -p "$GEN_DIR"
    mv gen/* "$GEN_DIR"/

    echo Cleaning up
    clean
}

echo
echo "# Generate parsers"
echo

PYTHON_GRAMMER_DIR="$STARTING_DIR/vendor/grammars-v4/python/python"
gen_parser Python \
    "$PYTHON_GRAMMER_DIR" \
    "$PYTHON_GRAMMER_DIR/Python3"

CPP_GRAMMER_DIR="$STARTING_DIR/vendor/grammars-v4/cpp"
gen_parser CPP14 \
    "$CPP_GRAMMER_DIR" \
    "$CPP_GRAMMER_DIR/Python3"



echo
echo "# Post processing"
echo

# Running isort now because it's easier than consistently stopping it from running.
echo Organizing imports
pipx run isort "$GEN_DIR/"

echo "Attempting to make files Python 3.9 compatible by removing | syntax for Union type"
sed -e "s/: PythonVersion | int//g" -i "$GEN_DIR"/*.py

echo
echo "Victory!"