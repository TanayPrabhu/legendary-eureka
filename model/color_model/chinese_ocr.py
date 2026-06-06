import numpy as np
import re

_chinese_ocr_instance = None

def get_chinese_ocr_instance():
    global _chinese_ocr_instance
    if _chinese_ocr_instance is None:
        from paddleocr import PaddleOCR
        import logging
        logging.getLogger("ppocr").setLevel(logging.ERROR)
        # CPU Mode, optimized for Chinese Manhua
        _chinese_ocr_instance = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
    return _chinese_ocr_instance

def extract_text_from_region(image_pil, box):
    roi_pil = image_pil.crop(box)
    img_array = np.array(roi_pil)
    # Convert RGB to BGR for PaddleOCR
    img_array = img_array[:, :, ::-1] 
    
    ocr = get_chinese_ocr_instance()
    
    try:
        # Angle Classifier ON
        result = ocr.ocr(img_array, cls=True)
        text_segments = []
        
        if result and result[0]:
            lines = result[0]   
            
            # ✅ STEP 1: Vote on the orientation of the text inside the bubble
            vertical_votes = 0
            horizontal_votes = 0
            for line in lines:
                box_coords = line[0] # The 4 corners of the detected text line
                x_coords = [pt[0] for pt in box_coords]
                y_coords = [pt[1] for pt in box_coords]
                width = max(x_coords) - min(x_coords)
                height = max(y_coords) - min(y_coords)
                
                # If it's noticeably taller than it is wide, it's vertical
                if height > width * 1.2:
                    vertical_votes += 1
                else:
                    horizontal_votes += 1
                    
            is_vertical = vertical_votes >= horizontal_votes
            
            # ✅ STEP 2: Sort based on the winning orientation
            if is_vertical:
                # Vertical: Sort Right-to-Left (Highest X coordinate first)
                sorted_lines = sorted(lines, key=lambda line_box: max([pt[0] for pt in line_box[0]]), reverse=True)
            else:
                # Horizontal: Sort Top-to-Bottom (Lowest Y coordinate first)
                sorted_lines = sorted(lines, key=lambda line_box: min([pt[1] for pt in line_box[0]]), reverse=False)
                
            # Extract the strings
            for line in sorted_lines:
                extracted_string = line[1][0]
                text_segments.append(extracted_string)
                
        final_text = "".join(text_segments).strip()
        
        # ✅ STEP 3: Cleanup Filter (Destructive Regex removed!)
        if final_text:
            # We only strip spaces because Chinese text shouldn't have them. 
            # Qwen 2.5 will natively handle all punctuation and typo corrections!
            final_text = final_text.replace(" ", "")
            
        return {"text": final_text, "status": "success"}
        
    except Exception as e:
        return {"text": "", "status": "error", "message": str(e)}