# Steam 리뷰 크롤러 (메인)

Steam 공개 리뷰 API(`store.steampowered.com/appreviews`)로 장르별 게임 리뷰를 수집합니다.
**이 프로젝트의 최종 수집 방식**입니다.

## 특징
- 여러 주제(장르)를 **라운드 로빈**으로 번갈아 수집 (한쪽 치우침 방지)
- 게임별 **모든 리뷰**를 수집, 중단 시 `progress.json` 기반 이어받기
- 외국어 리뷰 한국어 번역, JSONL 저장
- 리뷰 수집 자체는 **API 키 불필요**

## 실행
```cmd
pip install -r requirements.txt
python steam_review_crawler.py
```
- 상단 CONFIG에서 `TOPICS`, `MAX_GAMES`, `TRANSLATE_TO_KOREAN` 등 설정
- 결과: `output/reviews/{주제}.jsonl`

## 파일
- `steam_review_crawler.py` — 리뷰 수집기
- `preprocess_steam_reviews.py` — 수집한 JSONL을 분석용 CSV로 정리하는 보조 스크립트
