import os
import sys
import shutil
import json
import cv2
import pytesseract
from PIL import Image
import numpy as np
import re
import difflib

def get_tesseract_cmd():
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd and os.path.exists(env_cmd):
        return env_cmd
    for p in ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]:
        if os.path.exists(p):
            return p
    path_which = shutil.which("tesseract")
    if path_which:
        return path_which
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        win_paths.append(os.path.join(local_app, "Programs", "Tesseract-OCR", "tesseract.exe"))
    user_prof = os.environ.get("USERPROFILE")
    if user_prof:
        win_paths.append(os.path.join(user_prof, "AppData", "Local", "Programs", "Tesseract-OCR", "tesseract.exe"))
    for p in win_paths:
        if os.path.exists(p):
            return p
    return None

tess_path = get_tesseract_cmd()
if tess_path:
    pytesseract.pytesseract.tesseract_cmd = tess_path

def sanitize_ocr_text(raw_text):
    if not raw_text:
        return ""
    preserve_keywords = [
        'mrp', 'maximum', 'retail', 'price', 'net', 'qty', 'quantity', 'weight', 'wt',
        'mfg', 'mfd', 'pkg', 'pkd', 'packed', 'manufactured', 'date', 'use',
        'best', 'before', 'expiry', 'exp', 'batch', 'lot', 'unit', 'sale',
        'incl', 'taxes', 'tax', 'rs', 'inr', 'consumer', 'customer', 'care',
        'helpline', 'email', 'phone', 'toll', 'address', 'office', 'marketed',
        'imported', 'packer', 'complaint', 'feedback', 'contact', 'pvt', 'ltd',
        'fssai', 'lic', 'no', 'gram', 'gms', 'kg', 'ml', 'l', 'litre', 'servings',
        'country', 'origin', 'made', 'india'
    ]
    lines = raw_text.split('\n')
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        stripped = re.sub(r'^[^\x00-\x7F]+|[^\x00-\x7F]+$', '', stripped).strip()
        stripped = re.sub(r'[\=\_\~\`\|\^\*\#]+', ' ', stripped).strip()
        if not stripped or len(stripped) < 2:
            continue
        lower = stripped.lower()
        has_keyword = any(kw in lower for kw in preserve_keywords)
        has_dates = bool(re.search(r'\d{1,2}[/\-.]\d{1,2}|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b|\d{1,2}[/\-]\d{2,4}', lower))
        has_prices = bool(re.search(r'rs\.?|₹|\d+\.\d{2}|\d+\s*/\-|\d+\s*\(incl', lower))
        has_numeric = bool(re.search(r'\d{2,}', lower))
        if has_keyword or has_dates or has_prices or has_numeric:
            cleaned_lines.append(stripped)
        elif len(stripped) >= 4 and sum(1 for c in stripped if c.isalnum()) >= 3:
            cleaned_lines.append(stripped)
    seen = set()
    deduped = []
    for line in cleaned_lines:
        normalized = re.sub(r'\s+', ' ', line.lower()).strip()
        if normalized not in seen and len(normalized) > 1:
            seen.add(normalized)
            deduped.append(line)
    return '\n'.join(deduped).strip()

