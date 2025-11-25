# Helper script: create GitHub repo and push current folder
# Requires: Git and GitHub CLI (`gh`) installed and authenticated

param(
    [string]$repoName = "TheBot.py",
    [string]$visibility = "public"
)

Write-Host "Initializing git repository (if not initialized)..."
if (-not (Test-Path .git)) {
    git init
}

git add .
git commit -m "Initial commit"

Write-Host "Creating repo on GitHub via gh..."
gh repo create $repoName --$visibility --source=. --remote=origin --push
Write-Host "Done. Repository created and pushed."
