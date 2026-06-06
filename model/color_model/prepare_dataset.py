import os
import shutil
import json
import random
from pathlib import Path

def get_base_dir():
    return Path(__file__).resolve().parent.parent.parent

def convert_labelme_to_yolo(labelme_json_path, yolo_txt_path, class_mapping):
    # ... (Keep your exact same convert_labelme_to_yolo function code here, no changes needed) ...
    try:
        with open(labelme_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        print(f"⚠️ Error reading {labelme_json_path}: {e}")
        return False

    image_width = data.get('imageWidth', 0)
    image_height = data.get('imageHeight', 0)
    
    if image_width == 0 or image_height == 0:
        return False

    try:
        with open(yolo_txt_path, 'w', encoding='utf-8') as f:
            for shape in data.get('shapes', []):
                label = shape.get('label', '')
                if label in class_mapping:
                    class_id = class_mapping[label]
                    points = shape.get('points', [])
                    
                    if len(points) < 2:
                        continue

                    x_min = min(p[0] for p in points)
                    y_min = min(p[1] for p in points)
                    x_max = max(p[0] for p in points)
                    y_max = max(p[1] for p in points)

                    x_min = max(0, min(x_min, image_width))
                    x_max = max(0, min(x_max, image_width))
                    y_min = max(0, min(y_min, image_height))
                    y_max = max(0, min(y_max, image_height))

                    if x_max <= x_min or y_max <= y_min:
                        continue

                    x_center = (x_min + x_max) / (2 * image_width)
                    y_center = (y_min + y_max) / (2 * image_height)
                    width = (x_max - x_min) / image_width
                    height = (y_max - y_min) / image_height

                    f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
        return True
    except IOError as e:
        return False

def process_image_list(image_list, image_source_folder, annotation_source_folder, output_dir, class_mapping):
    """Process a specific list of images and route them to train or val."""
    processed = 0
    errors = 0
    
    for img_file in image_list:
        src_img_path = os.path.join(image_source_folder, img_file)
        dst_img_path = os.path.join(output_dir, "images", img_file)
        
        try:
            shutil.copy2(src_img_path, dst_img_path)
        except IOError as e:
            errors += 1
            continue

        json_filename = os.path.splitext(img_file)[0] + ".json"
        json_path = os.path.join(annotation_source_folder, json_filename)
        yolo_path = os.path.join(output_dir, "labels", os.path.splitext(img_file)[0] + ".txt")

        if os.path.exists(json_path):
            if convert_labelme_to_yolo(json_path, yolo_path, class_mapping):
                processed += 1
            else:
                errors += 1
        else:
            try:
                open(yolo_path, 'w').close()
                processed += 1
            except IOError as e:
                errors += 1
                
    return processed, errors

def main():
    base_dir = get_base_dir()
    data_dir = base_dir / "data_uniqueid"
    image_source_dir = data_dir / "color"
    annotation_source_dir = data_dir / "annotations" / "color"

    model_dir = base_dir / "model" / "color_model"
    train_dir = model_dir / "train"
    val_dir = model_dir / "val"

    # Create YOLO directory structure
    for dir_path in [train_dir / "images", train_dir / "labels", 
                     val_dir / "images", val_dir / "labels"]:
        os.makedirs(dir_path, exist_ok=True)

    class_mapping = {
        "speech bubble": 0,
        "sfx": 1,
        "thought bubble": 2
    }

    print("=" * 50)
    print("📦 STRATIFIED DATASET PREPARATION")
    print("=" * 50)
    
    # Dynamically find all subfolders (1, 2, 3, etc.)
    all_folders = [f for f in os.listdir(image_source_dir) if os.path.isdir(os.path.join(image_source_dir, f))]
    
    if not all_folders:
        print(f"❌ No subfolders found in {image_source_dir}")
        return

    print(f"📁 Found {len(all_folders)} manga folders to process.")
    
    total_train_processed = 0
    total_val_processed = 0

    # Iterate through each folder and do an 80/20 split
    for folder in all_folders:
        print(f"\n📚 Processing Folder: {folder}")
        
        img_folder_path = os.path.join(image_source_dir, folder)
        ann_folder_path = os.path.join(annotation_source_dir, folder)
        
        # Get all valid images in this specific folder
        images = [f for f in os.listdir(img_folder_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif', '.gif'))]
        
        if not images:
            print(f"   ⚠️ No images found, skipping.")
            continue
            
        # Shuffle the images randomly
        random.shuffle(images)
        
        # Calculate the 80% split point
        split_idx = int(len(images) * 0.8)
        
        train_images = images[:split_idx]
        val_images = images[split_idx:]
        
        # Process Training set
        t_proc, t_err = process_image_list(train_images, img_folder_path, ann_folder_path, str(train_dir), class_mapping)
        total_train_processed += t_proc
        print(f"   ✓ Train: {t_proc} images")
        
        # Process Validation set
        v_proc, v_err = process_image_list(val_images, img_folder_path, ann_folder_path, str(val_dir), class_mapping)
        total_val_processed += v_proc
        print(f"   ✓ Val:   {v_proc} images")

    print("\n" + "=" * 50)
    print("✅ Dataset preparation complete!")
    print(f"   📊 Total Training:   {total_train_processed} images")
    print(f"   📊 Total Validation: {total_val_processed} images")

if __name__ == "__main__":
    main()