def preprocess_and_extract(image_path, lang_str='eng'):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("Image file could not be loaded or is corrupted.")
    orig_h, orig_w = img.shape[:2]
    target_dim = 1200
    scale = 1.0
    if max(orig_h, orig_w) > target_dim or max(orig_h, orig_w) < 600:
        scale = target_dim / float(max(orig_h, orig_w))
        img = cv2.resize(img, (int(orig_w * scale), int(orig_h * scale)), interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    cfg_std = r'--oem 3 --psm 6'
    t1 = pytesseract.image_to_string(enhanced, config=cfg_std, lang=lang_str)
    return t1, enhanced, scale, orig_w, orig_h

def load_patterns():
    patterns = {
        "MRP": ["mrp", "maximum retail price", "retail price", "m.r.p.", "rs.", "₹", "rs"],
        "NetQuantity": ["net qty", "net quantity", "net weight", "net wt", "net content", "quantity", "net weight/qty"],
        "MfgDate": ["mfg", "pkg", "packed", "manufactured", "pkd", "mfg date", "pkg date", "mfd"],
        "Manufacturer": ["mfg by", "manufactured by", "packed by", "packer", "importer", "marketed by", "manufactured & marketed by", "pvt. ltd.", "village", "district", "regd. office"],
        "ConsumerCare": ["consumer care", "customer care", "helpline", "email", "phone", "contact", "consumer service", "pincode", "feedback"]
    }
    if os.path.exists("rules.json"):
        try:
            with open("rules.json", "r") as f:
                rules = json.load(f)
            mand_rules = rules.get("mandatory_declarations", {})
            for key, val in mand_rules.items():
                pats = val.get("patterns", [])
                if pats and key in patterns:
                    patterns[key] = list(set(patterns[key] + pats))
        except Exception:
            pass
    return patterns

def are_words_near(w1, w2, max_h_dist=150, max_v_dist=25):
    v_dist = abs(w1['top'] - w2['top'])
    if v_dist > max_v_dist:
        return False
    h_dist = max(0, w2['left'] - (w1['left'] + w1['width']), w1['left'] - (w2['left'] + w2['width']))
    return h_dist <= max_h_dist

def fuzzy_match_in_line(pattern, line_text, threshold=0.75):
    if pattern.lower() in line_text.lower():
        idx = line_text.lower().find(pattern.lower())
        return idx, len(pattern)
    words = line_text.split()
    pat_words = pattern.lower().split()
    pat_len = len(pat_words)
    if pat_len > 1:
        for idx in range(len(words) - pat_len + 1):
            window = " ".join(words[idx:idx+pat_len])
            ratio = difflib.SequenceMatcher(None, window.lower(), pattern.lower()).ratio()
            if ratio >= threshold:
                char_idx = line_text.lower().find(window.lower())
                if char_idx != -1:
                    return char_idx, len(window)
    else:
        for w in words:
            ratio = difflib.SequenceMatcher(None, w.lower(), pattern.lower()).ratio()
            if ratio >= threshold:
                char_idx = line_text.lower().find(w.lower())
                if char_idx != -1:
                    return char_idx, len(w)
    return -1, 0

_cached_lang_str = None

def extract_text(image_path, original_filename=None):
    global _cached_lang_str
    if not os.path.exists(image_path):
        return {"text": f"[ERROR] File not found: {os.path.basename(image_path)}", "boxes": {}, "width": 0, "height": 0}
    try:
        if _cached_lang_str is None:
            try:
                available_langs = pytesseract.get_languages()
                _cached_lang_str = 'eng+hin' if 'hin' in available_langs else 'eng'
            except Exception:
                _cached_lang_str = 'eng'
        lang_str = _cached_lang_str
        raw_text, enhanced_img, scale, orig_w, orig_h = preprocess_and_extract(image_path, lang_str)
        clean_text = sanitize_ocr_text(raw_text)
        if not clean_text:
            clean_text = "[NO TEXT DETECTED] Please upload a clearer image label."
        ocr_data = pytesseract.image_to_data(Image.fromarray(enhanced_img), config='--oem 3 --psm 6', lang=lang_str, output_type=pytesseract.Output.DICT)
        all_words = []
        words_by_line = {}
        for i in range(len(ocr_data['text'])):
            text_word = ocr_data['text'][i].strip()
            if not text_word:
                continue
            left = int(ocr_data['left'][i] / scale)
            top = int(ocr_data['top'][i] / scale)
            width = int(ocr_data['width'][i] / scale)
            height = int(ocr_data['height'][i] / scale)
            word_info = {
                "text": text_word,
                "left": left,
                "top": top,
                "width": width,
                "height": height,
                "block": ocr_data.get('block_num', [0]*len(ocr_data['text']))[i],
                "paragraph": ocr_data.get('par_num', [0]*len(ocr_data['text']))[i],
                "line": ocr_data.get('line_num', [0]*len(ocr_data['text']))[i],
                "index": len(all_words)
            }
            all_words.append(word_info)
            line_key = (word_info["block"], word_info["paragraph"], word_info["line"])
            if line_key not in words_by_line:
                words_by_line[line_key] = []
            words_by_line[line_key].append(word_info)
        sorted_lines = []
        for line_key, line_words in words_by_line.items():
            line_words.sort(key=lambda w: w["left"])
            line_text = " ".join(w["text"] for w in line_words)
            line_top = min(w["top"] for w in line_words)
            sorted_lines.append({"line_key": line_key, "words": line_words, "text": line_text, "top": line_top})
        sorted_lines.sort(key=lambda l: l["top"])
        patterns_dict = load_patterns()
        boxes = {}
        for decl_type, patterns in patterns_dict.items():
            matched_words = []
            for line in sorted_lines:
                line_text_lower = line["text"].lower()
                matched_pat_len = 0
                start_char = -1
                for pat in patterns:
                    idx, match_len = fuzzy_match_in_line(pat, line_text_lower)
                    if idx != -1:
                        start_char = idx
                        matched_pat_len = match_len
                        break
                if start_char != -1:
                    end_char = start_char + matched_pat_len
                    char_to_word = []
                    for w in line["words"]:
                        for _ in range(len(w["text"])):
                            char_to_word.append(w)
                        char_to_word.append(None)
                    for c_idx in range(start_char, min(end_char, len(char_to_word))):
                        w = char_to_word[c_idx]
                        if w and w not in matched_words:
                            matched_words.append(w)
                    if matched_words:
                        break
            if matched_words:
                merged_indices = {w["index"] for w in matched_words}
                added = True
                while added:
                    added = False
                    for w in all_words:
                        if w["index"] in merged_indices:
                            continue
                        for m_idx in list(merged_indices):
                            if are_words_near(all_words[m_idx], w):
                                merged_indices.add(w["index"])
                                added = True
                                break
                boxes[decl_type] = {
                    "x": min(all_words[idx]["left"] for idx in merged_indices),
                    "y": min(all_words[idx]["top"] for idx in merged_indices),
                    "width": max(all_words[idx]["left"] + all_words[idx]["width"] for idx in merged_indices) - min(all_words[idx]["left"] for idx in merged_indices),
                    "height": max(all_words[idx]["top"] + all_words[idx]["height"] for idx in merged_indices) - min(all_words[idx]["top"] for idx in merged_indices)
                }
            else:
                boxes[decl_type] = None
        return {"text": clean_text, "boxes": boxes, "width": orig_w, "height": orig_h}
    except Exception as e:
        return {"text": f"[ERROR] OCR processing failed: {str(e)}", "boxes": {}, "width": 0, "height": 0}
