import os
import uuid
import time
import json
from PIL import Image
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

def process_single_image(args):
    """Reads any image format, standardizes to PNG, and saves with a UUID name."""
    src_path, dst_dir, base_input = args
    
    try:
        # Generate a new unique filename
        new_filename = str(uuid.uuid4()) + ".png"
        
        # Calculate relative paths to preserve your folder structure
        rel_src_path = os.path.relpath(src_path, start=base_input)
        rel_dir = os.path.dirname(rel_src_path)
        dst_path = os.path.join(dst_dir, rel_dir, new_filename)
        
        # Ensure the destination subdirectory exists
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        
        # 1. Open the raw image
        with Image.open(src_path) as img:
            # 2. Handle transparency & Format Conversion
            has_alpha = img.mode in ('RGBA', 'LA', 'PA') or (img.mode == 'P' and 'transparency' in img.info)
            
            if has_alpha:
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
            else:
                if img.mode in ('RGBA', 'LA', 'PA'):
                    # Flatten transparent images that shouldn't have transparency (rare edge case)
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[3])
                    else:
                        img_rgba = img.convert('RGBA')
                        background.paste(img_rgba, mask=img_rgba.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
            
            # 3. Save directly as a optimized PNG with the UUID name
            img.save(dst_path, 'PNG', optimize=True)
            
        return {
            'original_path': rel_src_path,
            'new_uuid_path': os.path.join(rel_dir, new_filename)
        }
        
    except Exception as e:
        print(f"  ⚠️ Error processing {rel_src_path}: {str(e)}")
        return None

def preprocess_dataset(input_dir, output_dir, mapping_file='dataset_mapping.json'):
    print("=" * 50)
    print("🚀 MANGA DATASET PREPROCESSOR (SINGLE-PASS)")
    print("=" * 50)
    
    if not os.path.exists(input_dir):
        print(f"❌ Input directory not found: {input_dir}")
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # Recursively find ALL images (.webp, .jpg, .jpeg, .png)
    supported_formats = ('.webp', '.jpg', '.jpeg', '.png')
    image_files = []
    
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.lower().endswith(supported_formats):
                image_files.append(os.path.join(root, file))
                
    if not image_files:
        print("⚠️ No supported images found in the input directory.")
        return
        
    print(f"📸 Found {len(image_files)} raw images across all subfolders.")
    print("🔄 Standardizing formats, converting to PNG, and assigning UUIDs...")
    
    start_time = time.time()
    mappings = []
    
    # Process images in parallel using all available CPU cores
    max_workers = os.cpu_count() or 4
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        args_list = [(f, output_dir, input_dir) for f in image_files]
        for result in executor.map(process_single_image, args_list):
            if result:
                mappings.append(result)
                
    # Save the master mapping JSON so you always know where an image originally came from
    mapping_path = os.path.join(output_dir, mapping_file)
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, indent=4, ensure_ascii=False)
        
    end_time = time.time()
    print("\n" + "=" * 50)
    print("✅ PREPROCESSING COMPLETE!")
    print(f"   ⏱️  Time taken: {end_time - start_time:.2f} seconds")
    print(f"   ✓  Successfully processed: {len(mappings)} images")
    print(f"   📁 Output Folder: {output_dir}")
    print(f"   📝 Master Mapping saved to: {mapping_path}")

if __name__ == "__main__":
    raw_directory = input("📂 Enter the folder containing your RAW manga (can contain subfolders): ").strip().strip('"')
    clean_directory = input("📂 Enter the output folder for the CLEAN UUID Dataset: ").strip().strip('"')
    
    print()
    preprocess_dataset(raw_directory, clean_directory)