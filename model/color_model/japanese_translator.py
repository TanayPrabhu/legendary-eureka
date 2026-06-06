import os
import re
import logging
import ctranslate2
import sentencepiece as spm
from huggingface_hub import snapshot_download

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)

_translator = None
_sp_source = None
_sp_target = None

# --- PRE-PROCESSING DICTIONARY ---
SFX_AND_FRAGMENTS = {
    "？！！": "?!!",
    "！！": "!!",
    "こーーッ": "*Staaare*",
    "どうっ": "*Thud*",
    "くん♡": "*Sniff* ♡",
    "つー": "*Turn*",
    "ドキドキ": "*Thump thump*",
    "シーン": "*Silence*",
    "ゴゴゴゴ": "*Rumble*",
    "ドン": "*Bam*",
    "ガチャ": "*Click*",
    "キィィィ": "*Creeeak*",
    "フッ": "*Heh*",
    "はぁ？": "Huh?",
    "やっぱ": "As expected..."  
}

def clean_japanese_ocr(text):
    """Cleans text and checks against the lookup table before translation."""
    if not text:
        return "", True

    clean_key = text.strip()
    if clean_key in SFX_AND_FRAGMENTS:
        return SFX_AND_FRAGMENTS[clean_key], True

    text = re.sub(r'[\s\u3000]+', '', text) 
    text = re.sub(r'！+', '！', text)         
    text = re.sub(r'？+', '？', text)         
    text = re.sub(r'!+', '!', text)           
    text = re.sub(r'\?+', '?', text)          
    
    return text, False

def load_translation_model():
    global _translator, _sp_source, _sp_target
    if _translator is not None:
        return

    # Hugging Face repository containing the CTranslate2 Sugoi v4 model
    repo_id = "entai2965/sugoi-v4-ja-en-ctranslate2"
    model_dir = os.path.join(SCRIPT_DIR, "sugoi_model_cache")
    
    # Auto-download the model if it hasn't been downloaded yet
    if not os.path.exists(model_dir):
        logger.info(f"⬇️ Downloading Sugoi CTranslate2 model from Hugging Face (~1.1 GB)... This only happens once.")
        snapshot_download(repo_id=repo_id, local_dir=model_dir)
    else:
        logger.info(f"📂 Found cached Sugoi model in '{model_dir}'.")

    logger.info("🌐 Loading Sugoi CTranslate2 Model onto GPU...")
    
    # Load SentencePiece tokenizers from the downloaded 'spm' folder
    sp_source_model = os.path.join(model_dir, "spm", "spm.ja.nopretok.model")
    sp_target_model = os.path.join(model_dir, "spm", "spm.en.nopretok.model")
    
    _sp_source = spm.SentencePieceProcessor()
    _sp_source.load(sp_source_model)
    
    _sp_target = spm.SentencePieceProcessor()
    _sp_target.load(sp_target_model)

    # Load CTranslate2 model for fast execution
    _translator = ctranslate2.Translator(model_dir, device="cuda", compute_type="int8_float16")
    logger.info("✅ Model loaded successfully.")

def translate_text(text, target_lang='en'):
    if not text or not text.strip():
        return {"translated_text": ""}

    processed_text, skip_model = clean_japanese_ocr(text)
    
    if skip_model:
        return {"translated_text": processed_text}
        
    if not processed_text:
        return {"translated_text": ""}

    load_translation_model()

    # Encode text into SentencePiece tokens
    source_tokens = _sp_source.encode(processed_text, out_type=str)

    # Translate using CTranslate2
    results = _translator.translate_batch(
        [source_tokens], 
        beam_size=5 
    )
    
    target_tokens = results[0].hypotheses[0]
    
    # Decode the tokens back into an English string
    translated_text = _sp_target.decode(target_tokens)

    # Clean up any potential artifacts from the decoding process
    translated_text = translated_text.replace('⁇', '').strip()

    return {"translated_text": translated_text}

def should_translate_category(label, translate_all=False):
    if translate_all: return True
    return label.lower() in ['speech bubble', 'thought bubble']