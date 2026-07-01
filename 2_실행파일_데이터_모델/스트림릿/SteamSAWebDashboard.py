# -*- coding: utf-8 -*-
"""Steam 리뷰 감성 분석 대시보드"""

import os
import glob
from collections import Counter

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from mylib.sentiment_analyzer import SentimentAnalyzer, _get_okt
from mylib import myStreamlitVisualizer as viz

# 경로/설정  (data·model 은 상위 폴더(2_실행파일_데이터_모델)에 공용으로 있음)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE_DIR)
DATA_PATH = os.path.join(ROOT, "data", "steam_sentiment.csv")
VEC_PATH = os.path.join(ROOT, "model", "sa_steam_vectorizer.pkl")
MODEL_PATH = os.path.join(ROOT, "model", "sa_steam_predict.pkl")


def _find_korean_font():
    """OS에 맞는 한글 폰트 경로 자동 탐색 (Windows/리눅스/맥)."""
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",   # Streamlit Cloud(fonts-nanum)
        "c:/Windows/Fonts/malgun.ttf",                        # Windows
        "/Library/Fonts/AppleGothic.ttf",                     # macOS
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    hits = glob.glob("/usr/share/fonts/**/*Nanum*.ttf", recursive=True)
    return hits[0] if hits else None


FONT_PATH = _find_korean_font()

STOPWORDS = ["게임", "정말", "진짜", "그냥", "근데", "너무", "조금", "정도", "매우",
             "있다", "없다", "하다", "되다", "이다", "같다", "보다", "수"]
TAGS = ["Noun", "Adjective"]

POS_COLOR = "#3ddc84"   # 긍정 = 밝은 초록 (다크 배경에서 잘 보임)
NEG_COLOR = "#ff5c5c"   # 부정 = 밝은 빨강
LIGHT = "#d6dae0"

st.set_page_config(page_title="Steam 리뷰 감성 분석", page_icon="🎮", layout="centered")


# 캐시
@st.cache_resource
def get_model():
    return SentimentAnalyzer(VEC_PATH, MODEL_PATH)


@st.cache_data
def read_csv(path):
    df = pd.read_csv(path)
    df["review"] = df["review"].astype(str)
    return df


@st.cache_data
def predict(reviews):
    model = get_model()
    return [model.analyze(t) for t in reviews]


@st.cache_data
def count_words(reviews, stopwords, min_len):
    okt = _get_okt()
    stop = set(stopwords)
    tags = set(TAGS)
    c = Counter()
    for text in reviews:
        for word, tag in okt.pos(str(text), norm=True, stem=True):
            if tag in tags and word not in stop and len(word) >= min_len:
                c[word] += 1
    return c


# 사이드바
with st.sidebar:
    st.subheader("설정")
    num_words = st.slider("워드클라우드 단어 수", 20, 100, 50, step=10)
    # 기본 불용어를 미리 채워두고, 사용자가 자유롭게 추가/삭제
    stopword_text = st.text_area("제외할 단어 (쉼표로 구분)",
                                 value=", ".join(STOPWORDS), height=120)
    stopwords = [w.strip() for w in stopword_text.split(",") if w.strip()]
    st.caption("추천 = 긍정, 비추천 = 부정으로 학습한 모델입니다.")


st.title("🎮 Steam 리뷰 감성 분석")
st.write("리뷰가 긍정인지 부정인지 분석하고, 자주 나오는 단어를 보여줍니다.")
st.divider()

if not (os.path.exists(VEC_PATH) and os.path.exists(MODEL_PATH)):
    st.error("모델 파일이 없습니다. (model 폴더 확인)")
    st.stop()

with st.spinner("준비 중..."):
    model = get_model()

tab1, tab2 = st.tabs(["리뷰 분석", "파일 분석"])

# 1) 리뷰 한 줄 분석
with tab1:
    with st.form("one"):
        review = st.text_area("리뷰를 입력하세요", height=140,
                              placeholder="예) 그래픽은 좋은데 최적화가 아쉬워요")
        ok = st.form_submit_button("분석하기", type="primary")
    if ok:
        if not review.strip():
            st.warning("리뷰를 입력해 주세요.")
        else:
            label, conf = model.analyze(review)
            pct = f"{conf*100:.0f}%" if conf is not None else ""
            if label == "긍정":
                st.success("😊 긍정적인 리뷰입니다")
            else:
                st.error("😟 부정적인 리뷰입니다")
            if conf is not None:
                st.progress(conf, text=f"확신도 {pct}")

