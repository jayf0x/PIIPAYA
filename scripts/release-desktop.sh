#!/usr/bin/env bash
set -e

TAURI_CONF="piipaya-desktop/src-tauri/tauri.conf.json"
CARGO_TOML="piipaya-desktop/src-tauri/Cargo.toml"

# ── Detect native arch ───────────────────────────────────────────────────────
case "$(uname -m)" in
  arm64)  TARGET="aarch64-apple-darwin" ;;
  x86_64) TARGET="x86_64-apple-darwin" ;;
  *) echo "Unsupported arch: $(uname -m)" && exit 1 ;;
esac

# ── 1. Bump version ──────────────────────────────────────────────────────────
CURRENT=$(node -e "console.log(require('./$TAURI_CONF').version)")
MAJOR=$(echo "$CURRENT" | cut -d. -f1)
MINOR=$(echo "$CURRENT" | cut -d. -f2)
PATCH=$(echo "$CURRENT" | cut -d. -f3)

BUMP="${BUMP:-patch}"
case "$BUMP" in
  major) MAJOR=$((MAJOR+1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR+1)); PATCH=0 ;;
  patch) PATCH=$((PATCH+1)) ;;
  *) echo "Unknown BUMP value: $BUMP (use patch/minor/major)" && exit 1 ;;
esac

NEW="$MAJOR.$MINOR.$PATCH"
TAG="desktop-v$NEW"

echo "→ Bumping $CURRENT → $NEW (target: $TARGET)"

node -e "
  const fs = require('fs');
  const conf = JSON.parse(fs.readFileSync('$TAURI_CONF', 'utf8'));
  conf.version = '$NEW';
  fs.writeFileSync('$TAURI_CONF', JSON.stringify(conf, null, 2) + '\n');
"
sed -i '' "s/^version = \"$CURRENT\"/version = \"$NEW\"/" "$CARGO_TOML"

# ── 2. Build sidecar for native arch ─────────────────────────────────────────
echo "→ Building sidecar..."
(cd piipaya-desktop && bash scripts/build-sidecar.sh)

# ── 3. Build app for native arch ─────────────────────────────────────────────
echo "→ Ensuring Rust target..."
rustup target add "$TARGET"

echo "→ Building app..."
(cd piipaya-desktop && bun run tauri build --target "$TARGET")

# ── 4. Find DMG and copy out of gitignored target/ ───────────────────────────
DMG_SRC=$(find "piipaya-desktop/src-tauri/target/$TARGET/release/bundle/dmg" -name "*.dmg" | head -1)
if [ -z "$DMG_SRC" ]; then
  echo "Error: no .dmg found." && exit 1
fi
DMG="/tmp/PIIPAYA_${NEW}_${TARGET}.dmg"
cp "$DMG_SRC" "$DMG"
echo "→ DMG: $DMG"

# ── 5. Commit, tag, push ─────────────────────────────────────────────────────
git add "$TAURI_CONF" "$CARGO_TOML" "piipaya-desktop/src-tauri/Cargo.lock"
git commit -m "chore(desktop): release v$NEW"
git tag "$TAG"
git push origin HEAD
git push origin "$TAG"

# ── 6. Create GitHub release and upload DMG ──────────────────────────────────
echo "→ Creating GitHub release $TAG..."
gh release create "$TAG" "$DMG" \
  --title "PIIPAYA Desktop v$NEW" \
  --notes "## PIIPAYA Desktop v$NEW

### Install
Download the \`.dmg\` below and drag PIIPAYA to your Applications folder.

> Built on $(uname -m) macOS $(sw_vers -productVersion).

### What's new
See [commits](../../commits/$TAG) for full changelog."

echo "✓ Released $TAG → $(gh release view "$TAG" --json url -q .url)"
