# -*- coding: utf-8 -*-
"""
감성 분류용 학습 데이터 전처리
------------------------------------------------------------
jsonldata 폴더의 대용량 Steam 리뷰(JSONL)를 스트리밍하며
- 텍스트 정제(BBCode/URL 제거)
- 잡음/짧은 리뷰 제거(한글 미포함, 너무 짧음)
- 라벨 부여 (voted_up True=1 긍정 / False=0 부정)
- 클래스 균형 샘플링(긍정/부정 동수)
하여 학습용 CSV(data/steam_sentiment.csv)를 만든다.

입력 JSONL 한 줄 예:
 {"appid":252950,"game":"Rocket League","genre":"Sports",
  "lang":"koreana","review":"...","voted_up":false}
"""

import os
import re
import csv
import json
import glob
import random

# ============================================================
#                       설정 (CONFIG)
# ============================================================
# 원본 리뷰(JSONL) 폴더 경로 — 본인 환경에 맞게 수정하세요.
# ※ 원본 리뷰는 용량이 커서 제출본에 포함하지 않았습니다.
#   이미 전처리된 학습 데이터(data/steam_sentiment.csv)가 있으므로,
#   재학습만 하려면 이 스크립트를 실행하지 않아도 됩니다.
INPUT_DIR = r"C:\Users\user\Desktop\WebCrawling\jsonldata"
OUTPUT_CSV = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "steam_sentiment.csv")   # 상위 폴더의 data/

MAX_PER_CLASS = 20000   # 클래스(긍정/부정)당 최대 표본 수 -> 총 2*MAX_PER_CLASS
MIN_LEN = 5             # 정제 후 최소 글자 수
ONLY_KOREAN = True      # 한글이 포함된 리뷰만 사용
RANDOM_SEED = 42        # 재현성
# ============================================================

random.seed(RANDOM_SEED)

_BBCODE = re.compile(r"\[/?[a-zA-Z][^\]]*\]")
_URL = re.compile(r"https?://\S+|www\.\S+")
_WS = re.compile(r"\s+")
_HANGUL = re.compile(r"[가-힣]")


def clean_text(text):
    if not text:
        return ""
    text = _BBCODE.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _WS.sub(" ", text)
    return text.strip()


def is_valid(text):
    if len(text) < MIN_LEN:
        return False
    if ONLY_KOREAN and not _HANGUL.search(text):
        return False
    return True


def reservoir_add(pool, item, cap, seen_count):
    """저수지 샘플링: pool 크기를 cap 으로 유지하면서 전체에서 고르게 표본 추출."""
    if len(pool) < cap:
        pool.append(item)
    else:
        j = random.randint(0, seen_count)  # 0..seen_count
        if j < cap:
            pool[j] = item


def main():
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.jsonl")))
    if not files:
        print(f"[!] '{INPUT_DIR}' 에서 .jsonl 을 찾지 못했습니다.")
        return

    pos_pool, neg_pool = [], []      # (review, label, game, genre)
    pos_seen = neg_seen = 0
    total = kept = 0

    for path in files:
        print(f"[*] 읽는 중: {os.path.basename(path)}")
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                total += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                review = clean_text(obj.get("review", ""))
                if not is_valid(review):
                    continue

                label = 1 if obj.get("voted_up") else 0
                item = (review, label, obj.get("game", ""), obj.get("genre", ""))
                kept += 1

                if label == 1:
                    reservoir_add(pos_pool, item, MAX_PER_CLASS, pos_seen)
                    pos_seen += 1
                else:
                    reservoir_add(neg_pool, item, MAX_PER_CLASS, neg_seen)
                    neg_seen += 1

    print(f"\n[스캔 완료] 전체 {total:,}줄 / 유효 {kept:,}줄")
    print(f"  긍정(추천) 후보 {pos_seen:,} / 부정(비추천) 후보 {neg_seen:,}")

    # 클래스 균형: 두 풀 중 작은 쪽에 맞춤
    n = min(len(pos_pool), len(neg_pool))
    if n == 0:
        print("[!] 한쪽 클래스 표본이 없습니다.")
        return
    sample = pos_pool[:n] + neg_pool[:n]
    random.shuffle(sample)
    print(f"[균형 샘플] 클래스당 {n:,}개 -> 총 {len(sample):,}개")

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["review", "label", "game", "genre"])
        writer.writerows(sample)

    print(f"[저장] {OUTPUT_CSV}  (총 {len(sample):,}행)")
    print("[완료] 이제 train_sentiment_model.py 로 모델을 학습하세요.")


if __name__ == "__main__":
    main()
