import os
# 🛑 Stop the Paddle network check right at the start
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
# 🛡️ Globally disable the buggy oneDNN C++ accelerator
os.environ["FLAGS_use_mkldnn"] = "0"

import sys
import time
import subprocess
import requests
from tkinter import Tk, filedialog

from PIL import Image
import numpy as np

# 🔌 Import the dependency manager for lazy pipeline loading
from dependency_manager import prompt_and_install

# Dictionary to hold our three OCR models so they only load once
_ocr_models = {}

def get_ocr_model(lang_code):
    if lang_code not in _ocr_models:
        print(f"🔍 Loading {lang_code.upper()} Scanner (CPU Mode)...")
        try:
            from paddleocr import PaddleOCR
            _ocr_models[lang_code] = PaddleOCR(use_angle_cls=False, lang=lang_code, show_log=False, use_gpu=False)
        except Exception as e:
            print(f"⚠️ Skipping {lang_code.upper()} scanner (dependencies not installed or module missing: {e})")
            _ocr_models[lang_code] = None
    return _ocr_models[lang_code]

# ==========================================
# 🌟 OLLAMA AUTO-BOOT SEQUENCE
# ==========================================
def ensure_ollama_running():
    print("\n🔍 Checking if Ollama AI engine is awake...")
    try:
        # Just try to knock on Ollama's front door
        response = requests.get("http://localhost:11434/")
        if response.status_code == 200:
            print("✅ Ollama is already running!")
            return True
    except requests.exceptions.ConnectionError:
        # If it fails, the door is closed. Time to boot it up!
        print("⏳ Ollama is sleeping. Booting it up in the background...")
        try:
            # This silently runs "ollama serve" as a background process without opening a new window
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Give the server 3 seconds to fully initialize
            for i in range(3, 0, -1):
                print(f"   Warming up engine... {i}")
                time.sleep(1)
                
            print("✅ Ollama booted successfully!")
            return True
        except Exception as e:
            print(f"❌ Failed to start Ollama automatically. Make sure it's installed. Error: {e}")
            return False

# ==========================================
# 🌟 THE INTERACTIVE MEMORY PROMPT
# ==========================================
def start_translation_session(detected_language):
    """Only resets memory for the detected pipeline. Called AFTER language detection."""
    
    # Japanese uses Sugoi (stateless) — no persistent memory to wipe
    if detected_language == "japanese":
        return
    
    print("\n" + "="*50)
    print("📖 TRANSLATION MEMORY MANAGEMENT")
    print("="*50)
    
    user_choice = input("Are you starting a NEW manga? Do you want to wipe the AI's memory? (y/n): ").strip().lower()
    
    if user_choice == 'y':
        if detected_language == "chinese":
            from chinese_translator import reset_translation_context
            reset_translation_context()
        elif detected_language == "korean":
            from korean_translator import reset_translation_context
            reset_translation_context()
        print("✅ AI Memory wiped! Starting completely fresh.")
    else:
        print("⏭️ Keeping existing memory. Continuing the previous story...")
        
    print("="*50 + "\n")

