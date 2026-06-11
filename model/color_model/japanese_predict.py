from ultralytics import YOLO
import os
import json
import base64
import cv2
import numpy as np
import textwrap
import re
import shared_state
from PIL import Image, ImageDraw, ImageFont
from tkinter import Tk, filedialog

from simple_lama_inpainting import SimpleLama
from japanese_ocr import extract_text_from_region
from japanese_translator import translate_text, should_translate_category

def get_model_path():
    print("\n🔍 Please select the trained model file (e.g., best.pt)...")
    root = Tk()
    root.withdraw()
    model_path = filedialog.askopenfilename(title="Select Trained YOLO Model", filetypes=[("PyTorch Model", "*.pt")])
    if not model_path: raise FileNotFoundError("No model selected.")
    return model_path

def iou(boxA, boxB):
    xA, yA = max(boxA[0], boxB[0]), max(boxA[1], boxB[1])
    xB, yB = min(boxA[2], boxB[2]), min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    return interArea / float(((boxA[2] - boxA[0]) * (boxA[3] - boxA[1])) + ((boxB[2] - boxB[0]) * (boxB[3] - boxB[1])) - interArea + 1e-6)

def is_contained(inner, outer, threshold=0.85):
    ix1, iy1, ix2, iy2 = inner
    ox1, oy1, ox2, oy2 = outer
    inter_x1, inter_y1 = max(ix1, ox1), max(iy1, oy1)
    inter_x2, inter_y2 = min(ix2, ox2), min(iy2, oy2)
    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    return (inter_area / ((ix2 - ix1) * (iy2 - iy1) + 1e-6)) > threshold

def suppress_overlaps(boxes, scores, labels, iou_thresh=0.5, min_size=10):
    keep = []
    n = len(boxes)
    for i in range(n):
        discard = False
        if (boxes[i][2] - boxes[i][0]) < min_size or (boxes[i][3] - boxes[i][1]) < min_size: continue
        for j in range(n):
            if i == j: continue
            if is_contained(boxes[i], boxes[j]):
                if (boxes[i][2] - boxes[i][0]) * (boxes[i][3] - boxes[i][1]) < (boxes[j][2] - boxes[j][0]) * (boxes[j][3] - boxes[j][1]):
                    discard = True; break
            if iou(boxes[i], boxes[j]) > iou_thresh and scores[i] < scores[j]:
                discard = True; break
        if not discard: keep.append(i)
    return [boxes[k] for k in keep], [scores[k] for k in keep], [labels[k] for k in keep]

def get_base_font_path():
    for font_name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf", "NotoSans-Regular.ttf"]:
        try: ImageFont.truetype(font_name, 10); return font_name
        except IOError: continue
    return None

def clean_translation(text):
    if not text: return text
    # ✅ Strips out <unk> and other weird translation artifacts
    text = text.replace("<unk>", "")
    blacklist = ["sync", "corrected by", "elderman", "subtitles", "translation by"]
    lower_text = text.lower()
    for bad in blacklist:
        if bad in lower_text: return ""
    words = text.split()
    cleaned = []
    for word in words:
        if not cleaned or word.lower() != cleaned[-1].lower():
            cleaned.append(word)
    return " ".join(cleaned).strip()

def is_emotional_exclamation(text):
    if not text: return False
    return bool(re.search(r'([あいうえおアイウエオハヒフヘホ])\1{2,}', text))

def quality_assurance_check(japanese_text, english_text):
    if not english_text: return False
    if re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', english_text): return False
    if len(japanese_text) > 10 and len(english_text) < (len(japanese_text) * 0.5): return False
    return True

