# Steam 게임 리뷰 감성 분석

Steam 게임 리뷰를 수집·전처리하고, 머신러닝으로 **긍정/부정을 분류**하는 프로젝트입니다.
학습된 모델을 **Streamlit 대시보드**로 만들어, 리뷰 감성 분류와 긍정·부정 키워드 워드클라우드를 제공합니다.

## 폴더 구성

```
├── 1_소스코드_및_데이터/     # 리뷰 수집 크롤러(steam·opencritic) + 수집 데이터
├── 2_실행파일_데이터_모델/   # 학습 데이터 · 학습 코드 · 모델 · Streamlit 앱
└── 3_문서/                   # 기술문서 · 발표자료 · 시연영상
```

- **바로 실행해보려면** → `2_실행파일_데이터_모델` 폴더의 `run.bat` (또는 아래 "실행 방법")
- **데이터를 어떻게 모았는지 보려면** → `1_소스코드_및_데이터` 폴더

## 실행 방법

> **준비물**: Python 3.x (Anaconda 권장) · **Java(JDK)** (한글 형태소 분석 konlpy 필수)

### ⭐ 가장 빠른 방법 — 대시보드 바로 실행
학습된 모델이 포함되어 있어, 아래 두 단계면 바로 동작합니다.
```cmd
cd 2_실행파일_데이터_모델
pip install -r requirements.txt
run.bat
```
- `run.bat` 더블클릭도 가능. 실행되면 브라우저에 `http://localhost:8501` 이 열립니다.
- (직접 실행 시) `cd 스트림릿` → `streamlit run SteamSAWebDashboard.py`

### (선택) 처음부터 다시 만들기
| 단계 | 위치 | 명령 |
|------|------|------|
| ① 리뷰 수집 (Steam) | `1_소스코드_및_데이터/steam` | `pip install -r requirements.txt`<br>`python steam_review_crawler.py` |
| ① 리뷰 수집 (OpenCritic) | `1_소스코드_및_데이터/opencritic` | `set RAPIDAPI_KEY=발급키`<br>`python OpenCritic_WebCrawler.py` |
| ② 전처리 | `2_실행파일_데이터_모델/학습코드` | `python preprocess_sentiment_data.py` |
| ③ 모델 학습 | `2_실행파일_데이터_모델/학습코드` | `set KONLPY_HEAP_MB=4096`<br>`python train_sentiment_model.py` |
| ④ 대시보드 | `2_실행파일_데이터_모델/스트림릿` | `streamlit run SteamSAWebDashboard.py` |

> ②~③은 원본 대용량 리뷰 데이터가 필요합니다(저장소 미포함). 이미 전처리된 `data/steam_sentiment.csv`와
> 학습된 `model/*.pkl`이 있으므로, **그냥 실행만 하려면 ④(또는 run.bat)만** 하면 됩니다.

## 개요

| 단계 | 내용 |
|------|------|
| 데이터 수집 | Steam 공개 리뷰 API로 장르별 리뷰 크롤링 (별도: OpenCritic 크롤러) |
| 전처리 | 정제 → 라벨링(추천/비추천) → 클래스 균형 샘플링 |
| 모델 학습 | Okt 형태소 분석(부정어 처리) + TF-IDF(1–2그램) + 로지스틱 회귀 (정확도 약 79%) |
| 결과물 | Streamlit 대시보드 (감성 분류 + 게임별 분석 + 워드클라우드) |

## 저장소 안내
- **학습된 모델**(`2_실행파일_데이터_모델/model/*.pkl`)과 **학습 데이터**(`data/steam_sentiment.csv`)가 포함되어 있어, 받아서 바로 실행/재학습할 수 있습니다.
- 원본 대용량 수집본(약 800MB)은 제외했고, OpenCritic 수집 결과는 **샘플 500건**만 포함했습니다.

> 개인 학습/과제용 프로젝트입니다.