# ==========================================
# 🌟 THE SPLASH-ART SAFE SHOOTOUT
# ==========================================
def identify_manga_language(input_dir):
    image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
    image_files.sort() 
    
    if not image_files:
        print("❌ No images found in the selected folder.")
        return "unknown"
        
    languages = {'japan': 'japanese', 'ch': 'chinese', 'korean': 'korean'}
    confidence_totals = {'japanese': 0.0, 'chinese': 0.0, 'korean': 0.0}
    word_counts = {'japanese': 0, 'chinese': 0, 'korean': 0}
    
    valid_pages_checked = 0
    pages_to_check = 5
    
    print(f"\n📖 Running Confidence Shootout (Looking for {pages_to_check} valid text pages)...")
    
    for img_name in image_files:
        img_path = os.path.join(input_dir, img_name)
        img = Image.open(img_path).convert('RGB')
        img_array = np.array(img)[:, :, ::-1]
        
        page_has_text = False
        
        for lang_code, lang_name in languages.items():
            ocr = get_ocr_model(lang_code)
            if ocr is None:
                continue
                
            result = ocr.ocr(img_array, cls=False)
            
            if result and result[0]:
                for line in result[0]:
                    confidence = float(line[1][1])
                    text = line[1][0].strip()
                    if text:
                        confidence_totals[lang_name] += confidence
                        word_counts[lang_name] += 1
                        page_has_text = True

        if not page_has_text:
            print(f"⏭️ Skipping {img_name} (No text found - likely Splash Art)")
            continue
            
        valid_pages_checked += 1
        print(f"✅ Analyzed valid page {valid_pages_checked}/{pages_to_check} ({img_name})")
        
        if valid_pages_checked >= pages_to_check:
            break

    averages = {}
    for lang_name in confidence_totals:
        if word_counts[lang_name] > 0:
            averages[lang_name] = confidence_totals[lang_name] / word_counts[lang_name]
        else:
            averages[lang_name] = 0.0

    print("\n📊 Confidence Shootout Results:")
    for lang, score in averages.items():
        print(f"  - {lang.capitalize()}: {score*100:.1f}% confidence (found {word_counts[lang]} text blocks)")

    best_language = max(averages, key=averages.get)
    if averages[best_language] == 0.0:
        print("⚠️ No readable text found in any of the checked pages.")
        return "unknown"
        
    return best_language

def main():
    print("\n" + "="*50)
    print("📖 MANGA TRANSLATION PIPELINE")
    print("="*50)
    
    print("🚀 Starting Manga Translation Pipeline...")
    
    root = Tk()
    root.withdraw()
    
    print("\n📂 Please select your input and output folders...")
    input_dir = filedialog.askdirectory(title="Select Input Folder (Images)")
    if not input_dir:
        print("❌ No input folder selected. Exiting.")
        return
        
    output_img_dir = filedialog.askdirectory(title="Select Output Folder (Images)")
    output_json_dir = filedialog.askdirectory(title="Select Output Folder (JSON)")
    
    if not all([input_dir, output_img_dir, output_json_dir]):
        print("❌ Missing output folders. Exiting.")
        return

    # ==========================================
    # 🌟 STEP 1: DETECT LANGUAGE
    # ==========================================
    detected_language = identify_manga_language(input_dir)
    print(f"\n🌍 Winning Language: {detected_language.upper()}")

    # ==========================================
    # 🌟 STEP 2: ROUTE TO THE CORRECT PIPELINE
    # ==========================================
    if detected_language == "japanese":
        print("➡️ Routing to Japanese Pipeline...")
        # Japanese doesn't use Ollama or persistent memory, so just run it directly
        process_japanese_manga(input_dir, output_img_dir, output_json_dir)
        
    elif detected_language == "chinese":
        print("➡️ Routing to Chinese Pipeline...")
        
        # 🔌 Step 2a: Check for Chinese-specific dependencies
        if not prompt_and_install("chinese"):
            return
        
        # 🤖 Step 2b: Ensure the LLM backend is awake
        ensure_ollama_running()
        
        # 🧠 Step 2c: Ask about memory wipe (Chinese only)
        start_translation_session("chinese")
        
        # 🚀 Step 2d: Lazy-import and run the Chinese pipeline
        from chinese_predict import process_chinese_manga
        process_chinese_manga(input_dir, output_img_dir, output_json_dir)
        
    elif detected_language == "korean":
        print("➡️ Routing to Korean Pipeline...")
        
        # 🔌 Step 2a: Check for Korean-specific dependencies
        if not prompt_and_install("korean"):
            return
        
        # 🤖 Step 2b: Ensure the LLM backend is awake
        ensure_ollama_running()
        
        # 🧠 Step 2c: Ask about memory wipe (Korean only)
        start_translation_session("korean")
        
        # 🚀 Step 2d: Lazy-import and run the Korean pipeline
        from korean_predict import process_korean_manhwa
        process_korean_manhwa(input_dir, output_img_dir, output_json_dir)
        
    else:
        print("❌ Could not confidently determine language. Please check the images.")

if __name__ == "__main__":
    main()