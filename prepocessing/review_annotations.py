import os
import json
import subprocess
from pathlib import Path
from tkinter import Tk, filedialog

def get_directory(title):
    root = Tk()
    root.withdraw()
    return filedialog.askdirectory(title=title)

def setup_labelme_config():
    """Generates a clean config without terminal warnings."""
    config_path = Path(__file__).resolve().parent / "labelme_review_config.json"
    
    config = {
        "labels": ["speech bubble", "sfx", "thought bubble"]
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
    return str(config_path)

def patch_jsons_in_folder(json_dir, image_dir):
    """🔧 The Fix: Instantly points JSON files to the absolute image paths."""
    print("\n🔧 Patching JSON paths for LabelMe (This takes 0.1 seconds)...")
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    
    for j_file in json_files:
        j_path = os.path.join(json_dir, j_file)
        
        try:
            with open(j_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Get just the filename (e.g., "0a768c1b.png")
            img_filename = os.path.basename(data.get("imagePath", ""))
            if not img_filename:
                img_filename = j_file.replace('.json', '.png')

            # Create the absolute path pointing to the actual image directory
            abs_image_path = os.path.abspath(os.path.join(image_dir, img_filename))

            # Only rewrite the file if the path needs to be fixed
            if data.get("imagePath") != abs_image_path:
                data["imagePath"] = abs_image_path
                with open(j_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    
        except Exception as e:
            print(f"⚠️ Could not patch {j_file}: {e}")

def main():
    print("=" * 50)
    print("👁️  LABELME REVIEW LAUNCHER (PATH PATCHER ENABLED)")
    print("=" * 50)

    print("\n📂 Select the SPECIFIC IMAGE SUBFOLDER you want to review today...")
    image_dir = get_directory("Select Specific Image Subfolder")
    if not image_dir: return

    print("📂 Select the MATCHING JSON SUBFOLDER...")
    json_dir = get_directory("Select Matching JSON Subfolder")
    if not json_dir: return

    # 1. Generate clean config
    config_path = setup_labelme_config()

    # 2. Fix the JSON paths instantly
    patch_jsons_in_folder(json_dir, image_dir)

    print("\n🚀 Launching LabelMe for this specific folder...")
    print(f"   Images: {image_dir}")
    print(f"   JSONs:  {json_dir}")

    cmd = [
        "labelme",
        image_dir,
        "--output", json_dir,
        "--config", config_path,
        "--nodata" 
    ]

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print("❌ LabelMe not found! Make sure it is installed (pip install labelme)")

if __name__ == "__main__":
    main()
    