# 1. 소스코드 및 데이터 (크롤러)

리뷰를 **수집하는 크롤러**와 그 **수집 결과 데이터**입니다.

## 구성
```
1_소스코드_및_데이터/
├── steam/                              # Steam 리뷰 크롤러 (최종 사용)
│   ├── steam_review_crawler.py
│   ├── preprocess_steam_reviews.py
│   ├── requirements.txt
│   └── README.md
├── opencritic/                         # OpenCritic 크롤러 (초기 시도)
│   ├── OpenCritic_WebCrawler.py
│   ├── requirements.txt
│   └── README.md
└── data/
    └── opencritic_reviews_sample.jsonl # OpenCritic 수집 결과 (샘플 500건)
```
> 원본 전체 수집본은 용량이 커서 저장소에는 **샘플 500건**만 포함했습니다.

## 크롤러 요약
| | 설명 |
|---|---|
| **steam/** | Steam 공개 리뷰 API로 장르별 리뷰 수집 (최종 채택). 실행법은 `steam/README.md` |
| **opencritic/** | OpenCritic API(RapidAPI)로 평론 수집. 무료 API 데이터가 한정적이라 **Steam으로 전환**함. 실행법은 `opencritic/README.md` |

> 수집한 데이터로 모델을 학습·실행하는 부분은 **`2_실행파일_데이터_모델`** 폴더에 있습니다.
