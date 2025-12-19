"""Ecosystem profiles for repository analysis.

V2: Static, hardcoded profiles that define behavior based on repository type.
V2: No configuration files or CLI flags - automatic selection only.
V2: Suppresses expected framework duplicates to reduce noise in frontend repositories.
"""
from dataclasses import dataclass
from typing import Set
from .repo_type import RepoType


@dataclass
class EcosystemProfile:
    """V2: Defines behavior and exclusions for a specific ecosystem."""
    name: str
    ignored_duplicate_patterns: Set[str]
    risk_adjustments: dict
    
    def should_suppress_duplicate(self, filename: str) -> bool:
        """V2: Check if duplicate should be suppressed for this filename.
        
        Used to filter out valid framework patterns like multiple index.html files
        in multi-page Next.js sites, which are expected and not errors.
        """
        filename_lower = filename.lower()
        for pattern in self.ignored_duplicate_patterns:
            if pattern in filename_lower:
                return True
        return False


# V2: Python ecosystem profile - no duplicate suppressions
PYTHON_PROFILE = EcosystemProfile(
    name="python",
    ignored_duplicate_patterns=set(),  # No suppression for Python
    risk_adjustments={},
)

# V2: Next.js / frontend framework profile - suppresses common Next.js patterns
NEXTJS_PROFILE = EcosystemProfile(
    name="nextjs",
    ignored_duplicate_patterns={
        'index.html',      # Common in multi-page sites
        'index.tsx',       # React entry points
        'index.ts',        # TypeScript entry points
        'page.tsx',        # Next.js app router
        'layout.tsx',      # Next.js layouts
        '_app.tsx',        # Next.js app wrapper
        '_document.tsx',   # Next.js document
    },
    risk_adjustments={},
)

# V2: Static frontend profile - suppresses basic frontend patterns
FRONTEND_STATIC_PROFILE = EcosystemProfile(
    name="frontend-static",
    ignored_duplicate_patterns={
        'index.html',
        'index.js',
        'index.css',
    },
    risk_adjustments={},
)


def get_profile_for_repo_type(repo_type: RepoType) -> EcosystemProfile:
    """Select appropriate ecosystem profile based on repository type."""
    if repo_type == RepoType.PYTHON_DOMINANT:
        return PYTHON_PROFILE
    elif repo_type == RepoType.NON_PYTHON:
        # For non-Python, assume frontend
        return NEXTJS_PROFILE
    else:  # MIXED
        # For mixed repos, use conservative frontend profile
        return NEXTJS_PROFILE
