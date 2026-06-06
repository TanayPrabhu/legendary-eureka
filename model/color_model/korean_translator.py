import logging
import requests
import json 
import re 
import os
import unicodedata
from korean_romanizer.romanizer import Romanizer

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)8s] %(filename)s:%(lineno)d - %(message)s'))
    logger.addHandler(handler)

chat_history = []
MAX_HISTORY_PAIRS = 10 
GLOSSARY_FILE = os.path.join(SCRIPT_DIR, "korean_glossary.json")
glossary_cache = {}

KOREAN_REGEX = r'[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7A3]'

def load_glossary():
    global glossary_cache
    if os.path.exists(GLOSSARY_FILE):
        try:
            with open(GLOSSARY_FILE, "r", encoding="utf-8") as f:
                glossary_cache = json.load(f)
        except Exception:
            glossary_cache = {}
    else:
        glossary_cache = {}
        # Automatically generate the empty file on first boot
        save_glossary()

def save_glossary():
    with open(GLOSSARY_FILE, "w", encoding="utf-8") as f:
        json.dump(glossary_cache, f, ensure_ascii=False, indent=4)

def ask_wipe_memory():
    ans = input("🛑 Are you starting a NEW Webtoon? Do you want to wipe the AI's memory? (y/n): ").strip().lower()
    if ans == 'y':
        logger.info("🧹 Wiping persistent glossary memory for a fresh slate...")
        global glossary_cache
        glossary_cache = {}
        save_glossary()

load_glossary()

def clean_json_string(raw_str):
    return re.sub(r'^```json\s*|\s*```$', '', raw_str, flags=re.MULTILINE).strip()

def strip_accents(text):
    try:
        return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    except Exception:
        return text

def convert_surviving_korean_to_roman(text):
    def replace_with_roman(match):
        char = match.group(0)
        try:
            r = Romanizer(char)
            return f" {r.romanize()} "
        except:
            return char
    
    text_with_roman = re.sub(KOREAN_REGEX, replace_with_roman, text)
    return strip_accents(re.sub(r'\s+', ' ', text_with_roman).strip())

def reset_translation_context():
    global chat_history
    logger.info("🧠 Initializing Webtoon Translation Agent Context...")
    
    system_prompt = f"""You are an expert Korean webtoon translator. 
Translate the provided JSON of Korean text into natural English slang based on the ongoing story.

CRITICAL INSTRUCTIONS:
1. Contextual Naming (Adjacency Rule):
   - If you see adjacent Korean names (Surname + Given Name), it is a human. You MUST use standard Phonetic Romanization (e.g., '성진우' -> 'Sung Jinwoo').
   - ONLY use Semantic Translation for standalone descriptive titles or guild names (e.g., '백호' -> 'White Tiger').
2. NO KOREAN CHARACTERS: Output 100% standard English letters. Do NOT use accents or macrons.
3. OFFICIAL MEMORY GLOSSARY: You MUST use these exact established names for consistency:
{json.dumps(glossary_cache, ensure_ascii=False, indent=2)}

OUTPUT SCHEMA:
You MUST respond ONLY with a JSON object containing TWO keys:
- "new_names_found": A dictionary of any new characters/titles discovered in this batch and their English translation.
- "translations": A dictionary mapping the input numerical keys to the translated English text.
DO NOT add any conversational text or notes.
"""
    chat_history = [{"role": "system", "content": system_prompt}]

