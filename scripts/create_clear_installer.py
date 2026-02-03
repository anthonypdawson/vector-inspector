import tomllib
from pathlib import Path
import subprocess
import re

# --- CONFIG
PROJECT_NAME = "vector-inspector"
TARGET_PLATFORM = "windows"


def get_version():
    with open("pyproject.toml", "rb") as f:
        return tomllib.load(f)["project"]["version"]


def update_wxs(version):
    wxs_path = Path("build") / PROJECT_NAME / TARGET_PLATFORM / "app" / f"{PROJECT_NAME}.wxs"
    if wxs_path.exists():
        content = wxs_path.read_text()
        new_content = re.sub(r'Version="[^"]+"', f'Version="{version}"', content)
        wxs_path.write_text(new_content)
        print(f"--> [VERSION SYNC] {wxs_path.name} is now v{version}")


def main():
    version = get_version()
    print(f"--- Packaging {PROJECT_NAME} v{version} ---")

    # 1. Update the scaffold (Standard Briefcase)
    subprocess.run(["briefcase", "update", TARGET_PLATFORM, "--no-input"], check=True, shell=True)

    # 2. Fix the Version in the WiX template
    update_wxs(version)

    # 3. Package it!
    # No obfuscation needed, just standard packaging
    subprocess.run(["briefcase", "package", TARGET_PLATFORM, "--no-input"], check=True, shell=True)

    print(f"\n[SUCCESS] Installer ready: windows/{PROJECT_NAME}-{version}.msi")


if __name__ == "__main__":
    main()
