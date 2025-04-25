#!/usr/bin/env python
"""Setup script for the Local LLM Protection System."""

import os
from setuptools import setup, find_packages

# Get version from VERSION file
VERSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
VERSION = "1.0.0"  # Default version
if os.path.exists(VERSION_FILE):
    with open(VERSION_FILE, "r") as f:
        VERSION = f.read().strip()

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

# Read requirements from requirements.txt
with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="llm-protection-system",
    version=VERSION,
    description="A protection system for local large language models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/llm-protection-system",
    packages=find_packages(include=['src', 'src.*']),
    package_dir={'': '.'},
    include_package_data=True,
    package_data={
        "": ["static/**/*", "rules/**/*"],
    },
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "llm-protection=src.main:main",
        ],
    },
    py_modules=["src"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Security",
    ],
    python_requires=">=3.8",
    keywords="llm, security, firewall, protection, ai, machine learning",
)