def translate_text_batch(text_list):
    global chat_history, glossary_cache
    
    if not text_list:
        return []

    if not chat_history:
        reset_translation_context()

    input_dict = {str(i+1): text for i, text in enumerate(text_list)}
    chat_history.append({"role": "user", "content": json.dumps(input_dict, ensure_ascii=False)})

    payload = {
        "model": "qwen2.5:3b",
        "messages": chat_history,
        "format": "json",       
        "stream": False,
        "options": {"temperature": 0.3}
    }

    try:
        logger.info(f"🧠 [Phase 1] Qwen 2.5 translating {len(text_list)} lines...")
        response = requests.post("http://localhost:11434/api/chat", json=payload)
        response.raise_for_status()
        
        raw_output = clean_json_string(response.json().get("message", {}).get("content", ""))
        draft_json = json.loads(raw_output)
        
        chat_history.append({"role": "assistant", "content": raw_output})
        if len(chat_history) > (MAX_HISTORY_PAIRS * 2) + 1:
            chat_history = [chat_history[0]] + chat_history[-(MAX_HISTORY_PAIRS * 2):]

        # 🌟 THE BOUNCER
        new_names = draft_json.get("new_names_found", {})
        valid_new_names = {}
        rejected_junk = [] 
        
        for k, v in new_names.items():
            if isinstance(k, str) and len(k) < 7 and not re.search(r'[^\w\s]', k):
                valid_new_names[k] = v
            else:
                if isinstance(v, str):
                    rejected_junk.append(v)
                
        if valid_new_names:
            logger.info(f"💾 Added {len(valid_new_names)} new names to memory.")
            glossary_cache.update(valid_new_names)
            save_glossary()

        translations = draft_json.get("translations", draft_json)

        # 🌟 PHASE 2: CONTEXT-AWARE VALIDATOR (Surgical Fix)
        failed_items = {}
        for key, text in translations.items():
            if isinstance(text, str):
                has_asian_chars = bool(re.search(KOREAN_REGEX, text))
                is_hallucinated = any(junk in text for junk in rejected_junk if junk)

                if has_asian_chars or is_hallucinated:
                    failed_items[key] = {
                        "original_korean": input_dict.get(key, ""),
                        "flawed_draft": text
                    }

        if failed_items:
            logger.warning(f"⚠️ Caught {len(failed_items)} flawed lines! Executing Surgical Correction...")
            
            correction_prompt = (
                "You are a strict Error Correction AI for webtoon translation. "
                "The previous AI failed by leaving unauthorized Korean characters or hallucinated names in the 'flawed_draft'. "
                "I am providing the 'original_korean' for context, alongside the 'flawed_draft'.\n\n"
                "ERROR FIXING PROTOCOL:\n"
                "1. Total Failure: If the 'flawed_draft' is entirely Korean or nonsensical, translate the 'original_korean' completely into natural English.\n"
                "2. Partial Failure (Surgical Fix): If the 'flawed_draft' contains Korean characters amidst correct English, DO NOT ALTER the existing English text. "
                "   - If the Korean word is a translatable word (e.g., '형' -> 'bro/hyung', '괴물' -> 'monster'), you MUST translate it into English.\n"
                "   - ONLY use phonetic Romanization if the Korean word is a character's proper name.\n"
                "3. NAME RULE: When converting names phonetically, use standard ASCII letters ONLY. No accents.\n\n"
                "Output ONLY a flat JSON object mapping the same numerical keys directly to the fully corrected English strings."
            )

            correction_payload = {
                "model": "qwen2.5:3b",
                "messages": [
                    {"role": "system", "content": correction_prompt},
                    {"role": "user", "content": json.dumps(failed_items, ensure_ascii=False)}
                ],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.1}
            }

            try:
                corr_resp = requests.post("http://localhost:11434/api/chat", json=correction_payload)
                corr_resp.raise_for_status()
                
                raw_corr = clean_json_string(corr_resp.json().get("message", {}).get("content", ""))
                corr_json = json.loads(raw_corr)
                
                for k, v in corr_json.items():
                    if isinstance(v, str):
                        translations[k] = v
            except Exception as e:
                logger.error(f"❌ Validator correction pass failed: {e}")

        # 🌟 PHASE 3: EXTRACTION & ROMANIZATION SHIELD
        translated_list = []
        for i in range(len(text_list)):
            key = str(i+1)
            final_text = translations.get(key, "")
            
            if isinstance(final_text, dict):
                salvaged_str = ""
                for v in final_text.values():
                    if isinstance(v, str):
                        salvaged_str = v
                        break
                final_text = salvaged_str if salvaged_str else final_text.get("final", "")

            if not isinstance(final_text, str):
                final_text = str(final_text)

            final_text = strip_accents(final_text)

            if re.search(KOREAN_REGEX, final_text):
                logger.error(f"🛡️ ROMANIZATION SHIELD ACTIVATED: Converting surviving Korean in Bubble {key}!")
                final_text = convert_surviving_korean_to_roman(final_text)
                
                if not final_text.strip():
                    final_text = "..."
                
            translated_list.append(final_text)
            
        return translated_list
        
    except Exception as e:
        logger.error(f"❌ LLM Pipeline failed: {e}")
        if chat_history and chat_history[-1]["role"] == "user":
            chat_history.pop() 
        return [""] * len(text_list)