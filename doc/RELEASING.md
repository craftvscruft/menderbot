# Releasing

If you are a member of the Craft vs Cruft org, you can release Menderbot using git [tags](https://git-scm.com/book/en/v2/Git-Basics-Tagging).

```sh
. ./scripts/version.sh
```

Commit everthing. Do a dry run of the version bump.

```sh
./venv/bin/bumpversion --current-version $MENDERBOT_VERSION patch --dry-run --verbose
```

Version bump:

```sh
./venv/bin/bumpversion --current-version $MENDERBOT_VERSION patch
```

```sh
gh auth login

# For a prerelease:
gh release create --prerelease "v${MENDERBOT_VERSION}"

# For a real release:
gh release create "v$MENDERBOT_VERSION"
```

Hit enter a few times, leave a note. Check the workflows for progress. 