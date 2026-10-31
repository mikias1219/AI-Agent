"""Install a reviewed Hermes revision locally, without changing shell configuration."""

import json
import os
import subprocess
import sys
from pathlib import Path

REVISION = "b1d7c5b296d46f75d870583362640acc0cf8d6cb"
ROOT = Path(__file__).resolve().parents[1] / "data/hermes"
SOURCE = ROOT / "source"


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    if not SOURCE.exists():
        subprocess.run(
            ["git", "clone", "https://github.com/NousResearch/hermes-agent.git", str(SOURCE)],
            check=True,
        )
        subprocess.run(["git", "-C", str(SOURCE), "checkout", "--detach", REVISION], check=True)
    actual = subprocess.check_output(
        ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != REVISION:
        raise SystemExit("Hermes source revision differs; review it before updating the pin.")
    env = {**os.environ, "HERMES_HOME": str(ROOT / "home")}
    subprocess.run(
        [
            "bash",
            str(SOURCE / "scripts/install.sh"),
            "--dir",
            str(SOURCE),
            "--stage",
            "python-deps",
            "--non-interactive",
            "--skip-browser",
            "--skip-computer-use",
        ],
        env=env,
        check=True,
    )
    python = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; from pm.environments import selected_venv, venv_python; "
            "print(venv_python(selected_venv(Path.cwd())))",
        ],
        cwd=SOURCE,
        env=env,
        text=True,
    ).strip()
    if not Path(python).is_file():
        raise SystemExit("Hermes runtime interpreter was not installed.")
    (ROOT / "runtime.json").write_text(json.dumps({"python": python, "revision": actual}) + "\n")
    print("Hermes runtime ready. See docs/hermes.md for verification and activation.")


if __name__ == "__main__":
    main()
