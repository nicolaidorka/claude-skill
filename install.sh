#!/bin/bash

echo "=========================================="
echo "Unistream Claude Code Skills Installer"
echo "=========================================="
echo ""

# Check if Claude skills directory exists
if [ ! -d "$HOME/.claude/skills" ]; then
    echo "Creating Claude skills directory..."
    mkdir -p "$HOME/.claude/skills"
    echo "✓ Directory created: $HOME/.claude/skills"
else
    echo "✓ Claude skills directory exists"
fi

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install code validator
if [ -d "$SCRIPT_DIR/unistream-code-validator" ]; then
    echo ""
    echo "Installing unistream-code-validator..."

    # Remove existing if present
    rm -rf "$HOME/.claude/skills/unistream-code-validator"

    # Copy to Claude skills directory
    cp -r "$SCRIPT_DIR/unistream-code-validator" "$HOME/.claude/skills/"

    echo "✓ Code validator installed"
else
    echo "✗ Error: unistream-code-validator directory not found"
    exit 1
fi

# Install architecture analyzer
if [ -d "$SCRIPT_DIR/unistream-architecture-analyzer" ]; then
    echo ""
    echo "Installing unistream-architecture-analyzer..."

    # Remove existing if present
    rm -rf "$HOME/.claude/skills/unistream-architecture-analyzer"

    # Copy to Claude skills directory
    cp -r "$SCRIPT_DIR/unistream-architecture-analyzer" "$HOME/.claude/skills/"

    echo "✓ Architecture analyzer installed"
else
    echo "✗ Error: unistream-architecture-analyzer directory not found"
    exit 1
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Skills installed to: $HOME/.claude/skills/"
echo ""
echo "You can now use these skills with Claude Code."
echo ""
echo "Verify installation:"
echo "  ls -la ~/.claude/skills/"
echo ""
echo "Test the skills:"
echo "  python ~/.claude/skills/unistream-code-validator/validate_code.py --help"
echo "  python ~/.claude/skills/unistream-architecture-analyzer/analyze_architecture.py --help"
echo ""
