param(
    [string]$RepoName = $(Split-Path -Leaf (Get-Location)),
    [ValidateSet("public", "private")]
    [string]$Visibility = "public",
    [string]$RemoteUrl = "",
    [switch]$Force
)

function Write-ErrAndExit($msg, $code = 1) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit $code }

# Check git
try { git --version >$null 2>&1 } catch { Write-ErrAndExit "git not found. Install Git for Windows (https://git-scm.com/download/win) and restart terminal." }

# Ensure user.name/email present
$uname = (git config --global user.name) -join ''
$uemail = (git config --global user.email) -join ''
if (-not $uname -or -not $uemail) {
    Write-Host "Global git user.name or user.email not configured. You should set them now (or the commit will still succeed but be anonymous)."
    Write-Host "Run: git config --global user.name \"Your Name\"; git config --global user.email \"you@example.com\""
}

# Check for existing .git
$gitDir = Join-Path (Get-Location) '.git'
if (-not (Test-Path $gitDir)) {
    Write-Host "Initializing git repository..."
    git init
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "git init failed" }
}
else {
    Write-Host ".git already exists — repository initialized." -ForegroundColor Yellow
}

# Add and commit
$hasChanges = (git status --porcelain) -ne ''
if ($hasChanges -or $Force) {
    git add .
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "git add failed" }
    # Create commit if no commits yet
    git rev-parse --verify HEAD > $null 2>&1
    $hasCommits = ($LASTEXITCODE -eq 0)
    if (-not $hasCommits) {
        git commit -m "Initial commit from TheBot.py workspace"
        if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "git commit failed" }
    }
    else {
        git commit -m "Update workspace"
        if ($LASTEXITCODE -ne 0) { Write-Host "Nothing to commit or commit failed." -ForegroundColor Yellow }
    }
}
else {
    Write-Host "No changes to add/commit." -ForegroundColor Yellow
}

# Ensure main branch name
try { git branch -M main } catch { }

# Remote handling
if ($RemoteUrl) {
    Write-Host "Adding remote origin -> $RemoteUrl"
    git remote remove origin 2>$null
    git remote add origin $RemoteUrl
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "git remote add failed" }
    Write-Host "Pushing to remote..."
    git push -u origin main
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "git push failed. Check remote URL and credentials." }
    Write-Host "Pushed to $RemoteUrl" -ForegroundColor Green
    exit 0
}

# If gh is available, try to create repo
$ghAvailable = $false
try { gh --version >$null 2>&1; $ghAvailable = $true } catch { $ghAvailable = $false }

if ($ghAvailable) {
    Write-Host "Creating GitHub repo using gh: $RepoName ($Visibility)"
    # --confirm to avoid interactive prompt, --source to push current directory
    gh repo create $RepoName --$Visibility --source=. --remote=origin --push --confirm 2>&1 | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { Write-ErrAndExit "gh repo create failed (see output above)" }
    Write-Host "Repository created and pushed via gh." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "gh (GitHub CLI) not found. To create a GitHub repo from terminal, install gh: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host "Alternatively, create an empty repo on GitHub and rerun this script with -RemoteUrl 'https://github.com/yourname/yourrepo.git'"
    exit 0
}
