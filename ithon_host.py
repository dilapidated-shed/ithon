"""Run Ithon on an installed Python without shadowing that Python's stdlib."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import traceback
from types import ModuleType


ROOT = Path(__file__).resolve().parent


def load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load("ithon_static", ROOT / "Lib" / "ithon_static.py")
frontend = load("ithon_frontend", ROOT / "Lib" / "ithon_frontend.py")
runner = load("ithon_run", ROOT / "Lib" / "ithon_run.py")


def main() -> None:
    try:
        runner.main()
    except frontend.StaticTypeError as exc:
        sys.stderr.writelines(traceback.format_exception_only(exc))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
