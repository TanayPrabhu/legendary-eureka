import os
import torch
from manga_ocr import MangaOcr
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

_manga_ocr = None

def get_manga_ocr_instance():
    global _manga_ocr
    if _manga_ocr is not None:
        return _manga_ocr
    logger.info("🔤 Initializing MangaOCR...")
    _manga_ocr = MangaOcr()
    return _manga_ocr

def preprocess_for_ocr(roi_pil):
    """
    Enhances the image to make text sharper and more distinct from the background.
    """
    # 1. Convert to Grayscale
    img = ImageOps.grayscale(roi_pil)
    
    # 2. Increase Contrast: Makes the blacks blacker and whites whiter
    # This helps remove the 'fuzzy' gray artifacts around JPEG text
    img = ImageOps.autocontrast(img, cutoff=2)
    
    # 3. Subtle Sharpening: Helps define the edges of complex kanji strokes
    img = img.filter(ImageFilter.SHARPEN)
    
    return img

def detect_inverted_roi(roi_pil):
    # Convert to grayscale numpy for mean calculation
    gray_roi = np.array(ImageOps.grayscale(roi_pil))
    return np.mean(gray_roi) < 128

def extract_text_from_region(image_pil, box):
    # Crop the initial region
    roi_pil = image_pil.crop(box)
    
    # Handle inverted (dark) bubbles first
    if detect_inverted_roi(roi_pil):
        roi_pil = ImageOps.invert(roi_pil.convert("RGB"))
    
    # Apply the new preprocessing steps
    roi_pil = preprocess_for_ocr(roi_pil)
    
    ocr = get_manga_ocr_instance()
    try:
        text = ocr(roi_pil)
        return {"text": " ".join(text.split()).strip(), "status": "success"}
    except Exception as e:
        return {"text": "", "status": "error", "message": str(e)}