"""Setup script for AI-Squad"""
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop
from pathlib import Path

# Read version
version = {}
with open("ai_squad/__version__.py") as f:
    exec(f.read(), version)

# Read README for long description
readme = Path("README.md").read_text(encoding="utf-8")

class PostInstallCommand(install):
    """Post-installation checks for Copilot SDK compatibility."""

    def run(self):
        super().run()
        self._post_install()

    @staticmethod
    def _post_install():
        try:
            from ai_squad.core.sdk_compat import ensure_copilot_sdk_compat

            result = ensure_copilot_sdk_compat(auto_fix=True, allow_network=True)
            if not result.ok:
                print(f"WARN Copilot SDK compatibility check failed: {result.message}")
        except Exception as exc:
            print(f"WARN Copilot SDK compatibility check skipped: {exc}")


class PostDevelopCommand(develop):
    """Post-develop checks for Copilot SDK compatibility."""

    def run(self):
        super().run()
        self._post_install()

    @staticmethod
    def _post_install():
        try:
            from ai_squad.core.sdk_compat import ensure_copilot_sdk_compat

            result = ensure_copilot_sdk_compat(auto_fix=True, allow_network=True)
            if not result.ok:
                print(f"WARN Copilot SDK compatibility check failed: {result.message}")
        except Exception as exc:
            print(f"WARN Copilot SDK compatibility check skipped: {exc}")


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
            "skills/**/*",
            "workflows/**/*",
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