def wrap_text_in_box(draw, text, box, font_path, text_color="black", max_font_size=28, min_font_size=8, force_outline_color=None):
    x1, y1, x2, y2 = box
    box_width, box_height = x2 - x1, y2 - y1
    font_size, wrapped_lines, font = max_font_size, [], None
    
    while font_size >= min_font_size:
        font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
        if not font_path: break
        avg_w = font.getlength("A") if hasattr(font, 'getlength') else font.getsize("A")[0]
        chars_per_line = max(1, int(box_width / (avg_w * 1.1)))
        wrapped_lines = textwrap.wrap(text, width=chars_per_line, break_long_words=False)
        line_h = font.getbbox("A")[3] if hasattr(font, 'getbbox') else font.getsize("A")[1]
        if len(wrapped_lines) * line_h <= box_height: break
        font_size -= 1
        
    if not wrapped_lines: wrapped_lines = [text]
    line_h = font.getbbox("A")[3] if hasattr(font, 'getbbox') else font.getsize("A")[1]
    current_y = y1 + max(0, (box_height - (len(wrapped_lines) * line_h)) / 2)
    
    stroke_width = max(1, font_size // 12)
    outline_color = force_outline_color or ("white" if text_color == "black" else "black")
    
    for line in wrapped_lines:
        line_w = font.getlength(line) if hasattr(font, 'getlength') else font.getsize(line)[0]
        current_x = x1 + max(0, (box_width - line_w) / 2)
        draw.text((current_x, current_y), line, fill=text_color, font=font, stroke_width=stroke_width, stroke_fill=outline_color)
        current_y += line_h

def process_japanese_manga(input_dir, output_img_dir, output_json_dir):
    try:
        model_path = get_model_path(); print(f"📦 Loading YOLO model...")
        trained_model = YOLO(model_path); print("🪄 Loading LaMa AI Inpainting model...")
        lama = SimpleLama()
    except Exception as e: 
        print(f"❌ Failed to load models: {e}")
        return

    os.makedirs(output_img_dir, exist_ok=True)
    os.makedirs(output_json_dir, exist_ok=True)
    class_names, font_path = trained_model.names, get_base_font_path()
    conf_threshold = 0.25

    image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    print(f"📸 Processing {len(image_files)} Japanese images...")

    for idx, image_filename in enumerate(image_files, 1):
        if shared_state.stop_requested:
            print("\n🛑 Stop requested by user. Halting Japanese translation batch.")
            break
            
        image_path = os.path.join(input_dir, image_filename); print(f"\n📄 [{idx}/{len(image_files)}] Processing: {image_filename}")
        results = trained_model.predict(image_path, verbose=False, conf=conf_threshold, imgsz=1024)
        boxes, scores, labels = [], [], []
        for result in results:
            for box in result.boxes:
                boxes.append(box.xyxy[0].tolist()); scores.append(float(box.conf[0])); labels.append(class_names[int(box.cls[0])])

        final_boxes, final_scores, final_labels = suppress_overlaps(boxes, scores, labels)
        
        img_pil = Image.open(image_path).convert("RGB")
        img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        inpaint_mask = np.zeros(img_cv.shape[:2], dtype=np.uint8)
        img_width, img_height = img_pil.size
        
        print("  🔤 Extracting Japanese text and Translating...")
        
        # ✅ FIX: Stripped down the JSON to only the bare essentials
        labelme_data = {"version": "5.1.1", "shapes": []}
        to_typeset = []

        for box, score, label in zip(final_boxes, final_scores, final_labels):
            x1, y1, x2, y2 = map(int, box)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_width, x2), min(img_height, y2)
            
            ocr_result = extract_text_from_region(img_pil, [x1, y1, x2, y2])
            extracted_text = ocr_result.get("text", "")
            
            roi_pil = img_pil.crop((x1, y1, x2, y2))
            img_roi_cv = cv2.cvtColor(np.array(roi_pil), cv2.COLOR_RGB2BGR)
            is_dark_bubble = np.mean(cv2.cvtColor(img_roi_cv, cv2.COLOR_BGR2GRAY)) < 128
            typeset_color = "white" if is_dark_bubble else "black"
            
            translated_text, should_erase = "", False
            
            if extracted_text and should_translate_category(label):
                if is_emotional_exclamation(extracted_text):
                    translated_text = extracted_text 
                    should_erase = True 
                elif extracted_text.strip():
                    trans_result = translate_text(extracted_text)
                    translated_text = clean_translation(trans_result.get("translated_text", ""))
                    should_erase = True
                    
                if should_erase:
                    cv2.rectangle(inpaint_mask, (max(0, x1-2), max(0, y1-2)), (min(img_width, x2+2), min(img_height, y2+2)), 255, -1)

            to_typeset.append(([x1, y1, x2, y2], translated_text, typeset_color, extracted_text))
            
            # ✅ FIX: Clean JSON append
            labelme_data["shapes"].append({
                "label": label, 
                "ocr_text": extracted_text, 
                "translated_text": translated_text, 
                "points": [[x1, y1], [x2, y2]], 
                "shape_type": "rectangle"
            })

        print("  🪄 Reconstructing background using LaMa AI...")
        final_img_pil = lama(img_pil, Image.fromarray(inpaint_mask).convert('L'))
        draw = ImageDraw.Draw(final_img_pil)

        print("  ✍️  Typesetting professional translations...")
        for box, translated_text, typeset_color, original_japanese in to_typeset:
            if translated_text: 
                is_safe = quality_assurance_check(original_japanese, translated_text)
                warning_color = None if is_safe else "red"
                wrap_text_in_box(draw, translated_text, box, font_path, text_color=typeset_color, force_outline_color=warning_color)

        # ✅ FIX: Change output filename to [original_name]_output.[ext]
        base_name, ext = os.path.splitext(image_filename)
        output_filename = f"{base_name}_output{ext}"
        
        final_img_pil.save(os.path.join(output_img_dir, output_filename))
        
        # Save JSON with original base name if output_json_dir is provided
        if output_json_dir and os.path.isdir(output_json_dir):
            with open(os.path.join(output_json_dir, base_name + ".json"), "w", encoding="utf-8") as f: 
                json.dump(labelme_data, f, indent=4, ensure_ascii=False)
        print(f"  ✅ Saved page.")

    print("\n✅ Japanese Processing complete!")