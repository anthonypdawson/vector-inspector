# Vector Inspector: Packaging & Distribution Strategy

**Created:** April 27, 2026

---

## Executive Summary

The installation PR (progressive enhancement) removes the packaging blocker. Without torch, umap, hdbscan bundled, you can now create reasonable-sized binaries (~150-200MB vs 1-2GB).

**Path:** Briefcase → Multi-platform binaries → Homebrew → Distribution parity with VectorDBZ

---

## Why Packaging Is Now Viable

### Before PR (Blocker)
```
Core + torch (700MB) + umap (100MB) + hdbscan + scikit-learn + ... 
= 1-2GB packaged binary
```
- Too large for GitHub releases
- Too large for Homebrew
- Users bounce on download size

### After PR (Solved)
```
Core + Qt + requests + pip = ~150-200MB packaged binary
```
- Reasonable for all distribution channels
- Providers install on-demand through UI
- Updates are smaller (core only)

---

## Briefcase Packaging Guide

### Why Briefcase?
- You've had success with it before
- Native app bundles (.app, .exe, .deb, .rpm)
- Good PySide6/Qt integration
- Cross-platform from single config
- Proper app structure (user dirs, entitlements)

### Initial Setup

**1. Install briefcase:**
```bash
pip install briefcase
```

**2. Add to pyproject.toml:**
```toml
[tool.briefcase]
project_name = "Vector Inspector"
bundle = "com.divinedevops"
version = "0.8.0"
url = "https://vector-inspector.divinedevops.com"
license = "MIT"
author = "Anthony Dawson"
author_email = "anthony@divinedevops.com"

[tool.briefcase.app.vector-inspector]
formal_name = "Vector Inspector"
description = "RAG Engineering Workbench - Debug, compare, and migrate vector databases"
long_description = """Vector Inspector is a comprehensive desktop tool for RAG engineers. 
Debug retrieval failures, compare databases and embeddings, migrate between providers, 
and visualize your embedding space."""

sources = ["src/vector_inspector"]
icon = "resources/icon"  # Will need icon.png, icon.icns, icon.ico
splash = "resources/splash"

# CRITICAL: Bundle pip for in-app provider installs
requires = [
    "PySide6>=6.4.0",
    "requests>=2.28.0",
    "pip>=23.0",
    "setuptools>=65.0",
]

# macOS-specific
[tool.briefcase.app.vector-inspector.macOS]
requires = [
    "PySide6>=6.4.0",
    "requests>=2.28.0",
    "pip>=23.0",
    "setuptools>=65.0",
]

# Network access for provider downloads
entitlements."com.apple.security.network.client" = true
# File access for connections, imports, exports
entitlements."com.apple.security.files.user-selected.read-write" = true

# Windows-specific
[tool.briefcase.app.vector-inspector.windows]
requires = [
    "PySide6>=6.4.0",
    "requests>=2.28.0",
    "pip>=23.0",
    "setuptools>=65.0",
]

# Linux-specific
[tool.briefcase.app.vector-inspector.linux]
requires = [
    "PySide6>=6.4.0",
    "requests>=2.28.0",
    "pip>=23.0",
    "setuptools>=65.0",
]
system_requires = [
    "libgl1-mesa-glx",  # For Qt OpenGL
    "libxkbcommon-x11-0",  # For Qt keyboard
]
```

**3. Create/Build/Run:**
```bash
# Create the scaffold
briefcase create

# Build the app
briefcase build

# Run locally (still in dev mode)
briefcase run

# Package for distribution
briefcase package
```

---

## Fixing In-App Provider Installation

### The Challenge

When packaged, your app's Python is isolated from system Python. Standard `pip install` may not work or install to wrong location.

### Solution: Install to User Directory

**Update `src/vector_inspector/services/install_service.py`:**

