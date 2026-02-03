import os
import shutil
import subprocess
from pathlib import Path

# --- CONFIGURATION ---
PROJECT_NAME = "vector-inspector"
APP_PACKAGE = "vector_inspector"
TARGET_PLATFORM = "windows"
# ---------------------

def run_cmd(cmd):
    print(f"--> Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, shell=True)

def main():
    # 1. Preparation - Briefcase Update
    print(f"Step 1: Updating {TARGET_PLATFORM} scaffold...")
    # Using 'update' instead of 'create' to avoid the "will not be overwritten" error
    run_cmd(["briefcase", "update", TARGET_PLATFORM, "--no-input"])

    if os.path.exists("dist"):
        shutil.rmtree("dist")
    
    # 2. Configure PyArmor
    print("\nStep 2: Configuring PyArmor...")
    run_cmd(["pyarmor", "cfg", "data_files=*"])

    # 3. Obfuscate source - Optimized for Speed
    print("\nStep 3: Obfuscating source with PyArmor...")
    # Removed --no-runtime to avoid the --outer error. 
    # Added --mix for better performance-to-protection ratio.
    run_cmd([
        "pyarmor", "gen", 
        "-O", "dist", 
        "--mix",           # Mixed obfuscation is often faster than full restrict
        "-r", f"src/{APP_PACKAGE}"
    ])

    # 4. Define Briefcase Build Paths
    build_src_root = Path("build") / PROJECT_NAME / TARGET_PLATFORM / "app" / "src"
    briefcase_package_path = build_src_root / APP_PACKAGE
    
    # Locate the runtime folder
    try:
        runtime_folder = next(Path("dist").glob("pyarmor_runtime*")).name
    except StopIteration:
        print("Error: PyArmor runtime folder not found in dist/.")
        return

    briefcase_runtime_path = build_src_root / runtime_folder

    # 5. Overwrite Briefcase source
    print(f"\nStep 4: Replacing source in {briefcase_package_path}...")
    if briefcase_package_path.exists():
        shutil.rmtree(briefcase_package_path)
    shutil.copytree(Path("dist") / APP_PACKAGE, briefcase_package_path)

    # 6. Copy PyArmor runtime
    print(f"Step 5: Adding {runtime_folder} to {build_src_root}...")
    if briefcase_runtime_path.exists():
        shutil.rmtree(briefcase_runtime_path)
    shutil.copytree(Path("dist") / runtime_folder, briefcase_runtime_path)

    # 7. Final Build
    print("\nStep 6: Building protected app...")
    run_cmd(["briefcase", "build", TARGET_PLATFORM, "--no-input"])

    print(f"\n[SUCCESS] Build complete. Run 'briefcase run {TARGET_PLATFORM}' to test.")

if __name__ == "__main__":
    main()
