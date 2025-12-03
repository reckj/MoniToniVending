#!/bin/bash
# Setup script for GitHub repository

echo "MoniToni Vending Machine System - GitHub Setup"
echo "=============================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed."
    echo "Please install it first: https://cli.github.com/"
    echo ""
    echo "Or create the repository manually at:"
    echo "https://github.com/new"
    echo ""
    echo "Then run:"
    echo "  git remote add origin https://github.com/reckj/MoniToniVending.git"
    echo "  git push -u origin main"
    exit 1
fi

# Create GitHub repository
echo "Creating GitHub repository 'MoniToniVending'..."
gh repo create MoniToniVending --public --source=. --remote=origin --description="Production-ready vending machine control system for Raspberry Pi 5"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Repository created successfully!"
    echo ""
    echo "Pushing code to GitHub..."
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Code pushed successfully!"
        echo ""
        echo "Repository URL: https://github.com/reckj/MoniToniVending"
        echo ""
    else
        echo "❌ Failed to push code"
        exit 1
    fi
else
    echo "❌ Failed to create repository"
    echo ""
    echo "You can create it manually at: https://github.com/new"
    echo "Repository name: MoniToniVending"
    echo "Then run: git remote add origin https://github.com/reckj/MoniToniVending.git"
    echo "         git push -u origin main"
    exit 1
fi
