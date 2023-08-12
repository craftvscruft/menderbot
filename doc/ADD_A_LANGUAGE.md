# Add a new language

See this [GitHub issue](https://github.com/craftvscruft/menderbot/issues/5) for the current status of language support.

## Generate parser

Update `scripts/generate_parsers.sh` in the "Generate parsers" section to add your new language. It's expecting directories similar to `vendor/grammars-v4`.

```sh
PYTHON_GRAMMAR_DIR="$STARTING_DIR/vendor/grammars-v4/python/python"
gen_parser Python \
    # Grammar dir
    "$PYTHON_GRAMMAR_DIR" \
    # Work dir:
    "$PYTHON_GRAMMAR_DIR/Python3"
```

* One or more .g4 grammar files in the grammar directory
* A `transformGrammar.py` script in the work directory
* A `*Base.py` files in the work directory

If successful, it will create new parser code in `menderbot/antlr_generated` with the others.

## Implement a LanguageStrategy

Start in `menderbot/code.py`. This pattern is rapidly changing, more coming here when it settles down. 

Please [reach out](https://github.com/craftvscruft/menderbot/issues/5) if you are interested in adding a target language.

## Test the plumbing

Add an example to `scripts/smoke.sh` and run it.