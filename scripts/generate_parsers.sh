#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

ANTLR_EXE="antlr"
# ANTLR_EXE="antlr4"
STARTING_DIR=`git rev-parse --show-toplevel`
GEN_DIR="$STARTING_DIR"/menderbot/antlr_generated
WORK_DIR="$STARTING_DIR"/vendor/grammars-v4/python/python/Python3
echo $WORK_DIR
cd $WORK_DIR
cp ../PythonLexer.g4 ../PythonParser.g4 .
python transformGrammar.py

rm -rf gen/
echo "Generating Universal Python parser with Antlr4 (Python3 target)"
$ANTLR_EXE -Dlanguage=Python3 -o gen *.g4
cp PythonLexerBase.py  PythonParserBase.py gen/

echo "Attempting to make files Python 3.9 compatible by removing | syntax for Union type"
sed -e "s/: PythonVersion | int//g" -i gen/*.py
echo Moving generated files to $GEN_DIR
mv gen/* $GEN_DIR/

# Running isort now because it's easier than consistently stopping it from running.
echo Organizing imports
pipx run isort $GEN_DIR/

echo Cleaning up
rmdir gen/
#replace 3.10 | syntax with typing.Union