# Releasing

If you are a member of the Craft vs Cruft org, you can release Menderbot using git [tags](https://git-scm.com/book/en/v2/Git-Basics-Tagging).

## Prerelease

```sh
pipx run tbump current-version
MENDERBOT_VERSION=0.0.X-pre
pipx run tbump --only-patch "$MENDERBOT_VERSION"
git commit README.md menderbot/__init__.py tbump.toml -m "Bump to $MENDERBOT_VERSION"
gh auth login
gh release create --prerelease "v${MENDERBOT_VERSION}"
```

## Release

```sh
pipx run tbump current-version
MENDERBOT_VERSION=0.0.X-pre
pipx run tbump --only-patch "$MENDERBOT_VERSION"
git commit README.md menderbot/__init__.py tbump.toml -m "Bump to $MENDERBOT_VERSION"
gh auth login
gh release create --prerelease "v${MENDERBOT_VERSION}"
```

Hit enter a few times, leave a note. Check the workflows for progress. 