```python
import sys
import subprocess
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def is_packaged_app() -> bool:
    """Detect if running as packaged application"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_provider_install_location() -> Path:
    """
    Get directory for provider packages.
    
    - Packaged app: ~/.vector-inspector/site-packages
    - Development: uses normal site-packages
    """
    if is_packaged_app():
        app_dir = Path.home() / '.vector-inspector' / 'site-packages'
        app_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure it's on Python path
        if str(app_dir) not in sys.path:
            sys.path.insert(0, str(app_dir))
        
        logger.info(f"Provider install location: {app_dir}")
        return app_dir
    else:
        # Development: use normal installation
        return None


def get_install_command(package_spec: str) -> list[str]:
    """
    Build pip install command appropriate for environment.
    
    Args:
        package_spec: Package to install, e.g. "vector-inspector[chroma]"
    
    Returns:
        Command list for subprocess.run()
    """
    cmd = [sys.executable, '-m', 'pip', 'install', '--upgrade']
    
    # If packaged, install to user directory
    install_dir = get_provider_install_location()
    if install_dir:
        cmd.extend(['--target', str(install_dir)])
    
    cmd.append(package_spec)
    return cmd


def install(package_spec: str) -> subprocess.CompletedProcess:
    """
    Install a package (provider or feature group).
    
    Works in both development and packaged environments.
    
    Args:
        package_spec: Package to install, e.g. "vector-inspector[chroma]"
    
    Returns:
        CompletedProcess with stdout/stderr
    
    Example:
        result = install("vector-inspector[chroma]")
        if result.returncode == 0:
            print("Installed successfully")
    """
    cmd = get_install_command(package_spec)
    logger.info(f"Installing: {' '.join(cmd)}")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        logger.error(f"Install failed: {result.stderr}")
    else:
        logger.info(f"Install succeeded: {package_spec}")
    
    return result


def uninstall(package_name: str) -> subprocess.CompletedProcess:
    """
    Uninstall a package.
    
    Note: For packaged apps, this removes from ~/.vector-inspector/site-packages
    
    Args:
        package_name: Package name (not spec), e.g. "chromadb"
    
    Returns:
        CompletedProcess with stdout/stderr
    """
    # For packaged apps, pip uninstall won't find packages in --target dir
    # We need to manually remove them
    if is_packaged_app():
        install_dir = get_provider_install_location()
        package_dir = install_dir / package_name
        
        if package_dir.exists():
            import shutil
            shutil.rmtree(package_dir)
            logger.info(f"Removed {package_dir}")
            return subprocess.CompletedProcess(
                args=['manual-remove'],
                returncode=0,
                stdout=f"Removed {package_name}",
                stderr="",
            )
        else:
            return subprocess.CompletedProcess(
                args=['manual-remove'],
                returncode=1,
                stdout="",
                stderr=f"Package {package_name} not found",
            )
    else:
        # Development: use pip uninstall
        cmd = [sys.executable, '-m', 'pip', 'uninstall', '-y', package_name]
        return subprocess.run(cmd, capture_output=True, text=True)


def verify_pip_available() -> bool:
    """
    Check if pip is available in packaged app.
    
    Returns:
        True if pip can be imported, False otherwise
    """
    try:
        import pip
        logger.info("✓ pip available")
        return True
    except ImportError:
        logger.warning("✗ pip not available - in-app installs will fail")
        return False


def get_install_diagnostics() -> dict:
    """
    Get diagnostic info about install environment.
    
    Useful for debugging packaging issues.
    
    Returns:
        Dict with environment info
    """
    install_dir = get_provider_install_location()
    
    return {
        'is_packaged': is_packaged_app(),
        'python_executable': sys.executable,
        'python_version': sys.version,
        'pip_available': verify_pip_available(),
        'install_location': str(install_dir) if install_dir else 'default site-packages',
        'sys_path': sys.path,
    }
```

**Add startup verification in your main app:**

```python
# In src/vector_inspector/app.py or wherever app starts
from .services.install_service import verify_pip_available, get_install_diagnostics

def initialize_app():
    """App initialization"""
    # Verify install system works
    if not verify_pip_available():
        logger.warning("pip not available - provider installs may fail")
        # Could show a warning dialog to user
    
    # Log diagnostics in debug mode
    if logger.isEnabledFor(logging.DEBUG):
        diagnostics = get_install_diagnostics()
        logger.debug(f"Install environment: {diagnostics}")
```

---

## Fallback UX for Install Failures

**Update your provider install dialog to handle failures gracefully:**

