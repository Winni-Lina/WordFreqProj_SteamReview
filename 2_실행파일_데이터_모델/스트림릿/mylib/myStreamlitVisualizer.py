# -*- coding: utf-8 -*-
"""단어 빈도 시각화 (막대그래프 / 워드클라우드) — 다크 배경용"""

import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
from wordcloud import WordCloud

LIGHT = "#d6dae0"   # 어두운 배경용 글자색


def set_korean_font(font_path):
    if font_path:
        font_name = font_manager.FontProperties(fname=font_path).get_name()
        rc("font", family=font_name)
        plt.rcParams["axes.unicode_minus"] = False


def _transparent(fig, ax):
    """배경을 투명하게 해서 다크 테마에 자연스럽게 얹히도록."""
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)


def barh_figure(counter, num_words, title=None, xlabel=None, ylabel=None,
                font_path=None, color="#3ddc84", text_color=LIGHT):
    """고빈도 단어 수평 막대그래프."""
    set_korean_font(font_path)
    items = counter.most_common(num_words)
    x = [w for w, _ in items]
    y = [c for _, c in items]

    fig, ax = plt.subplots(figsize=(7, max(3.5, num_words * 0.32)))
    _transparent(fig, ax)
    ax.barh(x[::-1], y[::-1], color=color)
    if title:
        ax.set_title(title, color=text_color)
    if xlabel:
        ax.set_xlabel(xlabel, color=text_color)
    if ylabel:
        ax.set_ylabel(ylabel, color=text_color)
    ax.tick_params(colors=text_color)
    for sp in ax.spines.values():
        sp.set_color(text_color)
        sp.set_alpha(0.25)
    for i, v in enumerate(y[::-1]):
        ax.text(v, i, f" {v}", va="center", fontsize=9, color=text_color)
    fig.tight_layout()
    return fig


def _mono(hex_color):
    def f(*args, **kwargs):
        return hex_color
    return f


def wordcloud_figure(counter, num_words, font_path, color=None, colormap="viridis"):
    """워드클라우드 (투명 배경). color 지정 시 단색, 아니면 colormap 사용."""
    wc = WordCloud(
        font_path=font_path,
        width=800,
        height=460,
        max_words=num_words,
        mode="RGBA",
        background_color=None,          # 투명
        colormap=colormap,
        color_func=_mono(color) if color else None,
    )
    wc = wc.generate_from_frequencies(counter)

    fig, ax = plt.subplots(figsize=(7, 4.0))
    fig.patch.set_alpha(0)
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.tight_layout()
    return fig
