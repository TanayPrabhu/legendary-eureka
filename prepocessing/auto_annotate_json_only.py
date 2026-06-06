import os
import json
import cv2
from ultralytics import YOLO
from tkinter import Tk, filedialog

def get_directory(title):
    root = Tk()
    root.withdraw()
    return filedialog.askdirectory(title=title)

def get_model_path():
    root = Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Select Current Best YOLO Model (best.pt)", filetypes=[("PyTorch Model", "*.pt")])

def main():
    print("=" * 50)
    print("🤖 YOLO TO LABELME AUTO-ANNOTATOR (RECURSIVE)")
    print("=" * 50)

    model_path = get_model_path()
    if not model_path: return

    print("\n📂 Select Master Input Folder (Original Images)")
    input_dir = get_directory("Select Master Input Folder")
    if not input_dir: return

    print("📂 Select Master Output Folder (Where JSONs will be saved)")
    output_dir = get_directory("Select Master Output Folder")
    if not output_dir: return

    print("\n📦 Loading YOLO model...")
    model = YOLO(model_path)
    class_names = model.names
    
    # 🌟 RECURSIVE SCAN: Find all images in all subfolders
    image_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_files.append(os.path.join(root, file))

    print(f"📸 Found {len(image_files)} images to auto-annotate.")

    for img_path in image_files:
        # Calculate the exact subfolder this image lives in
        rel_dir = os.path.relpath(os.path.dirname(img_path), input_dir)
        img_file = os.path.basename(img_path)
        
        # Mirror that subfolder in the output directory
        out_sub_dir = os.path.join(output_dir, rel_dir)
        os.makedirs(out_sub_dir, exist_ok=True)

        img = cv2.imread(img_path)
        if img is None: continue
        height, width = img.shape[:2]

        results = model.predict(img_path, conf=0.15, verbose=False)
        
        shapes = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                class_id = int(box.cls[0])
                label_name = class_names[class_id]

                shape = {
                    "label": label_name,
                    "points": [[x1, y1], [x2, y2]],
                    "group_id": None,
                    "shape_type": "rectangle",
                    "flags": {}
                }
                shapes.append(shape)

        labelme_data = {
            "version": "5.1.1",
            "flags": {},
            "shapes": shapes,
            "imagePath": img_file, 
            "imageData": None,     
            "imageHeight": height,
            "imageWidth": width
        }

        # Save JSON in the correctly mirrored subfolder
        json_filename = os.path.splitext(img_file)[0] + ".json"
        out_json_path = os.path.join(out_sub_dir, json_filename)
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(labelme_data, f, indent=4, ensure_ascii=False)

        print(f"  ✅ Saved: {os.path.join(rel_dir, json_filename)}")

    print("\n🎉 Auto-Annotation Complete!")

if __name__ == "__main__":
    main()