```python
# In src/vector_inspector/ui/dialogs/provider_install_dialog.py

class ProviderInstallDialog(QDialog):
    def on_install_failed(self, provider_id: str, error_output: str):
        """Show manual install instructions if auto-install fails"""
        
        # Parse error to see if it's a known issue
        if "permission denied" in error_output.lower():
            message = (
                f"Permission denied during install.\n\n"
                f"Please run in terminal:\n"
                f"pip install vector-inspector[{provider_id}]\n\n"
                f"Then restart Vector Inspector."
            )
        elif "pip not found" in error_output.lower():
            message = (
                f"pip not available in packaged app.\n\n"
                f"Please run in terminal:\n"
                f"pip install vector-inspector[{provider_id}]\n\n"
                f"Then restart Vector Inspector."
            )
        else:
            message = (
                f"Auto-install failed.\n\n"
                f"Error: {error_output[:200]}\n\n"
                f"Please try manually:\n"
                f"pip install vector-inspector[{provider_id}]"
            )
        
        self.statusLabel.setText(message)
        
        # Add copy button for command
        self.copyCommandButton.setText(f"Copy Install Command")
        self.copyCommandButton.clicked.connect(
            lambda: QApplication.clipboard().setText(
                f"pip install vector-inspector[{provider_id}]"
            )
        )
        self.copyCommandButton.show()
```

This gives users a clear path forward even if in-app install breaks.

---

## Testing Strategy

### Phase 1: Local Packaging Test

```bash
# Build locally
briefcase create
briefcase build
briefcase run

# Check app size
du -sh build/vector-inspector/macos/app/
# Should be ~200-300MB

# Test basic functionality:
# - App launches
# - UI works
# - Can connect to a DB (if you have one running)
```

**Success criteria:**
- App launches without errors
- Size under 300MB
- UI renders correctly

### Phase 2: Test Provider Installation

```bash
# Package the app
briefcase package

# Install it properly
# macOS: copy to /Applications
# Windows: run installer
# Linux: install .deb/.rpm

# Launch and try installing a provider through UI
# Monitor logs:
# - macOS: Console.app, filter for "Vector Inspector"
# - Windows: Event Viewer
# - Linux: journalctl or ~/.vector-inspector/logs/
```

**Test cases:**
1. Install Chroma provider
   - Click install in UI
   - Watch progress
   - Verify it installs to ~/.vector-inspector/site-packages
   - Try connecting to Chroma DB
   - Restart app, verify provider still available

2. Install multiple providers
   - Chroma, Qdrant, Weaviate
   - Verify all work after restart

3. Uninstall provider
   - Remove Chroma
   - Verify it's gone
   - Reinstall, verify it works again

**If install fails:**
- Check logs for error messages
- Verify pip is bundled: `ls Vector\ Inspector.app/Contents/Resources/app_packages/ | grep pip`
- Test manual install as fallback: `pip install vector-inspector[chroma]`
- Improve error messaging in UI

### Phase 3: Cross-Platform Testing

Build on all platforms using GitHub Actions:

```yaml
# .github/workflows/build-binaries.yml
name: Build Binaries

on:
  push:
    branches: [master]
    tags: ['v*']
  workflow_dispatch:

jobs:
  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install briefcase
      
      - name: Build macOS app
        run: |
          briefcase create macOS
          briefcase build macOS
          briefcase package macOS --no-sign
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: vector-inspector-macos
          path: dist/*.dmg

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install briefcase
      
      - name: Build Windows app
        run: |
          briefcase create windows
          briefcase build windows
          briefcase package windows
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: vector-inspector-windows
          path: dist/*.msi

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install briefcase
      
      - name: Build Linux app (deb)
        run: |
          briefcase create linux
          briefcase build linux
          briefcase package linux --adhoc-sign
      
      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: vector-inspector-linux
          path: dist/*.deb
```

**Test on each platform:**
- Install the package
- Launch app
- Install a provider
- Connect to a database
- Run a search
- Test visualization (if provider supports it)

---

## Distribution Channels

### 1. GitHub Releases (Immediate)

**When:** After you have working builds for all platforms

**How:**
```bash
# Tag a release
git tag v0.8.0
git push origin v0.8.0

# GitHub Actions builds binaries automatically
# Attach them to the release
```

**Release page format:**
```markdown
# Vector Inspector v0.8.0 - Progressive Installation

Major update focused on installation speed and modularity.

## What's New
- 🚀 Install in 30 seconds (down from 10 minutes)
- 📦 Minimal core app (~150MB)
- 🔌 Install database providers on-demand
- 🎨 Improved UI for provider management
- 🐛 Bug fixes and performance improvements

## Installation

### macOS
Download: `vector-inspector-0.8.0-macos.dmg`

On first launch, right-click → Open → Open to bypass Gatekeeper.

### Windows
Download: `vector-inspector-0.8.0-windows.msi`

Run the installer, accept defaults.

### Linux (Ubuntu/Debian)
Download: `vector-inspector-0.8.0-linux.deb`

```bash
sudo dpkg -i vector-inspector-0.8.0-linux.deb
```

### From Source
```bash
pip install vector-inspector
vector-inspector
```

## Supported Databases
Chroma, Qdrant, Weaviate, Pinecone, LanceDB, pgvector, Milvus, Elasticsearch

Install providers on-demand through the app UI.

## Full Changelog
- [See full release notes](docs/RELEASE_REASON.md)
```

