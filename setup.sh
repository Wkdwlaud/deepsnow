#!/bin/bash
# AI Investment Agent - Setup Script
# Creates symlinks from this project into ~/.hermes so Hermes can discover
# the plugin and profiles. Run once after cloning.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"

echo "=== AI Investment Agent Setup ==="
echo "Project: $PROJECT_DIR"
echo "Hermes Home: $HERMES_HOME"
echo ""

# Ensure hermes directories exist
mkdir -p "$HERMES_HOME/plugins"
mkdir -p "$HERMES_HOME/profiles"
mkdir -p "$HERMES_HOME/investment-data"

# Symlink plugin
if [ -L "$HERMES_HOME/plugins/investment-research" ]; then
    rm "$HERMES_HOME/plugins/investment-research"
fi
if [ -d "$HERMES_HOME/plugins/investment-research" ]; then
    echo "WARNING: $HERMES_HOME/plugins/investment-research exists as a directory."
    echo "  Remove it manually and re-run this script."
    exit 1
fi
ln -sf "$PROJECT_DIR/plugin" "$HERMES_HOME/plugins/investment-research"
echo "✓ Plugin linked: $HERMES_HOME/plugins/investment-research -> $PROJECT_DIR/plugin"

# Symlink profiles
for profile_dir in "$PROJECT_DIR/profiles"/*/; do
    profile_name=$(basename "$profile_dir")
    target="$HERMES_HOME/profiles/$profile_name"
    if [ -L "$target" ]; then
        rm "$target"
    fi
    if [ -d "$target" ]; then
        echo "WARNING: $target exists as a directory. Skipping."
        continue
    fi
    ln -sf "$profile_dir" "$target"
    echo "✓ Profile linked: $target -> $profile_dir"
done

# Create report output directory
mkdir -p ~/Documents/investment/reports/tech/{deep,tracking,framework}
echo "✓ Report directory created: ~/Documents/investment/reports/"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy profiles/tech-analyst/.env.example to profiles/tech-analyst/.env"
echo "     and fill in your ANTHROPIC_API_KEY"
echo "  2. Enable the plugin: hermes plugins enable investment-research"
echo "  3. Test: hermes -p tech-analyst chat"
