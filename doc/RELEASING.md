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

Create the prerelease.
```
gh auth login
gh release create --prerelease "v${MENDERBOT_VERSION}-pre"
```

Hit enter a few times, leave a note. Check the workflows for progress. When ready to release for real:
```
gh release create "v$MENDERBOT_VERSION"
```
