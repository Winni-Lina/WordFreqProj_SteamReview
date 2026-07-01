# 2. 실행파일 · 데이터 · 모델

**학습 데이터 · 학습 코드 · 모델 · Streamlit 앱**을 역할별로 나눠 담았습니다.

## 구성
```
2_실행파일_데이터_모델/
├── run.bat                       # ▶ 더블클릭하면 대시보드 실행
├── requirements.txt
├── packages.txt                  # (클라우드 배포용 시스템 패키지)
│
├── data/                         # 학습 데이터
│   └── steam_sentiment.csv
├── model/                        # 학습된 모델
│   ├── sa_steam_vectorizer.pkl
│   └── sa_steam_predict.pkl
├── 학습코드/                     # 학습 관련 코드
│   ├── train_sentiment_model.py
│   ├── preprocess_sentiment_data.py
│   └── mylib/
└── 스트림릿/                     # Streamlit 앱
    ├── SteamSAWebDashboard.py
    ├── .streamlit/config.toml
    └── mylib/
```
> `data/` 와 `model/` 은 학습코드·스트림릿이 **공용으로 참조**합니다.

## 설치
```cmd
pip install -r requirements.txt
```
> 한글 형태소 분석(`konlpy`)은 **Java(JDK)** 가 설치되어 있어야 합니다.

## ① 바로 실행 (학습된 모델 사용)
- `run.bat` 더블클릭  또는
```cmd
cd 스트림릿
streamlit run SteamSAWebDashboard.py
```

## ② 다시 학습하기 (선택)
```cmd
cd 학습코드
set KONLPY_HEAP_MB=4096
python train_sentiment_model.py
```
→ 상위 `data/steam_sentiment.csv` 로 학습하여 상위 `model/` 의 `.pkl` 을 다시 생성합니다.

## 모델 개요
Okt 형태소 분석 + TF-IDF(3,000단어) + 로지스틱 회귀 · 정확도 약 78%.
