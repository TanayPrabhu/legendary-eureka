import numpy as np
import re

_korean_ocr_instance = None

def get_korean_ocr_instance():
    global _korean_ocr_instance
    if _korean_ocr_instance is None:
        from paddleocr import PaddleOCR
        import logging
        logging.getLogger("ppocr").setLevel(logging.ERROR)
        print("🧠 Booting PaddleOCR (Korean Webtoon Model)...")
        _korean_ocr_instance = PaddleOCR(use_angle_cls=True, lang="korean", use_gpu=False, show_log=False)
    return _korean_ocr_instance

def sanitize_ocr_text(raw_text):
    """🛡️ THE SANITIZER: Cleans up PaddleOCR's background noise hallucinations."""
    clean_text = re.sub(r'[\[\]\{\}\+\-\=\_\*\|\^\~\\]', ' ', raw_text)
    clean_text = re.sub(r'\b[a-zA-Z]{1,3}\b', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def extract_text_from_region(image_pil, box):
    roi_pil = image_pil.crop(box)
    img_array = np.array(roi_pil)
    img_array = img_array[:, :, ::-1] 
    
    ocr = get_korean_ocr_instance()
    
    try:
        result = ocr.ocr(img_array, cls=True)
        text_segments = []
        
        if result and result[0]:
            lines = result[0]   
            
            # Sorting logic for Webtoons (Mostly Horizontal)
            sorted_lines = sorted(lines, key=lambda line_box: min([pt[1] for pt in line_box[0]]), reverse=False)
                
            for line in sorted_lines:
                extracted_string = line[1][0]
                text_segments.append(extracted_string)
                
        # Korean uses spaces!
        raw_text = " ".join(text_segments).strip()
        final_text = sanitize_ocr_text(raw_text)
            
        return {"text": final_text, "status": "success"}
        
    except Exception as e:
        return {"text": "", "status": "error", "message": str(e)}