#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import platform
import sys
from typing import Any


EXPECTED_PYTHON = (3, 10)
EXPECTED_MODULES = {
    "numpy": "2.2.6",
    "scipy": "1.15.3",
    "matplotlib": "3.10.8",
    "sklearn": "1.7.2",
    "torch": "2.10.0",
    "torch_geometric": "2.7.0",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check the OpenFedBot runtime environment")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on missing or mismatched versions")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    return parser.parse_args()


def _version_matches(name: str, actual: str, expected: str) -> bool:
    if name == "torch":
        return actual == expected or actual.startswith(f"{expected}+")
    return actual == expected


def collect_report() -> dict[str, Any]:
    python_version = platform.python_version()
    python_ok = sys.version_info[:2] == EXPECTED_PYTHON
    modules: dict[str, dict[str, Any]] = {}
    problems: list[str] = []

    for module_name, expected_version in EXPECTED_MODULES.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as exc:
            modules[module_name] = {
                "status": "missing",
                "expected": expected_version,
                "error": str(exc),
            }
            problems.append(f"{module_name}: missing")
            continue

        actual_version = str(getattr(module, "__version__", "unknown"))
        version_ok = _version_matches(module_name, actual_version, expected_version)
        modules[module_name] = {
            "status": "ok" if version_ok else "mismatch",
            "expected": expected_version,
            "actual": actual_version,
        }
        if not version_ok:
            problems.append(f"{module_name}: expected {expected_version}, found {actual_version}")

    cuda_available = False
    if modules.get("torch", {}).get("status") != "missing":
        torch_module = importlib.import_module("torch")
        cuda_available = bool(torch_module.cuda.is_available())

    return {
        "python": {
            "expected_major_minor": f"{EXPECTED_PYTHON[0]}.{EXPECTED_PYTHON[1]}",
            "actual": python_version,
            "status": "ok" if python_ok else "mismatch",
        },
        "modules": modules,
        "cuda_available": cuda_available,
        "problems": problems,
    }


def main() -> None:
    args = parse_args()
    report = collect_report()

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"python\t{report['python']['actual']}\t{report['python']['status']}")
        for module_name in EXPECTED_MODULES:
            payload = report["modules"][module_name]
            if payload["status"] == "missing":
                print(f"{module_name}\tmissing\t{payload['error']}")
            else:
                print(f"{module_name}\t{payload['actual']}\t{payload['status']}")
        print(f"cuda_available\t{int(report['cuda_available'])}")

    if args.strict:
        has_problem = report["python"]["status"] != "ok" or bool(report["problems"])
        if has_problem:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
