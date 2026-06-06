# Modular Pipelines, Consistent Naming & Relative Paths

Refactor the `color_model` project so that:
1. All 3 pipelines follow the `{language}_{role}.py` naming convention
2. Only the **Japanese pipeline** (the main pipeline) + router deps are installed by default
3. Chinese/Korean pipeline-specific deps are **lazily checked and installed on-demand** with user confirmation
4. All CWD-relative file paths become **script-relative** so the project works from any working directory

---

## User Review Required

> [!IMPORTANT]
> **File Renaming** — The Japanese pipeline files will be renamed to match the Chinese/Korean naming convention:
> - `predict_model.py` → `japanese_predict.py`
> - `custom_ocr.py` → `japanese_ocr.py`
> - `translator.py` → `japanese_translator.py`
> 
> The old files will be deleted. If anything else imports these by name (e.g., notebooks, scripts), those references will break.

> [!IMPORTANT]
> **Startup Flow Change** — Currently the "wipe AI memory?" prompt runs **before** language detection (and imports both Chinese + Korean translators eagerly). After this change, the memory prompt only appears **after** language is detected, and only for the relevant pipeline. This avoids importing Chinese/Korean modules when running Japanese.

> [!WARNING]
> **`requirements_ocr.txt` will be deleted** — It references `easyocr` and `deep-translator` which are no longer used anywhere in the codebase. It will be replaced by the new split requirements files.

---

## Open Questions

> [!IMPORTANT]
> **PaddleOCR as Base Dependency** — The language router uses PaddleOCR to detect the manga's language (Japanese/Chinese/Korean). This means PaddleOCR (~300-400 MB installed) is a base dependency even if you only ever process Japanese manga. Are you OK with this, or would you prefer a **"skip detection"** option that defaults to Japanese without needing PaddleOCR?

---

## Proposed Changes

### Component 1: Consistent File Naming

Rename the 3 Japanese pipeline files to match the `{language}_{role}.py` convention already used by Chinese and Korean.

#### [RENAME] `predict_model.py` → [japanese_predict.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/japanese_predict.py)
- Rename file, update internal imports: `from custom_ocr` → `from japanese_ocr`, `from translator` → `from japanese_translator`

#### [RENAME] `custom_ocr.py` → [japanese_ocr.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/japanese_ocr.py)
- Rename file only, no content changes needed

#### [RENAME] `translator.py` → [japanese_translator.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/japanese_translator.py)
- Rename file, fix the CWD-relative `sugoi_model_cache` path to be script-relative

#### [DELETE] `predict_model.py`, `custom_ocr.py`, `translator.py`
- Old files removed after renames

---

### Component 2: Dependency Manager

#### [NEW] [dependency_manager.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/dependency_manager.py)

A new module that defines the additional (non-base) dependencies per pipeline and provides:
- `check_missing_deps(pipeline_name)` — returns list of missing packages
- `prompt_and_install(pipeline_name)` — prints a summary table (package name, pip name, approximate download size, purpose), asks for user confirmation, and runs `pip install` if accepted

```
PIPELINE_DEPS = {
    "chinese": [
        {"import_name": "pypinyin", "pip_name": "pypinyin", "size": "~20 MB", "description": "Pinyin romanization fallback for untranslated Chinese characters"}
    ],
    "korean": [
        {"import_name": "korean_romanizer", "pip_name": "korean-romanizer", "size": "~1 MB", "description": "Korean romanization fallback for untranslated Hangul characters"}
    ]
}
```

---

### Component 3: Restructured Language Router

#### [MODIFY] [language_router.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/language_router.py)

**Current problem:** All 6 pipeline modules are eagerly imported at the top, which means:
- Chinese/Korean deps must be installed even if never used
- The memory-wipe prompt fires before language detection (unnecessary for Japanese)

**Changes:**
1. **Remove all top-level Chinese/Korean imports** (lines 15-16, 19-20)
2. **Keep Japanese import only**: `from japanese_predict import process_japanese_manga`
3. **Move `start_translation_session()`** to run **after** language detection, parameterized by detected language
4. **Add dependency checks** before Chinese/Korean pipeline execution:
   ```python
   elif detected_language == "chinese":
       from dependency_manager import prompt_and_install
       if not prompt_and_install("chinese"):
           return
       # Now safe to import
       from chinese_predict import process_chinese_manga
       from chinese_translator import reset_translation_context
       # Ask about memory wipe for Chinese only
       ...
   ```
5. **Lazy-import Chinese/Korean modules** only when the detected language requires them

**New `main()` flow:**
```
1. Select folders (file dialog)
2. Detect language (PaddleOCR shootout)
3. IF Japanese → run Japanese pipeline directly
4. IF Chinese/Korean →
   a. Check pipeline-specific deps → prompt to install if missing
   b. Ensure Ollama is running
   c. Ask about memory wipe (for this language only)
   d. Import and run the pipeline
```

---

### Component 4: Fix CWD-Relative Paths → Script-Relative

All 3 translator files use bare filenames like `"sugoi_model_cache"` or `"korean_glossary.json"` which resolve relative to whichever directory the user runs the script from. This breaks if you `cd` somewhere else.

**Fix pattern** (applied to all 3 files):
```python
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GLOSSARY_FILE = os.path.join(SCRIPT_DIR, "korean_glossary.json")
```

#### [MODIFY] [japanese_translator.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/japanese_translator.py) (formerly translator.py)
- `model_dir = "sugoi_model_cache"` → `model_dir = os.path.join(SCRIPT_DIR, "sugoi_model_cache")`

#### [MODIFY] [chinese_translator.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/chinese_translator.py)
- `GLOSSARY_FILE = "translation_glossary.json"` → `os.path.join(SCRIPT_DIR, "translation_glossary.json")`

#### [MODIFY] [korean_translator.py](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/korean_translator.py)
- `GLOSSARY_FILE = "korean_glossary.json"` → `os.path.join(SCRIPT_DIR, "korean_glossary.json")`

---

### Component 5: New Requirements Files

#### [NEW] [requirements_base.txt](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/requirements_base.txt)
Base + Japanese pipeline (always installed):
```
ultralytics
manga-ocr
simple-lama-inpainting
ctranslate2
sentencepiece
huggingface_hub
paddleocr
opencv-python
Pillow
numpy
torch
torchvision
requests
```

#### [NEW] [requirements_chinese.txt](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/requirements_chinese.txt)
```
pypinyin
```

#### [NEW] [requirements_korean.txt](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/requirements_korean.txt)
```
korean-romanizer
```

#### [DELETE] [requirements_ocr.txt](file:///c:/Users/tanay/OneDrive/Desktop/AiML/manga_translator/model/color_model/requirements_ocr.txt)
- References `easyocr` and `deep-translator` which are no longer used anywhere in the project

---

## Verification Plan

### Manual Verification
1. **Import check** — Run `python -c "from japanese_predict import process_japanese_manga"` from the `color_model` directory to confirm renames + import fixes work
2. **Dependency manager test** — Run `python -c "from dependency_manager import check_missing_deps; print(check_missing_deps('chinese'))"` to confirm it correctly detects missing `pypinyin`
3. **Path test** — Run `python -c "from japanese_translator import load_translation_model"` from a *different* working directory to confirm script-relative paths resolve correctly
4. **No broken imports** — Grep for any remaining references to old file names (`predict_model`, `custom_ocr`, `translator`) across the project
