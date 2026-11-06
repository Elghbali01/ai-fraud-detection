"""Validate and sequentially execute tracked notebooks with nbclient."""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import nbformat
from nbclient import NotebookClient

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    notebooks = sorted((ROOT / "notebooks").glob("*.ipynb"))
    if not notebooks:
        print("No notebooks found.", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="fraud-notebook-ipython-") as ipython_dir:
        os.environ["IPYTHONDIR"] = ipython_dir
        startup_dir = Path(ipython_dir) / "startup"
        startup_dir.mkdir()
        (startup_dir / "sitecustomize.py").write_text(
            "import asyncio\n"
            "import sys\n"
            "if sys.platform == 'win32':\n"
            "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n",
            encoding="utf-8",
        )
        inherited_pythonpath = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = os.pathsep.join(
            part for part in (str(startup_dir), str(ROOT / "src"), inherited_pythonpath) if part
        )
        for notebook_path in notebooks:
            notebook = nbformat.read(notebook_path, as_version=4)
            nbformat.validate(notebook)
            NotebookClient(
                notebook,
                timeout=300,
                kernel_name="python3",
                resources={"metadata": {"path": str(ROOT)}},
            ).execute()
            print(f"Executed: {notebook_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
