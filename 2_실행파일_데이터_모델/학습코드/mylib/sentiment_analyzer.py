# -*- coding: utf-8 -*-
"""
감성 분석 배포 모듈
------------------------------------------------------------
- korean_tokenizer: TF-IDF 벡터라이저가 사용하는 한국어 토크나이저.
  ★ 학습(train)과 배포(앱)가 '완전히 같은' 함수를 참조해야 저장된 벡터라이저를
    불러올 수 있으므로, 이 함수는 반드시 이 모듈에 두고 두 폴더(학습코드/스트림릿)를
    동일하게 유지한다.
- SentimentAnalyzer: 저장된 vectorizer/model(.pkl)을 불러와 리뷰 긍부정 판단.
"""

import os
import re
import joblib
from konlpy.tag import Okt

# 분석에 사용할 품사 (부사도 포함: 별로/전혀/아주 등 강조·반어 신호)
MY_TAGS = ["Noun", "Adjective", "Verb", "Adverb"]
MY_STOPWORDS = set()

# 부정/반어 신호어: 이 뒤의 내용어에 'NEG_' 표시 -> '안 좋다' 와 '좋다' 를 구분
NEG_CUES = {"안", "못", "없다", "아니다", "말다", "별로", "전혀", "그닥", "덜"}

# 3번 이상 반복 문자 축소 (번역체/구어체 정규화: ㅋㅋㅋㅋ->ㅋㅋ, 좋아아아->좋아아)
_REPEAT = re.compile(r"(.)\1{2,}")

# Okt는 JVM 로딩이 무거우므로 모듈 전역에서 1회만 생성(지연 초기화)
_okt = None
# JVM 힙: 앱은 소량 토큰화만 하므로 기본 512MB. 대량 학습 시 KONLPY_HEAP_MB=4096 권장.
JVM_HEAP_MB = int(os.environ.get("KONLPY_HEAP_MB", "512"))


def _get_okt():
    global _okt
    if _okt is None:
        try:
            from konlpy import jvm
            jvm.init_jvm(max_heap_size=JVM_HEAP_MB)
        except Exception:
            pass
        _okt = Okt()
    return _okt


def _normalize(text):
    """번역체/구어체 정규화."""
    return _REPEAT.sub(r"\1\1", str(text))


def korean_tokenizer(text):
    """
    한국어 텍스트 -> 토큰 리스트.
    - Okt 형태소 분석(정규화·원형 복원) 후 명사/형용사/동사/부사만 사용
    - 부정어(안/못/없다 등) 바로 뒤 내용어에는 'NEG_' 를 붙여 반어·부정 표현을 학습
      (예: "안 재밌다" -> ['안', 'NEG_재밌다'],  "재미없다" -> ['재미', 'NEG_...'])
    """
    okt = _get_okt()
    tokens = []
    neg = False
    for word, tag in okt.pos(_normalize(text), norm=True, stem=True):
        if word in NEG_CUES:
            neg = True
            tokens.append(word)
            continue
        if tag in MY_TAGS and word not in MY_STOPWORDS:
            tokens.append(("NEG_" + word) if neg else word)
            neg = False
    return tokens


class SentimentAnalyzer:
    """저장된 모델로 리뷰 긍부정을 판단한다."""

    def __init__(self, vectorizer_file, model_file):
        self.vectorizer = joblib.load(vectorizer_file)
        self.model = joblib.load(model_file)

    def analyze(self, review):
        """review(str) -> (label, confidence)
        label: '긍정'/'부정', confidence: 0~1 확률(가능할 때) 또는 None."""
        fv = self.vectorizer.transform([review])
        pred = int(self.model.predict(fv)[0])
        label = "긍정" if pred == 1 else "부정"

        conf = None
        if hasattr(self.model, "predict_proba"):
            proba = self.model.predict_proba(fv)[0]
            conf = float(proba[pred])
        return label, conf


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    model_dir = os.path.join(os.path.dirname(os.path.dirname(base)), "model")
    sa = SentimentAnalyzer(
        os.path.join(model_dir, "sa_steam_vectorizer.pkl"),
        os.path.join(model_dir, "sa_steam_predict.pkl"),
    )
    for r in ["정말 재미있고 시간 가는 줄 모르고 했어요",
              "최악의 게임 환불하고 싶다",
              "그래픽은 좋은데 최적화가 너무 별로",
              "와 진짜 재밌겠다 ㅋㅋ 버그 때문에 실행도 안 됨"]:
        label, conf = sa.analyze(r)
        c = f"{conf*100:.1f}%" if conf is not None else "-"
        print(f"{r} -> {label} ({c})")
