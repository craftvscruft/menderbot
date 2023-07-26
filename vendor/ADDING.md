# Adding more languages

Add more tree-sitter grammars as git submodules.

```
git submodule add https://github.com/tree-sitter/tree-sitter-cpp.git vendor/tree-sitter-cpp
```

Update `menderbot/build_treesitter.py` and `menderbot/code.py`.