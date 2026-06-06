"""
🔌 DEPENDENCY MANAGER — Lazy Pipeline Dependency Checker & Installer

Checks for pipeline-specific dependencies at runtime and prompts the user
to install only what's needed, keeping the project lightweight.
"""
import importlib
import subprocess
import sys

# ==========================================
# 📦 PIPELINE DEPENDENCY REGISTRY
# ==========================================
# Only lists the ADDITIONAL deps beyond the base (router + Japanese) install.
# Each entry: import_name (for checking), pip_name (for installing),
#             size (approximate download), description (shown to user).

PIPELINE_DEPS = {
    "chinese": [
        {
            "import_name": "pypinyin",
            "pip_name": "pypinyin",
            "size": "~20 MB",
            "description": "Chinese-to-Pinyin romanization (failsafe for untranslated characters)"
        },
    ],
    "korean": [
        {
            "import_name": "korean_romanizer",
            "pip_name": "korean-romanizer",
            "size": "~1 MB",
            "description": "Korean-to-Roman romanization (failsafe for untranslated Hangul)"
        },
    ],
}


def check_missing_deps(pipeline_name):
    """
    Returns a list of dependency dicts that are NOT installed for the given pipeline.
    Returns an empty list if everything is already installed.
    """
    deps = PIPELINE_DEPS.get(pipeline_name, [])
    missing = []
    for dep in deps:
        try:
            importlib.import_module(dep["import_name"])
        except ImportError:
            missing.append(dep)
    return missing


def prompt_and_install(pipeline_name):
    """
    Checks for missing deps, shows a summary to the user, and installs if accepted.
    
    Returns:
        True  — all deps are ready (already installed or just installed)
        False — user declined or installation failed
    """
    missing = check_missing_deps(pipeline_name)

    if not missing:
        return True

    # ==========================================
    # 📋 DISPLAY MISSING DEPENDENCIES
    # ==========================================
    print(f"\n{'='*55}")
    print(f"📦 {pipeline_name.upper()} PIPELINE — ADDITIONAL DEPENDENCIES REQUIRED")
    print(f"{'='*55}")
    print(f"\nThe following package(s) are needed for {pipeline_name.capitalize()} translation:\n")

    for dep in missing:
        print(f"  📌 {dep['pip_name']}  ({dep['size']})")
        print(f"     └── {dep['description']}")
        print()

    total_count = len(missing)
    print(f"  Total: {total_count} package(s) to install\n")

    # ==========================================
    # 🛑 ASK FOR USER CONSENT
    # ==========================================
    choice = input("Would you like to install these now? (y/n): ").strip().lower()

    if choice != 'y':
        print("❌ Installation declined. Cannot proceed with the "
              f"{pipeline_name.capitalize()} pipeline.")
        return False

    # ==========================================
    # ⬇️ INSTALL DEPENDENCIES
    # ==========================================
    print(f"\n⏳ Installing {pipeline_name.capitalize()} pipeline dependencies...\n")

    for dep in missing:
        pip_target = dep["pip_name"]
        print(f"  ⬇️  Installing {pip_target}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
            print(f"  ✅ {pip_target} installed successfully!")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install {pip_target}: {e}")
            print("     Please try installing manually: "
                  f"pip install {pip_target}")
            return False

    print(f"\n✅ All {pipeline_name.capitalize()} dependencies installed successfully!")
    return True

def uninstall_deps(pipeline_name):
    """
    Uninstalls the pip dependencies for the given pipeline.
    """
    deps = PIPELINE_DEPS.get(pipeline_name, [])
    for dep in deps:
        pip_target = dep["pip_name"]
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "uninstall", "-y", pip_target],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            pass # Ignore if not installed
    return True
