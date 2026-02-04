#!/bin/bash

# Memory Scope - GitHub Repository Setup Script
# This script helps you safely push your code to GitHub

set -e

REPO_URL="https://github.com/jonmooreai/memoryscope.git"

echo "🔐 GitHub Repository Setup"
echo "=========================="
echo ""

# Check if .env files exist and warn
if [ -f .env ] || [ -f website/.env.local ]; then
    echo "⚠️  WARNING: .env files detected!"
    echo "   These will be excluded by .gitignore, but double-check before pushing."
    echo ""
fi

# Check if git is initialized
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    git branch -M main
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository already exists"
fi

# Check remote
if git remote get-url origin &>/dev/null; then
    CURRENT_REMOTE=$(git remote get-url origin)
    if [ "$CURRENT_REMOTE" != "$REPO_URL" ]; then
        echo "🔄 Updating remote URL..."
        git remote set-url origin "$REPO_URL"
    else
        echo "✅ Remote already configured: $REPO_URL"
    fi
else
    echo "🔗 Adding remote repository..."
    git remote add origin "$REPO_URL"
    echo "✅ Remote added: $REPO_URL"
fi

# Verify .gitignore
echo ""
echo "🔍 Verifying .gitignore..."
if git check-ignore .env website/.env.local &>/dev/null; then
    echo "✅ .env files are properly ignored"
else
    echo "⚠️  WARNING: .env files may not be ignored. Check .gitignore"
fi

# Show what will be committed
echo ""
echo "📋 Files that will be committed:"
echo "--------------------------------"
git status --short | head -20
if [ $(git status --short | wc -l) -gt 20 ]; then
    echo "... and more files"
fi

echo ""
echo "❌ Files that will be EXCLUDED (good!):"
echo "---------------------------------------"
git status --ignored --short | head -10

echo ""
read -p "Continue with commit and push? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Cancelled. No changes made."
    exit 0
fi

# Remove embedded git repository in website if it exists
if [ -d website/.git ]; then
    echo "🔧 Removing embedded git repository in website/..."
    rm -rf website/.git
    echo "✅ Removed website/.git"
fi

# Stage files
echo ""
echo "📦 Staging files..."
git add .

# Check for any .env files that might have been added
STAGED_FILES=$(git diff --cached --name-only 2>/dev/null || echo "")
if [ -n "$STAGED_FILES" ]; then
    ENV_FILES=$(echo "$STAGED_FILES" | grep -E "\.env$|\.env\.|\.env\.bak" | grep -v "env.example" || true)
    if [ -n "$ENV_FILES" ]; then
        echo "⚠️  WARNING: .env files detected in staged files!"
        echo "   Unstaging them..."
        # Use git reset without HEAD for first commit
        if git rev-parse --verify HEAD >/dev/null 2>&1; then
            git reset HEAD $ENV_FILES
        else
            git reset $ENV_FILES
        fi
        echo "✅ Unstaged .env files"
    fi
fi

# Commit
echo ""
echo "💾 Creating commit..."
git commit -m "Initial commit: Memory Scope API and website

- FastAPI backend with policy enforcement and memory management
- Next.js website with Firebase authentication
- Database migrations and schema
- Deployment scripts and configuration
- Comprehensive documentation
- All sensitive files excluded via .gitignore"

# Push
echo ""
echo "🚀 Pushing to GitHub..."
echo ""
echo "⚠️  IMPORTANT: Make sure your GitHub repo is set to PRIVATE!"
echo "   Go to: https://github.com/jonmooreai/memoryscope/settings"
echo ""
read -p "Press Enter to continue with push, or Ctrl+C to cancel..."

git push -u origin main

echo ""
echo "✅ Successfully pushed to GitHub!"
echo ""
echo "📝 Next steps:"
echo "   1. Go to https://github.com/jonmooreai/memoryscope/settings"
echo "   2. Scroll down to 'Danger Zone'"
echo "   3. Click 'Change visibility' → 'Make private'"
echo "   4. Deploy backend to Railway/Render/Cloud Run"
echo "   5. Configure DNS"
echo "   6. Deploy frontend to Firebase"
echo ""
echo "📚 See GITHUB_SETUP.md for detailed instructions"