### 2. Homebrew (Week 2-3)

**Why:** Developers trust Homebrew, easy updates, distribution parity with VectorDBZ

**How:**

1. **Create a tap repository:**
```bash
# On GitHub, create repo: homebrew-vector-inspector
# Clone it locally
git clone https://github.com/anthonypdawson/homebrew-vector-inspector.git
cd homebrew-vector-inspector
```

2. **Create Cask formula:** `Casks/vector-inspector.rb`
```ruby
cask "vector-inspector" do
  version "0.8.0"
  sha256 "abc123..."  # Get from `shasum -a 256 vector-inspector-0.8.0-macos.dmg`

  url "https://github.com/anthonypdawson/vector-inspector/releases/download/v#{version}/vector-inspector-#{version}-macos.dmg"
  name "Vector Inspector"
  desc "RAG engineering workbench - debug, compare, and migrate vector databases"
  homepage "https://vector-inspector.divinedevops.com"

  app "Vector Inspector.app"

  zap trash: [
    "~/Library/Application Support/Vector Inspector",
    "~/.vector-inspector",
    "~/Library/Preferences/com.divinedevops.vector-inspector.plist",
    "~/Library/Caches/com.divinedevops.vector-inspector",
  ]
end
```

3. **Test locally:**
```bash
brew tap anthonypdawson/vector-inspector
brew install --cask vector-inspector
```

4. **Update README:**
```markdown
# Homebrew Tap for Vector Inspector

## Installation

```bash
brew tap anthonypdawson/vector-inspector
brew install --cask vector-inspector
```

## Updating

```bash
brew upgrade --cask vector-inspector
```
```

5. **Announce:**
- Update main repo README with Homebrew instructions
- Tweet about it
- Mention in Show HN post

### 3. Website Download Page

**Update vector-inspector.divinedevops.com/download:**

```html
<h1>Download Vector Inspector</h1>

<div class="download-options">
  <div class="platform">
    <h2>macOS</h2>
    <a href="https://github.com/.../vector-inspector-0.8.0-macos.dmg" class="download-btn">
      Download for macOS
    </a>
    <p>Requires macOS 10.15 or later</p>
    <p>Or install via Homebrew:</p>
    <code>brew install --cask vector-inspector</code>
  </div>

  <div class="platform">
    <h2>Windows</h2>
    <a href="https://github.com/.../vector-inspector-0.8.0-windows.msi" class="download-btn">
      Download for Windows
    </a>
    <p>Requires Windows 10 or later</p>
  </div>

  <div class="platform">
    <h2>Linux</h2>
    <a href="https://github.com/.../vector-inspector-0.8.0-linux.deb" class="download-btn">
      Download .deb (Ubuntu/Debian)
    </a>
    <p>Or install from PyPI:</p>
    <code>pip install vector-inspector</code>
  </div>
</div>

<div class="install-notes">
  <h3>What's Included</h3>
  <p>The core app (~150MB) with Qt UI and connection management.</p>
  <p>Database providers install on-demand through the app when you need them.</p>
  
  <h3>First Launch</h3>
  <ul>
    <li><strong>macOS:</strong> Right-click → Open on first launch to bypass Gatekeeper</li>
    <li><strong>Windows:</strong> May show SmartScreen warning, click "More info" → "Run anyway"</li>
    <li><strong>Linux:</strong> May need to mark as executable: <code>chmod +x vector-inspector</code></li>
  </ul>
</div>
```

---

## Marketing Angle: Distribution Parity

**Now you can say:**

### Before (Pain Point)
- "10-minute pip install, lots of dependencies"
- People bounce before trying it

### After (Competitive)
- "30-second download, install providers on-demand"
- Distribution parity with VectorDBZ
- Actually BETTER architecture (lean core, modular providers)

**Comparison:**

| | VectorDBZ | Vector Inspector (Post-PR) |
|---|-----------|----------------------------|
| Download size | ~150MB | ~150MB ✅ |
| Install method | Download → drag to /Applications | Same ✅ |
| Homebrew | ✅ | ✅ (after you create tap) |
| Update size | Full app (~150MB) | Core only (~150MB, providers stay) |
| Provider model | All bundled | On-demand (better!) |

