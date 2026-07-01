# -*- coding: utf-8 -*-
"""
텍스트 분석 모듈
------------------------------------------------------------
CSV 로딩 -> 한국어 토큰화 -> 단어 빈도수 분석
(WordFreqProj/mylib/myTextAnalyzer.py 구조를 Steam 리뷰용으로 맞춤)
"""

import pandas as pd
from collections import Counter


def load_corpus_from_csv(data_filename, column):
    """CSV에서 지정한 컬럼을 읽어 문장 리스트(corpus)로 반환."""
    data_df = pd.read_csv(data_filename)
    # 결측치 제거
    if data_df[column].isnull().sum():
        data_df = data_df.dropna(subset=[column])
    return list(data_df[column].astype(str))


def tokenize_korean_corpus(corpus, tokenizer, my_tags=None, my_stopwords=None,
                           min_len=2):
    """
    한국어 corpus를 토큰화해서 단어 리스트로 반환.
    - tokenizer: 형태소 분석기 pos 함수 (예: Okt().pos)
    - my_tags: 남길 품사 태그 리스트 (예: ['Noun','Verb','Adjective'])
    - my_stopwords: 제외할 단어 리스트
    - min_len: 이 글자수 미만 단어 제외 (한 글자 노이즈 제거)
    """
    my_stopwords = set(my_stopwords or [])
    all_tokens = []
    for text in corpus:
        for word, tag in tokenizer(text):
            if my_tags and tag not in my_tags:
                continue
            if word in my_stopwords:
                continue
            if len(word) < min_len:
                continue
            all_tokens.append(word)
    return all_tokens


def analyze_word_freq(tokens):
    """토큰 리스트 -> Counter(단어:빈도)."""
    return Counter(tokens)
