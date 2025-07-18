from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from typing import List, Dict
import jieba
from pypinyin import lazy_pinyin, Style
import re
import os
import json
import asyncio
from functools import lru_cache
import time
import gc

app = FastAPI(root_path="/api/chinese")

# Thêm middleware để tối ưu hóa
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=500)  # Giảm minimum size

# =========================
# 1. TỪ ĐIỂN CC-CEDICT + CACHING TỐI ƯU CHO MÁY YẾU
# =========================
dictionary: Dict[str, List[Dict]] = {}

# Cache cho jieba để tránh load lại - giảm size cho máy yếu
jieba_cache = {}

@lru_cache(maxsize=1000)  # Giảm từ 10000 xuống 1000
def cached_jieba_cut(text: str):
    """Cache kết quả jieba để tránh tính toán lại"""
    return list(jieba.cut(text))

@lru_cache(maxsize=1000)  # Giảm từ 10000 xuống 1000
def cached_pinyin(word: str):
    """Cache pinyin để tránh tính toán lại"""
    return lazy_pinyin(word, style=Style.TONE, errors='ignore')

def extract_classifiers(cl_text: str):
    classifiers = []
    cl_text = cl_text[3:] if cl_text.startswith("CL:") else cl_text
    parts = cl_text.split(",")
    for part in parts:
        match = re.match(r"([^\[\]|]+)(\|([^\[\]]+))?\[(.+?)\]", part.strip())
        if match:
            trad = match.group(1)
            simp = match.group(3) if match.group(3) else trad
            py_number = match.group(4)
            py_marked = lazy_pinyin(simp, style=Style.TONE, errors='ignore')[0]
            classifiers.append({
                "word": simp,
                "pinyin_numbered": py_number,
                "pinyin": py_marked
            })
    return classifiers

def load_cedict(filepath: str):
    pattern = re.compile(r"^(\S+)\s+(\S+)\s+\[(.+?)\]\s+/(.+)/")
    temp_dict = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            if line.startswith("#"):
                continue
            match = pattern.match(line)
            if match:
                trad, simp, pinyin_num, meanings_raw = match.groups()
                meanings = []
                classifiers = []
                for m in meanings_raw.split("/"):
                    if m.startswith("CL:"):
                        classifiers.extend(extract_classifiers(m))
                    elif m.strip():
                        meanings.extend([s.strip() for s in m.split(";") if s.strip()])
                pinyin_marked = " ".join(lazy_pinyin(simp, style=Style.TONE, errors="ignore"))
                temp_dict.setdefault(simp, []).append({
                    "traditional": trad,
                    "simplified": simp,
                    "pinyin_numbered": pinyin_num,
                    "pinyin": pinyin_marked,
                    "meanings": meanings,
                    "classifiers": classifiers
                })
    return temp_dict

def dump_cedict_json(data: Dict, path="cedict_dump.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_from_json(path="cedict_dump.json"):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# Chọn nạp từ JSON hay .u8
USE_JSON = True
if USE_JSON and os.path.exists("cedict_dump.json"):
    dictionary = load_from_json("cedict_dump.json")
else:
    dictionary = load_cedict("cedict_ts.u8")
    dump_cedict_json(dictionary)  # dump cache sau khi nạp

# =========================
# 2. PHÂN TÍCH & PINYIN TỐI ƯU CHO MÁY YẾU
# =========================
async def process_sentence_async(sentence: str):
    """Xử lý async cho một câu"""
    words = cached_jieba_cut(sentence)
    pinyins_list = [cached_pinyin(word) for word in words]
    combined = [
        {"word": word, "pinyin": ''.join(pinyins_list[i]) if i < len(pinyins_list) else ""}
        for i, word in enumerate(words)
    ]
    return combined

@app.post("/segment")
async def segment_sentences(sentences: List[str]):
    # Giới hạn số lượng câu xử lý đồng thời cho máy yếu
    semaphore = asyncio.Semaphore(3)  # Giảm từ 10 xuống 3
    
    async def process_with_semaphore(sentence):
        async with semaphore:
            result = await process_sentence_async(sentence)
            # Force garbage collection sau mỗi request
            gc.collect()
            return result
    
    # Xử lý song song với giới hạn
    tasks = [process_with_semaphore(sentence) for sentence in sentences]
    result = await asyncio.gather(*tasks)
    
    # Clear cache nếu quá lớn
    if len(cached_jieba_cut.cache_info()) > 800:  # Nếu cache > 80%
        cached_jieba_cut.cache_clear()
        cached_pinyin.cache_clear()
    
    return result

# =========================
# 3. API DỊCH TỪ TỐI ƯU
# =========================
@app.get("/translate")
async def translate_word(word: str = Query(..., description="Từ tiếng Trung cần tra")):
    results = dictionary.get(word)
    if not results:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy từ '{word}' trong từ điển.")
    return results

# =========================
# 4. HEALTH CHECK
# =========================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}

# =========================
# 5. STARTUP EVENT
# =========================
@app.on_event("startup")
async def startup_event():
    # Pre-load jieba dictionary
    jieba.initialize()
    print("Jieba initialized and ready")

# =========================
# 6. SHUTDOWN EVENT - CLEANUP
# =========================
@app.on_event("shutdown")
async def shutdown_event():
    # Clear all caches
    cached_jieba_cut.cache_clear()
    cached_pinyin.cache_clear()
    gc.collect()
    print("Caches cleared and memory freed")
