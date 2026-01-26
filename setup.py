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
    name="ai-squad",
    version=version["__version__"],
    description="Your AI Development Squad - Five expert AI agents, one command away",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="Piyush Jain",
    author_email="piyush@example.com",
    url="https://github.com/jnPiyush/AI-Squad",
    project_urls={
        "Bug Reports": "https://github.com/jnPiyush/AI-Squad/issues",
        "Source": "https://github.com/jnPiyush/AI-Squad",
        "Documentation": "https://github.com/jnPiyush/AI-Squad/tree/main/docs",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    include_package_data=True,
    package_data={
        "ai_squad": [
            "templates/**/*",
            "templates/**/*.md",
            "templates/**/*.yaml",
            "skills/**/*",
            "skills/**/*.md",
            "skills/**/*.yaml",
            "agents_definitions/*.md",
            "prompts/*.md",
            "prompts/README.md",
            "copilot-instructions.md",
            "dashboard/templates/*.html",
            "dashboard/static/**/*",
        ],
    },
    python_requires=">=3.11",
    install_requires=[
        "click>=8.1.0",
        "rich>=13.0.0",
        "pyyaml>=6.0",
        "github-copilot-sdk>=0.1.16",
        "aiohttp>=3.9.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "ruff>=0.1.9",
            "mypy>=1.8.0",
            "pre-commit>=3.6.0",
        ],
        "docs": [
            "mkdocs>=1.5.0",
            "mkdocs-material>=9.5.0",
            "mkdocstrings[python]>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "squad=ai_squad.cli:main",
            "ai-squad=ai_squad.cli:main",  # Alias
        ],
    },
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Software Development :: Quality Assurance",
    ],
    keywords="ai agents copilot development productivity automation github",
    license="MIT",
)
