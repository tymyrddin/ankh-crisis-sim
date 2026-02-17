"""Entry point for the Ankh-Morpork Crisis Simulator."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # Ensure project root is on path
    project_root = Path(__file__).parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from src.gui.app import App

    app = App(
        config_dir=str(project_root / "config"),
        map_image=str(project_root / "static" / "images" / "ankh-morpork.png"),
    )
    app.mainloop()


if __name__ == "__main__":
    main()