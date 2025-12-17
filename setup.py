from setuptools import setup, find_packages

setup(
    name="repo-structure-tool",
    version="0.1.0",
    description="A suggest-first tool to analyze and clean up Python repository structure",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "pathspec>=0.11.0",
    ],
    entry_points={
        "console_scripts": [
            "repo-tool=src.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
