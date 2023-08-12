# Releasing

If you are a member of the Craft vs Cruft org, you can release Menderbot using git [tags](https://git-scm.com/book/en/v2/Git-Basics-Tagging).

## Release

```sh
pipx run tbump current-version
export MENDERBOT_VERSION=0.0.X
pipx run tbump --only-patch "$MENDERBOT_VERSION"
git commit README.md menderbot/__init__.py tbump.toml -m "Bump to $MENDERBOT_VERSION"
git push
gh auth login
gh release create "v${MENDERBOT_VERSION}" --notes ""
```

Hit enter a few times, leave a note. Check the workflows for progress. 

## Prerelease (Optional)

```sh
pipx run tbump current-version
export MENDERBOT_VERSION=0.0.X-pre
pipx run tbump --only-patch "$MENDERBOT_VERSION"
git commit README.md menderbot/__init__.py tbump.toml -m "Bump to $MENDERBOT_VERSION"
git push
gh auth login
gh release create --prerelease "v${MENDERBOT_VERSION}" --notes ""
```