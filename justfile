# cuti development automation

# Increment patch version (bugfix), build, publish, and update local tool
publish:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "⚠️  Uncommitted changes detected!"
        git status --short
        echo ""
        read -p "Do you want to continue with publishing? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Publishing cancelled"
            exit 1
        fi
    else
        echo "✅ No uncommitted changes"
    fi
    
    echo "🔢 Incrementing patch version..."
    # Read current version
    current_version=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "Current version: $current_version"
    
    # Split version into parts
    IFS='.' read -r major minor patch <<< "$current_version"
    
    # Increment patch version
    new_patch=$((patch + 1))
    new_version="$major.$minor.$new_patch"
    
    echo "New version: $new_version"
    
    # Update pyproject.toml
    sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    
    echo "✅ Updated pyproject.toml to version $new_version"
    
    echo "🔄 Running uv sync..."
    uv sync
    
    echo "🧹 Cleaning old build artifacts..."
    rm -rf dist/
    
    echo "🏗️  Building package..."
    uv build
    
    echo "📦 Publishing to PyPI..."
    uv publish
    
    echo "🔧 Updating local tool installation..."
    # Loop until the tool is updated with the new version
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt: Updating cuti tool..."
        
        # Update the tool (will install if not present)
        uv tool update cuti
        
        # Check if the installed version matches the new version
        installed_version=$(uv tool run cuti version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
        
        if [ "$installed_version" = "$new_version" ]; then
            echo "✅ Tool successfully updated to version $new_version"
            break
        else
            echo "⏳ Tool version is $installed_version, waiting for PyPI propagation... (attempt $attempt/$max_attempts)"
            sleep 10
        fi
        
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "❌ Failed to update tool after $max_attempts attempts"
        echo "The package was published but tool installation timed out"
        echo "Try running 'uv tool install cuti' manually in a few minutes"
        exit 1
    fi
    
    echo "🎉 Successfully published and installed cuti version $new_version"

# Increment minor version (feature release), build, publish, and update local tool
publish-minor:
    #!/usr/bin/env bash
    set -euo pipefail
    
    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo "⚠️  Uncommitted changes detected!"
        git status --short
        echo ""
        read -p "Do you want to continue with publishing? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "❌ Publishing cancelled"
            exit 1
        fi
    else
        echo "✅ No uncommitted changes"
    fi
    
    echo "🔢 Incrementing minor version..."
    # Read current version
    current_version=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "Current version: $current_version"
    
    # Split version into parts
    IFS='.' read -r major minor patch <<< "$current_version"
    
    # Increment minor version, reset patch to 0
    new_minor=$((minor + 1))
    new_version="$major.$new_minor.0"
    
    echo "New version: $new_version"
    
    # Update pyproject.toml
    sed -i '' "s/^version = \".*\"/version = \"$new_version\"/" pyproject.toml
    
    echo "✅ Updated pyproject.toml to version $new_version"
    
    echo "🔄 Running uv sync..."
    uv sync
    
    echo "🧹 Cleaning old build artifacts..."
    rm -rf dist/
    
    echo "🏗️  Building package..."
    uv build
    
    echo "📦 Publishing to PyPI..."
    uv publish
    
    echo "🔧 Updating local tool installation..."
    # Loop until the tool is updated with the new version
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt: Updating cuti tool..."
        
        # Update the tool (will install if not present)
        uv tool update cuti
        
        # Check if the installed version matches the new version
        installed_version=$(uv tool run cuti version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
        
        if [ "$installed_version" = "$new_version" ]; then
            echo "✅ Tool successfully updated to version $new_version"
            break
        else
            echo "⏳ Tool version is $installed_version, waiting for PyPI propagation... (attempt $attempt/$max_attempts)"
            sleep 10
        fi
        
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "❌ Failed to update tool after $max_attempts attempts"
        echo "The package was published but tool installation timed out"
        echo "Try running 'uv tool install cuti' manually in a few minutes"
        exit 1
    fi
    
    echo "🎉 Successfully published and installed cuti version $new_version"

# Just build without publishing
build:
    echo "🏗️  Building package..."
    uv build

# Install development version locally (editable install in current environment)
install-dev:
    echo "🔧 Installing development version..."
    uv pip install -e . --force-reinstall

# Build and install cuti as a global tool from current development code (overrides PyPI version)
dev:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🔨 Building and installing cuti from current development code..."
    echo ""
    
    # Get current version from pyproject.toml
    current_version=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "📌 Development version: $current_version"
    
    # Clean any existing builds
    echo "🧹 Cleaning old build artifacts..."
    rm -rf dist/ build/ *.egg-info/
    
    # Build the package
    echo "🏗️  Building package from current code..."
    uv build
    
    # Check if build was successful
    if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
        echo "❌ Build failed - no dist directory or files created"
        exit 1
    fi
    
    # Uninstall existing cuti tool if present
    if uv tool list | grep -q "^cuti "; then
        echo "🗑️  Removing existing cuti tool installation..."
        uv tool uninstall cuti
    fi
    
    # Install from the local wheel file
    echo "📦 Installing cuti tool from local build..."
    wheel_file=$(ls dist/*.whl | head -n1)
    
    if [ -z "$wheel_file" ]; then
        echo "❌ No wheel file found in dist/"
        exit 1
    fi
    
    echo "   Installing from: $wheel_file"
    uv tool install "$wheel_file" --force
    
    # Verify installation
    echo ""
    echo "✅ Verifying installation..."
    
    # Check if cuti is available
    if ! command -v cuti >/dev/null 2>&1; then
        echo "⚠️  cuti command not found in PATH"
        echo "   You may need to add ~/.local/bin to your PATH"
        echo "   Run: export PATH=\"\$HOME/.local/bin:\$PATH\""
    else
        installed_version=$(cuti --version 2>/dev/null | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
        echo "📍 Installed cuti version: $installed_version"
        echo "📍 Expected version: $current_version"
        
        if [ "$installed_version" = "$current_version" ]; then
            echo "✅ Successfully installed development version!"
        else
            echo "⚠️  Version mismatch - installation may have issues"
        fi
    fi
    
    # Show where it's installed
    echo ""
    echo "📂 Installation details:"
    uv tool list | grep -A 2 "^cuti " || echo "Could not get installation details"
    
    echo ""
    echo "🎉 Development installation complete!"
    echo "   Run 'cuti' to test your changes"

# Switch back to production version from PyPI
prod:
    echo "📦 Switching to production version from PyPI..."
    uv tool uninstall cuti || true
    uv tool install cuti
    echo "✅ Done! Using $(cuti --version 2>/dev/null || echo 'cuti')"

# Build, install as tool, and run web interface for testing
dev-test-web:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Building, installing, and running cuti web interface..."
    
    # First install the development version
    just dev
    
    echo ""
    echo "🌐 Starting web interface..."
    echo "   Access at: http://localhost:8000"
    echo ""
    
    # Run the web interface
    cuti web

# Build, install as tool, and run CLI for testing  
dev-test-cli:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Building, installing, and running cuti CLI..."
    
    # First install the development version
    just dev
    
    echo ""
    echo "💻 Starting CLI interface..."
    echo ""
    
    # Run the CLI
    cuti cli

# Show current version
version:
    #!/usr/bin/env bash
    current_version=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
    echo "pyproject.toml version: $current_version"
    
    if command -v cuti >/dev/null 2>&1; then
        echo "Installed cuti version: $(cuti version)"
    else
        echo "cuti not found in PATH"
    fi
    
    if uv tool list | grep -q cuti; then
        echo "Tool cuti version: $(uv tool run cuti version 2>/dev/null || echo 'failed to get version')"
    else
        echo "cuti tool not installed"
    fi

# Clean build artifacts
clean:
    echo "🧹 Cleaning build artifacts..."
    rm -rf dist/
    rm -rf build/
    rm -rf *.egg-info/

# Build website (validate and prepare for deployment)
website-build:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🌐 Building website..."
    
    # Check if website directory exists
    if [ ! -d "website" ]; then
        echo "❌ website directory not found"
        exit 1
    fi
    
    # Validate all required files exist
    required_files=("index.html" "docs.html" "styles.css" "script.js" "docs.js" "favicon.svg")
    for file in "${required_files[@]}"; do
        if [ ! -f "website/$file" ]; then
            echo "❌ Missing required file: website/$file"
            exit 1
        fi
    done
    
    echo "✅ All required files present"
    
    # Check if markdown docs exist
    if [ ! -d "docs" ]; then
        echo "⚠️  Warning: docs directory not found"
    else
        doc_count=$(find docs -name "*.md" | wc -l | tr -d ' ')
        echo "📚 Found $doc_count documentation files"
    fi
    
    # Validate HTML (basic check)
    echo "🔍 Validating HTML structure..."
    if ! head -n 1 website/index.html | grep -qi "<!DOCTYPE"; then
        echo "⚠️  Warning: index.html missing DOCTYPE"
    fi
    if ! head -n 1 website/docs.html | grep -qi "<!DOCTYPE"; then
        echo "⚠️  Warning: docs.html missing DOCTYPE"
    fi
    
    echo "✅ Website build validation complete!"
    echo ""
    echo "📝 To test locally, run:"
    echo "   just website-serve"
    echo ""
    echo "🚀 To deploy, run:"
    echo "   just website-deploy-github  # For GitHub Pages"
    echo "   just website-deploy          # Interactive deployment"

# Serve website locally for testing
website-serve:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Starting local website server..."
    echo ""
    cd website
    exec python3 serve.py

# Deploy website (interactive - choose platform)
website-deploy:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "🚀 Website Deployment"
    echo "===================="
    echo ""
    echo "Choose deployment target:"
    echo "  1) GitHub Pages (gh-pages branch)"
    echo "  2) Manual (instructions only)"
    echo ""
    read -p "Enter choice (1-2): " choice
    echo ""
    
    case $choice in
        1)
            just website-deploy-github
            ;;
        2)
            just website-deploy-manual
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac

# Deploy to GitHub Pages (gh-pages branch)
website-deploy-github:
    #!/usr/bin/env bash
    set -euo pipefail
    
    echo "📦 Deploying to GitHub Pages..."
    echo ""
    
    # Check if git repo
    if [ ! -d ".git" ]; then
        echo "❌ Not a git repository"
        exit 1
    fi
    
    # Check for uncommitted changes in website/
    if git status --porcelain website/ | grep -q '^'; then
        echo "⚠️  Uncommitted changes in website/ directory:"
        git status --short website/
        echo ""
        read -p "Do you want to commit these changes first? (y/N) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git add website/
            read -p "Enter commit message: " commit_msg
            git commit -m "$commit_msg"
            echo "✅ Changes committed"
        else
            echo "⚠️  Proceeding with uncommitted changes"
        fi
    fi
    
    # Build first
    just website-build
    
    echo ""
    echo "📤 Pushing to gh-pages branch..."
    
    # Check if gh-pages branch exists
    if git rev-parse --verify gh-pages >/dev/null 2>&1; then
        echo "✅ gh-pages branch exists"
    else
        echo "📝 Creating gh-pages branch..."
        git checkout -b gh-pages
        git checkout -
    fi
    
    # Use git subtree to push website folder to gh-pages
    echo "🔄 Deploying website folder to gh-pages branch..."
    git subtree push --prefix website origin gh-pages
    
    echo ""
    echo "✅ Website deployed to GitHub Pages!"
    echo ""
    echo "📍 Your site will be available at:"
    echo "   https://$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | sed 's/.*github.com[:/]\(.*\)/\1/').github.io/$(basename $(git rev-parse --show-toplevel))/"
    echo ""
    echo "⏳ Note: It may take a few minutes for changes to appear"
    echo ""
    echo "🔧 Enable GitHub Pages in your repo settings:"
    echo "   Settings → Pages → Source: gh-pages branch → / (root)"

# Show manual deployment instructions
website-deploy-manual:
    #!/usr/bin/env bash
    echo "📖 Manual Deployment Instructions"
    echo "================================="
    echo ""
    echo "Your static website is ready in the 'website/' folder."
    echo ""
    echo "🌐 Deployment Options:"
    echo ""
    echo "1️⃣  Netlify:"
    echo "   • Drag and drop 'website/' folder to Netlify"
    echo "   • Or connect your Git repo and set build directory to 'website'"
    echo "   • netlify.com"
    echo ""
    echo "2️⃣  Vercel:"
    echo "   • Import your repo"
    echo "   • Set output directory to 'website'"
    echo "   • vercel.com"
    echo ""
    echo "3️⃣  GitHub Pages (manual):"
    echo "   • Run: just website-deploy-github"
    echo ""
    echo "4️⃣  Cloudflare Pages:"
    echo "   • Connect Git repo"
    echo "   • Build directory: website"
    echo "   • pages.cloudflare.com"
    echo ""
    echo "5️⃣  AWS S3 + CloudFront:"
    echo "   • Upload website/ contents to S3 bucket"
    echo "   • Configure bucket for static hosting"
    echo "   • Add CloudFront CDN (optional)"
    echo ""
    echo "6️⃣  Firebase Hosting:"
    echo "   • firebase init hosting"
    echo "   • Set public directory to 'website'"
    echo "   • firebase deploy"
    echo ""
    echo "📝 The website folder contains all necessary files:"
    ls -1 website/
    echo ""
    echo "✅ No build step required - deploy directly!"

# Help
help:
    just --list