**Marketing message:**
> "Vector Inspector is lightweight by design. Download the core app in seconds, then install only the database providers you actually use. Updates are fast because we only update the core, not every database driver."

---

## Timeline

### Week 1: Basic Packaging
- [ ] Merge installation PR (dependency stripping)
- [ ] Configure briefcase in pyproject.toml
- [ ] Create icon assets (icon.png, icon.icns, icon.ico)
- [ ] Run `briefcase create` and `briefcase build`
- [ ] Test locally with `briefcase run`
- [ ] Verify app size <300MB

### Week 2: Fix In-App Installs
- [ ] Implement install-to-user-directory in install_service.py
- [ ] Add startup verification (verify_pip_available)
- [ ] Test provider installation from packaged app
- [ ] Add fallback UI for manual install if needed
- [ ] Test uninstall functionality

### Week 3: Multi-Platform Builds
- [ ] Set up GitHub Actions workflow for builds
- [ ] Test builds on all platforms (macOS, Windows, Linux)
- [ ] Create release v0.8.0 with binaries attached
- [ ] Update website download page
- [ ] Write release notes

### Week 4: Distribution & Marketing
- [ ] Create Homebrew tap
- [ ] Test Homebrew installation
- [ ] Update main README with all install methods
- [ ] Announce on Show HN, Reddit, Twitter
- [ ] Update positioning doc with "distribution parity achieved"

---

## Common Issues & Solutions

### Issue: "Vector Inspector.app is damaged"
**Platform:** macOS
**Cause:** Gatekeeper blocking unsigned app
**Solution:** 
```bash
xattr -cr /Applications/Vector\ Inspector.app
```
Or right-click → Open on first launch.

### Issue: Provider install fails with "permission denied"
**Cause:** Trying to install to app bundle (read-only)
**Solution:** Already handled by installing to ~/.vector-inspector/site-packages

### Issue: Qt plugins not found
**Cause:** Briefcase didn't bundle Qt plugins correctly
**Solution:** Add to pyproject.toml:
```toml
[tool.briefcase.app.vector-inspector]
requires = [
    # ... existing requires
]
# Force include Qt plugins
resources = [
    "PySide6.Qt6.plugins",
]
```

### Issue: App crashes on launch (no error)
**Cause:** Missing dependencies or Qt platform plugin
**Debug:**
```bash
# macOS: check Console.app for crash logs
# Windows: Event Viewer → Application logs
# Linux: journalctl -f while launching

# Or run from terminal to see stdout:
./Vector\ Inspector.app/Contents/MacOS/Vector\ Inspector
```

### Issue: Huge binary size (>500MB)
**Cause:** Bundling unnecessary dependencies
**Solution:**
- Verify installation PR is merged (stripped dependencies)
- Check briefcase requirements are minimal
- Use `du -sh build/*/app/*` to find what's taking space

---

## Resources

**Briefcase Docs:**
- https://briefcase.readthedocs.io/
- https://briefcase.readthedocs.io/en/latest/how-to/code-signing/index.html (for signing)

**Qt/PySide6:**
- https://doc.qt.io/qtforpython/deployment.html
- https://doc.qt.io/qt-6/deployment.html

**Homebrew Casks:**
- https://docs.brew.sh/Cask-Cookbook
- https://github.com/Homebrew/homebrew-cask/blob/master/CONTRIBUTING.md

**GitHub Actions:**
- https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python

---

## Next Steps

1. **Merge the PR** - Dependency stripping is the foundation
2. **Test briefcase locally** - Get a working macOS build
3. **Fix in-app installs** - Critical for UX
4. **Automate builds** - GitHub Actions for all platforms
5. **Distribute** - GitHub releases, Homebrew, website
6. **Market** - Show HN with "download and try" story

**This is your path to distribution parity.** Once you have binaries, you're competing on equal footing with VectorDBZ. Then your feature advantage (LLM explainability, migration, etc.) becomes the differentiator.

---

## Questions to Answer

1. **Code signing:** Do you want to sign the macOS app? (Requires Apple Developer account, $99/year, but removes Gatekeeper warnings)

2. **Windows signing:** Same question for Windows (requires code signing cert, ~$300-500/year)

3. **Auto-updates:** Do you want built-in update checking, or rely on users re-downloading?

4. **Telemetry:** Do you want to track which platforms/install methods are most popular?

5. **Monetization:** Free binaries forever, or consider paid Pro version later?

Let me know when you're ready to start testing briefcase builds!
