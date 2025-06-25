"""
Setup script for Desktop MCP with zero-configuration plugin system.
"""

from setuptools import setup, find_packages

setup(
    name="desktop-mcp",
    version="0.1.0",
    description="Desktop automation MCP server with zero-config NPM plugin support",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Desktop MCP Team",
    author_email="team@desktop-mcp.dev",
    url="https://github.com/your-org/desktop-mcp",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "mcp>=0.1.0",
        "psutil>=5.9.0",
        "pillow>=9.0.0",
    ],
    extras_require={
        "python-plugins": [
            "pyautogui>=0.9.54",
            "pygetwindow>=0.0.9",
        ],
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "desktop-mcp=desktop_mcp.server:main",
        ],
        # Allow other packages to register as plugins
        "desktop_mcp_plugins": [
            # Plugins can register here via their setup.py
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Systems Administration",
    ],
    keywords="mcp desktop automation plugins npm",
    project_urls={
        "Bug Reports": "https://github.com/your-org/desktop-mcp/issues",
        "Source": "https://github.com/your-org/desktop-mcp",
        "Documentation": "https://desktop-mcp.readthedocs.io/",
    },
)