import os
import shutil
import subprocess
import re
import tomllib
from pathlib import Path

# --- CONFIGURATION ---
PROJECT_NAME = "vector-inspector"
APP_PACKAGE = "vector_inspector"
TARGET_PLATFORM = "windows"
# ---------------------


def get_version():
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
        return data.get("project", {}).get("version", "0.0.1")


def update_wix_metadata(version):
    """Syncs version to WiX template to fix MSI filename."""
    wxs_path = Path("build") / PROJECT_NAME / TARGET_PLATFORM / "app" / "vector-inspector.wxs"
    if wxs_path.exists():
        content = wxs_path.read_text()
        new_content = re.sub(r'Version="[\d\.]+"', f'Version="{version}"', content)
        wxs_path.write_text(new_content)
        print(f"--> Synced MSI template to version {version}")


def perform_obfuscated_swap(build_root):
    """
    Swaps clear-text code for PyArmor protected code and
    removes the clear-text 'wheel' install from app_packages.
    """
    src_root = build_root / "src"
    briefcase_package_path = src_root / APP_PACKAGE

    # Identify PyArmor runtime
    runtime_folder = next(Path("dist").glob("pyarmor_runtime*")).name
    briefcase_runtime_path = src_root / runtime_folder

    # 1. Swap the main source folder
    print(f"--> Swapping obfuscated code into {briefcase_package_path}")
    if briefcase_package_path.exists():
        shutil.rmtree(briefcase_package_path)
    shutil.copytree(Path("dist") / APP_PACKAGE, briefcase_package_path)

    # 2. Inject the runtime folder
    if briefcase_runtime_path.exists():
        shutil.rmtree(briefcase_runtime_path)
    shutil.copytree(Path("dist") / runtime_folder, briefcase_runtime_path)

    # 3. CRITICAL: Remove the clear-text install from site-packages (app_packages)
    # This is where Briefcase stores the 'installed' version of your app.
    app_packages_path = build_root / "app_packages" / APP_PACKAGE
    if app_packages_path.exists():
        print(f"--> [CLEANUP] Removing clear-text wheel install from {app_packages_path}")
        shutil.rmtree(app_packages_path)

    # Also remove the .dist-info folder to be thorough
    dist_info_path = next((build_root / "app_packages").glob(f"{APP_PACKAGE}-*.dist-info"), None)
    if dist_info_path and dist_info_path.exists():
        print(f"--> [CLEANUP] Removing metadata from {dist_info_path}")
        shutil.rmtree(dist_info_path)


def run_cmd(cmd):
    print(f"--> Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, shell=True)


def main():
    version = get_version()
    print(f"\n=== Starting Protected Build v{version} ===\n")

    # 1. Update/Create Briefcase project
    run_cmd(["briefcase", "update", TARGET_PLATFORM, "--no-input"])
    update_wix_metadata(version)

    # 2. Obfuscate with PyArmor
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    print("\nStep 2: Obfuscating...")
    run_cmd(["pyarmor", "cfg", "data_files=*"])
    run_cmd(["pyarmor", "gen", "-O", "dist", "-r", f"src/{APP_PACKAGE}"])

    # 3. Path Setup (pointing to the 'app' root inside the build folder)
    build_app_root = Path("build") / PROJECT_NAME / TARGET_PLATFORM / "app"

    # 4. First Swap (Pre-Build)
    perform_obfuscated_swap(build_app_root)

    # 5. Build
    print("\nStep 6: Running Briefcase build...")
    run_cmd(["briefcase", "build", TARGET_PLATFORM, "--no-input"])

    # 6. SAFETY SWAP (Final check before packaging)
    print("\nStep 7: Performing Final Safety Swap...")
    perform_obfuscated_swap(build_app_root)

    # 7. Package
    print("\nStep 8: Packaging MSI...")
    # We remove --no-update. Since we aren't using '-u', Briefcase
    # should leave our build/ folder alone.
    run_cmd(["briefcase", "package", TARGET_PLATFORM, "--no-input"])

    print(f"\n[SUCCESS] Protected MSI v{version} is ready in the windows/ folder.")


if __name__ == "__main__":
    main()
