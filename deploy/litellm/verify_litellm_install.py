"""Verify LiteLLM install is not the compromised 1.107.0 release.

Run on the proxy host or in the proxy venv:
    python deploy/litellm/verify_litellm_install.py
"""

from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

COMPROMISED_VERSION = "1.107.0"
IOC_FILES = ("cook.pth", "cook.py", "sitecustomize.py")


def _scan_site_packages_for_ioc() -> list[Path]:
    import site

    hits: list[Path] = []
    for root in site.getsitepackages() + [site.getusersitepackages()]:
        base = Path(root)
        if not base.is_dir():
            continue
        for name in IOC_FILES:
            candidate = base / name
            if candidate.is_file():
                hits.append(candidate)
    return hits


def main() -> int:
    try:
        version = importlib.metadata.version("litellm")
    except importlib.metadata.PackageNotFoundError:
        print("litellm is not installed in this environment.", file=sys.stderr)
        return 1

    if version == COMPROMISED_VERSION:
        print(
            f"REFUSED: litellm=={COMPROMISED_VERSION} is a known compromised release. "
            "Rebuild the environment and pin to deploy/litellm/requirements.txt.",
            file=sys.stderr,
        )
        return 2

    ioc = _scan_site_packages_for_ioc()
    if ioc:
        print("Possible compromise indicators found:", file=sys.stderr)
        for path in ioc:
            print(f"  {path}", file=sys.stderr)
        print(
            "Treat this environment as compromised; rebuild and rotate secrets.",
            file=sys.stderr,
        )
        return 3

    print(f"OK: litellm {version} (not {COMPROMISED_VERSION}); no IOC files in site-packages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
