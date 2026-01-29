"""Setup script for AI-Squad"""
from pathlib import Path
import re
import subprocess
import sys
import platform
import os

try:
    from setuptools import setup, find_packages
    from setuptools.command.install import install
    from setuptools.command.develop import develop
except ImportError as exc:
    raise RuntimeError("setuptools is required to install AI-Squad") from exc

# Read version
version_text = Path("ai_squad/__version__.py").read_text(encoding="utf-8")
match = re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", version_text)
if not match:
    raise RuntimeError("Unable to determine AI-Squad version")
version = {"__version__": match.group(1)}

# Read README for long description
readme = Path("README.md").read_text(encoding="utf-8")

class PostInstallCommand(install):
    """Post-installation checks for Copilot SDK compatibility and CLI."""

    def run(self):
        super().run()
        self._post_install()

    @staticmethod
    def _check_github_cli():
        """Check if GitHub CLI is installed"""
        try:
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0:
                print("[OK] GitHub CLI (gh) is installed")
                return True
            else:
                print("[X] GitHub CLI (gh) not found")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("[X] GitHub CLI (gh) not found")
            return False

    @staticmethod
    def _check_github_copilot_cli():
        """Check if GitHub Copilot CLI is installed"""
        try:
            result = subprocess.run(
                ["gh", "extension", "list"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and "copilot" in result.stdout.lower():
                print("[OK] GitHub Copilot CLI extension is installed")
                return True
            else:
                print("[X] GitHub Copilot CLI extension not found")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("[X] Cannot check GitHub Copilot CLI extension")
            return False

    @staticmethod
    def _install_github_copilot_cli():
        """Attempt to install GitHub Copilot CLI extension"""
        try:
            print("\nInstalling GitHub Copilot CLI extension...")
            result = subprocess.run(
                ["gh", "extension", "install", "github/gh-copilot"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )
            if result.returncode == 0:
                print("[OK] GitHub Copilot CLI extension installed successfully!")
                print("\nTo use AI-powered features:")
                print("  1. Authenticate: gh auth login")
                print("  2. Test: gh copilot --version")
                return True
            else:
                print(f"[X] Failed to install GitHub Copilot CLI: {result.stderr}")
                return False
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"[X] Error installing GitHub Copilot CLI: {e}")
            return False

    @staticmethod
    def _post_install():
        """Run post-installation checks and setup"""
        print("\n" + "="*60)
        print("AI-Squad Post-Installation Setup")
        print("="*60 + "\n")

        # Check Python version
        py_version = sys.version_info
        print(f"Python Version: {py_version.major}.{py_version.minor}.{py_version.micro}")
        
        # Check Copilot SDK
        try:
            from ai_squad.core.sdk_compat import ensure_copilot_sdk_compat
            result = ensure_copilot_sdk_compat(auto_fix=True, allow_network=True)
            if result.ok:
                print("[OK] GitHub Copilot SDK installed")
            else:
                print(f"[X] Copilot SDK compatibility issue: {result.message}")
        except (ImportError, RuntimeError, OSError, ValueError) as exc:
            print(f"[X] Copilot SDK check failed: {exc}")

        # Check GitHub CLI
        has_gh = PostInstallCommand._check_github_cli()
        
        if has_gh:
            # Check GitHub Copilot CLI extension
            has_copilot = PostInstallCommand._check_github_copilot_cli()
            
            if not has_copilot:
                print("\n[!] GitHub Copilot CLI extension not found!")
                print("   This is REQUIRED for AI-powered agent collaboration.")
                print("   Without it, agents will use template-based fallback (limited functionality).\n")
                
                response = input("Install GitHub Copilot CLI extension now? [Y/n]: ").strip().lower()
                if response in ("", "y", "yes"):
                    PostInstallCommand._install_github_copilot_cli()
                else:
                    print("\nSkipping installation. You can install later with:")
                    print("  gh extension install github/gh-copilot")
        else:
            print("\n[!] GitHub CLI (gh) not found!")
            print("   This is REQUIRED for AI-powered features.")
            print("\n   Installation instructions:")
            os_name = platform.system()
            if os_name == "Windows":
                print("     winget install --id GitHub.cli")
                print("     OR download from: https://cli.github.com/")
            elif os_name == "Darwin":  # macOS
                print("     brew install gh")
            else:  # Linux
                print("     See: https://github.com/cli/cli/blob/trunk/docs/install_linux.md")
            
            print("\n   After installing gh CLI:")
            print("     1. gh auth login")
            print("     2. gh extension install github/gh-copilot")
            print("     3. Reinstall ai-squad: pip install --force-reinstall ai-squad")

        print("\n" + "="*60)
        print("Setup complete! Run 'squad --help' to get started.")
        print("="*60 + "\n")


class PostDevelopCommand(develop):
    """Post-develop checks for Copilot SDK compatibility and CLI."""

    def run(self):
        super().run()
        PostInstallCommand._post_install()  # Reuse the same logic


setup(
    # Core metadata - others inherited from pyproject.toml
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    include_package_data=True,
    package_data={
        "ai_squad": [
            "templates/**/*",
            "templates/**/*.md",
            "templates/**/*.yaml",
            "skills/**/*",
            "skills/**/*.md",
            "agents_definitions/*.md",
            "prompts/*.md",
            "prompts/README.md",
            "copilot-instructions.md",
            "dashboard/templates/*.html",
            "dashboard/static/**/*",
        ],
    },
    # Post-installation hooks
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    },
)
