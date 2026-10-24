import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import venv
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.core.infrastructure.services.tools.plugins import manifest, contained, NAME


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["install", "remove-env"])
    parser.add_argument("plugin")
    args = parser.parse_args()
    if not NAME.fullmatch(args.plugin):
        parser.error("Invalid plugin ID")
    environments = ROOT / ".plugin-envs"
    target = contained(environments, args.plugin)
    if target == environments.resolve():
        raise ValueError("Refusing to modify environment root")
    if args.action == "remove-env":
        if target.exists():
            shutil.rmtree(target)
        print("Environment removed; plugin sources preserved. Disable or remove its folder before next Start.")
        return
    folder = contained(ROOT / "plugins", args.plugin)
    data = manifest(folder)
    requirements = data.get("requirements")
    requirement_file = contained(folder, requirements) if requirements else None
    if requirement_file and not requirement_file.is_file():
        raise ValueError("Requirements file not found")
    ready = target / ".ready"
    ready.unlink(missing_ok=True)
    venv.EnvBuilder(with_pip=True).create(target)
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if requirement_file:
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(requirement_file)], check=True, cwd=folder)
    ready.write_text("SDK 1", encoding="utf-8")
    print("Plugin environment ready. Restart Lina to discover tools.")


if __name__ == "__main__":
    main()
