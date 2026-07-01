# -*- coding: utf-8 -*-
"""
Steam 리뷰 긍부정 분류 모델 학습
------------------------------------------------------------
1. 전처리 CSV(data/steam_sentiment.csv) 로딩
2. TF-IDF 특징 벡터 추출 (Okt 한국어 토크나이저)
3. 여러 머신러닝 모델 학습 및 비교
4. 최고 성능 모델 + 벡터라이저 저장 (model/*.pkl)
(D:\\_AIService26 노트북 06 '머신러닝기반 텍스트분류' 방식)

실행:
    python train_sentiment_model.py
"""

import os
import time

import numpy as np
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.metrics import classification_report, confusion_matrix

# 저장된 벡터라이저가 참조할 토크나이저는 반드시 이 모듈에서 가져온다
from mylib.sentiment_analyzer import korean_tokenizer

# ============================================================
#                       설정 (CONFIG)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE_DIR)   # data·model 은 상위 폴더에 공용으로 있음
DATA_CSV = os.path.join(ROOT, "data", "steam_sentiment.csv")
MODEL_DIR = os.path.join(ROOT, "model")

MAX_FEATURES = 5000     # TF-IDF 최대 특징 수 (2-그램 포함으로 늘림)
NGRAM_RANGE = (1, 2)    # 1~2그램: '안 좋다', '재미 없다', '정말 별로' 같은 구절 포착(반어/부정)
TEST_SIZE = 0.2
RANDOM_STATE = 42
# ============================================================


def main():
    if not os.path.exists(DATA_CSV):
        print(f"[!] 학습 데이터가 없습니다: {DATA_CSV}")
        print("    먼저 preprocess_sentiment_data.py 를 실행하세요.")
        return

    # ---------- 1. 데이터 로딩 ----------
    df = pd.read_csv(DATA_CSV)
    df = df.dropna(subset=["review", "label"])
    df["review"] = df["review"].astype(str)
    print(f"[*] 데이터 {len(df):,}건 (긍정 {int((df.label==1).sum()):,} / "
          f"부정 {int((df.label==0).sum()):,})")

    X = list(df["review"])
    y = np.array(df["label"], dtype=int)

    train_X, test_X, train_y, test_y = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y)
    print(f"[*] 학습 {len(train_X):,} / 평가 {len(test_X):,}")

    # ---------- 2. TF-IDF 특징 벡터 ----------
    print("[*] TF-IDF 벡터라이저 학습(형태소 분석)... 잠시 걸립니다.")
    t0 = time.time()
    # 토크나이저가 부정어(NEG_) 처리를 하고, 2-그램으로 구절 단위 반어/부정도 학습
    vectorizer = TfidfVectorizer(tokenizer=korean_tokenizer,
                                 ngram_range=NGRAM_RANGE,
                                 max_features=MAX_FEATURES)
    train_X_fv = vectorizer.fit_transform(train_X)
    test_X_fv = vectorizer.transform(test_X)
    print(f"    특징 수: {len(vectorizer.get_feature_names_out())}, "
          f"소요 {time.time()-t0:.1f}초")

    # ---------- 3. 모델별 학습/평가 ----------
    models = {
        "NaiveBayes": MultinomialNB(),
        "LogisticRegression": LogisticRegression(max_iter=1000),
        "LinearSVC": LinearSVC(),
    }

    score_df = pd.DataFrame(columns=["train", "test"])
    trained = {}
    for name, model in models.items():
        t0 = time.time()
        model.fit(train_X_fv, train_y)
        tr = model.score(train_X_fv, train_y) * 100
        te = model.score(test_X_fv, test_y) * 100
        score_df.loc[name] = [tr, te]
        trained[name] = model
        print(f"  - {name:<20} train {tr:.2f}% / test {te:.2f}%  ({time.time()-t0:.1f}s)")

    print("\n[성능 비교]")
    print(score_df.sort_values("test", ascending=False).round(2))

    # ---------- 4. 최고 모델 선택 + 저장 ----------
    best_name = score_df["test"].astype(float).idxmax()
    best_model = trained[best_name]
    print(f"\n[선택] 최고 성능 모델: {best_name}")

    # 상세 평가
    pred = best_model.predict(test_X_fv)
    print("\n[분류 리포트]")
    print(classification_report(test_y, pred, target_names=["부정", "긍정"]))
    print("[혼동 행렬] (행=실제, 열=예측)")
    print(confusion_matrix(test_y, pred))

    os.makedirs(MODEL_DIR, exist_ok=True)
    vec_path = os.path.join(MODEL_DIR, "sa_steam_vectorizer.pkl")
    model_path = os.path.join(MODEL_DIR, "sa_steam_predict.pkl")
    joblib.dump(vectorizer, vec_path)
    joblib.dump(best_model, model_path)
    print(f"\n[저장] {vec_path}")
    print(f"[저장] {model_path}")

    # ---------- 5. 샘플 예측 ----------
    print("\n[샘플 예측]")
    samples = [
        "정말 재미있고 시간 가는 줄 모르고 플레이했어요",
        "최악의 게임 돈 아깝다 환불",
        "그래픽은 좋은데 최적화가 너무 별로예요",
        "가성비 최고의 명작 강력 추천합니다",
        "버그 투성이에 자꾸 튕겨서 못하겠다",
    ]
    for s in samples:
        fv = vectorizer.transform([s])
        p = int(best_model.predict(fv)[0])
        print(f"  {s} -> {'긍정' if p == 1 else '부정'}")

    print("\n[완료] 모델 학습 및 저장 끝.")


if __name__ == "__main__":
    main()
