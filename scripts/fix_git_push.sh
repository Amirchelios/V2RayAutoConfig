#!/bin/bash
# Script to fix Git push issues in GitHub Actions

set -e

echo "🔧 Fixing Git push issues..."

# Get current branch
BRANCH="${GITHUB_REF#refs/heads/}"
if [[ -z "$BRANCH" ]]; then 
    BRANCH="main"
fi

echo "Current branch: $BRANCH"

# Configure git
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

# Check if there are any changes to commit
if git diff --quiet; then
    echo "No changes to commit."
    exit 0
fi

# Add all changes
git add -A

# Commit changes
git commit -m "chore: auto-update configs and README [skip ci]"

# Fetch latest changes from remote
echo "Fetching latest changes from remote..."
git fetch origin "$BRANCH"

# Try different strategies to handle conflicts
echo "Attempting to push changes..."

# Strategy 1: Try rebase
if git pull --rebase origin "$BRANCH"; then
    echo "✅ Rebase successful"
    git push origin HEAD:"$BRANCH"
    echo "✅ Push successful with rebase"
    exit 0
fi

echo "⚠️ Rebase failed, trying merge strategy..."

# Strategy 2: Reset and merge
git reset --soft HEAD~1
git stash
git pull origin "$BRANCH"
git stash pop
git add -A
git commit -m "chore: auto-update configs and README [skip ci]"

# Try push again
if git push origin HEAD:"$BRANCH"; then
    echo "✅ Push successful with merge"
    exit 0
fi

echo "⚠️ Merge strategy failed, trying force push..."

# Strategy 3: Force push (use with caution)
if [[ "$GITHUB_REF" == "refs/heads/main" ]]; then
    echo "❌ Force push not allowed on main branch"
    exit 1
fi

git push --force-with-lease origin HEAD:"$BRANCH"
echo "✅ Force push successful"

echo "🎉 Git push issues resolved!"
