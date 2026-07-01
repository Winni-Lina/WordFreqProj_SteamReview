# -*- coding: utf-8 -*-
"""
Steam 리뷰 전처리 스크립트
------------------------------------------------------------
웹크롤러(steam_review_crawler.py)가 모은 JSONL 리뷰들을
미니프로젝트(단어빈도 분석/대시보드)가 쓸 CSV 로 변환한다.

[입력] 크롤러 결과 폴더 안의 *.jsonl
        각 줄: {"게임 이름": "", "작성자": "", "리뷰 내용": "", "평점": ""}
[출력] data/steam_reviews.csv
        컬럼: title, author, rating, recommend, review, topic

전처리 내용:
- Steam 리뷰 특유의 BBCode 태그([b], [url], [spoiler] 등) 제거
- URL 제거, 공백 정리
- 빈 리뷰 / 너무 짧은 리뷰 제거
- (옵션) 중복 리뷰 제거
"""

import os
import re
import csv
import json
import glob

# ============================================================
#                       설정 (CONFIG)
# ============================================================
# 크롤러가 저장한 리뷰 폴더 (steam_review_crawler.py 의 OUTPUT_DIR/reviews)
INPUT_DIR = r"C:\Users\user\Desktop\WebCrawling\Steam_WebCrawler\output\reviews"

# 전처리 결과 CSV 저장 위치 (이 스크립트 옆 data 폴더)
OUTPUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "data", "steam_reviews.csv")

MIN_REVIEW_LEN = 2        # 정제 후 글자수가 이보다 짧으면 버림
DROP_DUPLICATES = True    # 같은 (게임, 작성자, 리뷰) 중복 제거
# ============================================================


# Steam BBCode 태그: [b], [/b], [url=...], [list], [spoiler] 등
_BBCODE = re.compile(r"\[/?[a-zA-Z][^\]]*\]")
# URL
_URL = re.compile(r"https?://\S+|www\.\S+")
# 여러 공백/줄바꿈
_WS = re.compile(r"\s+")


def clean_text(text):
    """리뷰 텍스트에서 BBCode/URL 제거 후 공백 정리."""
    if not text:
        return ""
    text = _BBCODE.sub(" ", text)
    text = _URL.sub(" ", text)
    text = _WS.sub(" ", text)
    return text.strip()


def load_jsonl_reviews(input_dir):
    """input_dir 안의 모든 *.jsonl 을 읽어 (레코드, 주제) 리스트로 반환."""
    files = sorted(glob.glob(os.path.join(input_dir, "*.jsonl")))
    if not files:
        print(f"[!] '{input_dir}' 에서 .jsonl 파일을 찾지 못했습니다.")
        print("    먼저 steam_review_crawler.py 로 리뷰를 수집하세요.")
        return []

    rows = []
    for path in files:
        # 파일명(확장자 제외)을 주제(topic)로 사용
        topic = os.path.splitext(os.path.basename(path))[0]
        n = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rows.append((obj, topic))
                n += 1
        print(f"  - {os.path.basename(path)}: {n}줄 읽음")
    return rows


def preprocess(rows):
    """원시 레코드 -> 정제된 행 리스트(dict)."""
    cleaned = []
    seen = set()
    dropped_empty = 0
    dropped_dup = 0

    for obj, topic in rows:
        title = (obj.get("게임 이름") or "").strip()
        author = (obj.get("작성자") or "").strip()
        rating = (obj.get("평점") or "").strip()        # "추천" / "비추천"
        review = clean_text(obj.get("리뷰 내용") or "")

        # 정제 후 너무 짧으면 제거
        if len(review) < MIN_REVIEW_LEN:
            dropped_empty += 1
            continue

        # 중복 제거
        if DROP_DUPLICATES:
            key = (title, author, review)
            if key in seen:
                dropped_dup += 1
                continue
            seen.add(key)

        cleaned.append({
            "title": title,
            "author": author,
            "rating": rating,
            "recommend": 1 if rating == "추천" else 0,  # 숫자형 평점(추천=1/비추천=0)
            "review": review,
            "topic": topic,
        })

    print(f"\n[전처리] 유효 {len(cleaned)}건 "
          f"(빈/짧은 리뷰 {dropped_empty}건, 중복 {dropped_dup}건 제거)")
    return cleaned


def save_csv(records, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fields = ["title", "author", "rating", "recommend", "review", "topic"]
    # utf-8-sig: Excel 에서도 한글이 깨지지 않음
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(f"[저장] {out_path}  (총 {len(records)}행)")


def print_summary(records):
    if not records:
        return
    from collections import Counter
    by_topic = Counter(r["topic"] for r in records)
    by_game = Counter(r["title"] for r in records)
    recommend = sum(r["recommend"] for r in records)

    print("\n========== 요약 ==========")
    print(f"총 리뷰 수 : {len(records)}")
    print(f"추천 : {recommend}  /  비추천 : {len(records) - recommend}")
    print(f"주제 수 : {len(by_topic)}  /  게임 수 : {len(by_game)}")
    print("주제별 리뷰 수 (상위 10):")
    for topic, cnt in by_topic.most_common(10):
        print(f"  {topic:<24} {cnt}")
    print("==========================")


def main():
    print(f"[*] 입력 폴더: {INPUT_DIR}")
    rows = load_jsonl_reviews(INPUT_DIR)
    if not rows:
        return
    print(f"[*] 총 {len(rows)}줄 로드됨. 전처리 시작...")

    records = preprocess(rows)
    if not records:
        print("[!] 유효한 리뷰가 없습니다.")
        return

    save_csv(records, OUTPUT_CSV)
    print_summary(records)
    print("\n[완료] 이제 이 CSV 로 단어빈도 분석/대시보드를 만들 수 있습니다.")


if __name__ == "__main__":
    main()