# 2) 파일 분석 + 워드클라우드
with tab2:
    st.write("리뷰가 들어있는 CSV 파일을 분석합니다.")
    up = st.file_uploader("파일 올리기 (선택)", type=["csv"])
    if up is not None:
        df = pd.read_csv(up)
    elif os.path.exists(DATA_PATH):
        df = read_csv(DATA_PATH)
        st.caption(f"기본 데이터로 분석합니다 · {os.path.basename(DATA_PATH)}")
    else:
        df = None
        st.info("분석할 파일을 올려주세요.")

    if df is not None:
        text_cols = [c for c in df.columns if df[c].dtype == object] or list(df.columns)
        c1, c2 = st.columns(2)
        review_col = c1.selectbox("리뷰가 담긴 열", text_cols)
        labels = ["(없음)"] + list(df.columns)
        label_col = c2.selectbox("실제 정답 열 (선택)", labels,
                                 index=labels.index("label") if "label" in df.columns else 0)
        n = st.slider("분석할 개수", 50, min(2000, len(df)), min(300, len(df)), step=50)

        if st.button("분석 시작", type="primary"):
            sub = df.head(n).copy()
            reviews = [str(t) for t in sub[review_col]]

            with st.spinner("리뷰를 분석하는 중..."):
                res = predict(tuple(reviews))
            sub["결과"] = [r[0] for r in res]
            sub["확신도(%)"] = [round(r[1] * 100, 1) if r[1] is not None else None
                             for r in res]

            pos = int((sub["결과"] == "긍정").sum())
            neg = len(sub) - pos

            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("전체", f"{len(sub):,}")
            m2.metric("😊 긍정", f"{pos:,}")
            m3.metric("😟 부정", f"{neg:,}")
            if label_col != "(없음)":
                truth = sub[label_col].apply(
                    lambda v: 1 if str(v) in ("1", "긍정", "True", "true") else 0)
                guess = (sub["결과"] == "긍정").astype(int)
                m4.metric("정답률", f"{(truth == guess).mean()*100:.0f}%")

            # 긍정/부정 비율 막대 (초록/빨강)
            viz.set_korean_font(FONT_PATH)
            figr, axr = plt.subplots(figsize=(7, 1.2))
            figr.patch.set_alpha(0)
            axr.patch.set_alpha(0)
            axr.barh(["분포"], [pos], color=POS_COLOR, label="긍정")
            axr.barh(["분포"], [neg], left=[pos], color=NEG_COLOR, label="부정")
            leg = axr.legend(ncol=2, loc="upper center",
                             bbox_to_anchor=(0.5, -0.25), frameon=False)
            for t in leg.get_texts():
                t.set_color(LIGHT)
            axr.set_xlim(0, len(sub))
            axr.axis("off")
            st.pyplot(figr)

            st.markdown("#### 자주 나온 단어")
            pos_reviews = sub.loc[sub["결과"] == "긍정", review_col].tolist()
            neg_reviews = sub.loc[sub["결과"] == "부정", review_col].tolist()
            with st.spinner("단어를 세는 중..."):
                pos_c = count_words(tuple(pos_reviews), tuple(stopwords), 2)
                neg_c = count_words(tuple(neg_reviews), tuple(stopwords), 2)

            w1, w2 = st.columns(2)
            with w1:
                st.markdown("**😊 긍정 리뷰**")
                if pos_c:
                    st.pyplot(viz.wordcloud_figure(pos_c, num_words, FONT_PATH,
                                                   color=POS_COLOR))
                    st.pyplot(viz.barh_figure(pos_c, 12, xlabel="횟수",
                                              font_path=FONT_PATH, color=POS_COLOR))
                else:
                    st.info("긍정 리뷰가 없어요.")
            with w2:
                st.markdown("**😟 부정 리뷰**")
                if neg_c:
                    st.pyplot(viz.wordcloud_figure(neg_c, num_words, FONT_PATH,
                                                   color=NEG_COLOR))
                    st.pyplot(viz.barh_figure(neg_c, 12, xlabel="횟수",
                                              font_path=FONT_PATH, color=NEG_COLOR))
                else:
                    st.info("부정 리뷰가 없어요.")

            # 게임별 분류 분석 (game/게임 이름 열이 있을 때)
            game_col = next((c for c in ["game", "게임 이름", "title"]
                             if c in sub.columns), None)
            if game_col:
                st.markdown("#### 🎮 게임별 분류")
                g = sub.copy()
                g["_pos"] = (g["결과"] == "긍정").astype(int)
                agg = g.groupby(game_col).agg(
                    리뷰수=("결과", "size"), 긍정=("_pos", "sum"))
                agg["부정"] = agg["리뷰수"] - agg["긍정"]
                agg["긍정률(%)"] = (agg["긍정"] / agg["리뷰수"] * 100).round(1)
                agg = agg.sort_values("리뷰수", ascending=False)

                st.dataframe(agg[["리뷰수", "긍정", "부정", "긍정률(%)"]],
                             width="stretch", height=280)

                top = agg.head(10)
                if len(top):
                    viz.set_korean_font(FONT_PATH)
                    figg, axg = plt.subplots(figsize=(7, max(2, len(top) * 0.45)))
                    figg.patch.set_alpha(0); axg.patch.set_alpha(0)
                    names = list(top.index)[::-1]
                    pv = list(top["긍정"])[::-1]; nv = list(top["부정"])[::-1]
                    axg.barh(names, pv, color=POS_COLOR, label="긍정")
                    axg.barh(names, nv, left=pv, color=NEG_COLOR, label="부정")
                    axg.tick_params(colors=LIGHT)
                    for sp in axg.spines.values():
                        sp.set_color(LIGHT); sp.set_alpha(0.2)
                    leg = axg.legend(ncol=2, loc="upper center",
                                     bbox_to_anchor=(0.5, -0.06), frameon=False)
                    for t in leg.get_texts():
                        t.set_color(LIGHT)
                    axg.set_title("리뷰 많은 게임 Top 10 (긍정/부정)", color=LIGHT)
                    figg.tight_layout()
                    st.pyplot(figg)

            with st.expander("분석 결과 표 보기"):
                st.dataframe(sub[[review_col, "결과", "확신도(%)"]],
                             width="stretch", height=350)
                csv = sub.to_csv(index=False).encode("utf-8-sig")
                st.download_button("결과 내려받기", csv, "result.csv", "text/csv")
