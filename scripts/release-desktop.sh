#!/usr/bin/env bash
set -e

TAURI_CONF="piipaya-desktop/src-tauri/tauri.conf.json"
CARGO_TOML="piipaya-desktop/src-tauri/Cargo.toml"

# Get current version from tauri.conf.json
CURRENT=$(node -e "console.log(require('./$TAURI_CONF').version)")

# Parse semver
MAJOR=$(echo "$CURRENT" | cut -d. -f1)
MINOR=$(echo "$CURRENT" | cut -d. -f2)
PATCH=$(echo "$CURRENT" | cut -d. -f3)

# Allow override: BUMP=minor or BUMP=major
BUMP="${BUMP:-patch}"
case "$BUMP" in
  major) MAJOR=$((MAJOR+1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR+1)); PATCH=0 ;;
  patch) PATCH=$((PATCH+1)) ;;
  *) echo "Unknown BUMP value: $BUMP (use patch/minor/major)"; exit 1 ;;
esac

NEW="$MAJOR.$MINOR.$PATCH"
TAG="desktop-v$NEW"

echo "Bumping $CURRENT → $NEW (tag: $TAG)"

# Update tauri.conf.json
node -e "
  const fs = require('fs');
  const conf = JSON.parse(fs.readFileSync('$TAURI_CONF', 'utf8'));
  conf.version = '$NEW';
  fs.writeFileSync('$TAURI_CONF', JSON.stringify(conf, null, 2) + '\n');
"

# Update Cargo.toml
sed -i '' "s/^version = \"$CURRENT\"/version = \"$NEW\"/" "$CARGO_TOML"

# Commit, tag, push
git add "$TAURI_CONF" "$CARGO_TOML"
git commit -m "chore(desktop): release v$NEW"
git tag "$TAG"
git push origin HEAD
git push origin "$TAG"

echo "Released $TAG — GitHub Actions will build the DMG."
