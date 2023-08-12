# Releasing

If you are a member of the Craft vs Cruft org, you can release Menderbot using git [tags](https://git-scm.com/book/en/v2/Git-Basics-Tagging).

```
export MENDERBOT_VERSION=`./venv/bin/python -c "import menderbot; print(menderbot.__version__)"`
echo $MENDERBOT_VERSION
```

Check that it's not already tagged.
```
git ls-remote --tags origin "$MENDERBOT_VERSION"
```

If so, bump it in `menderbot/__init__.py` and start over.

Tag, starting with "v".

```
git tag "v$MENDERBOT_VERSION"
```

Push the tag to the remote (origin here), and watch the build on GitHub.
```
git push origin "v$MENDERBOT_VERSION"
```
