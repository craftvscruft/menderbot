### Re-generating the parsers

The generated parsers are commited to the main repo, so you will only this step if you need to update them. The grammars are in [git submodules](https://git-scm.com/book/en/v2/Git-Tools-Submodules) so you can bring them in with:

```
git submodule init
```

You should now have many Antlr grammars in `vendor/grammars-v4`, we will use just a few. Build the parsers with this script:

```
./scripts/generate_parsers.sh
```

