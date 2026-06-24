import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# ── 한국어 폰트 설정 ──────────────────────────────────────
import matplotlib
import platform

if platform.system() == "Windows":
    matplotlib.rc("font", family="Malgun Gothic")
else:
    matplotlib.rc("font", family="AppleGothic")
matplotlib.rcParams["axes.unicode_minus"] = False

# ── 페이지 설정 ───────────────────────────────────────────
st.set_page_config(
    page_title="청년 지원금 정책 필드 추출 성능평가",
    layout="wide",
)

st.title("청년 지원금 정책 필드 추출 성능평가")
st.markdown("---")

# ── 데이터 ────────────────────────────────────────────────

# LLM 성능 데이터 (50개 기준)
llm_data = {
    "모델":       ["LLM only (Ollama)", "Rule+Ollama", "LLM only (Watson)", "Rule+Watson"],
    "Exact":      [38, 45, 45, 50],
    "Total":      [50, 50, 50, 50],
    "Precision":  [0.739, 0.967, 0.946, 1.000],
    "Recall":     [0.447, 0.763, 0.921, 1.000],
    "F1":         [0.557, 0.853, 0.933, 1.000],
    "평균시간(초)": [72.57, 22.50, 0.52, 0.27],
}

# 임베딩 성능 데이터 (520개 기준)
embedding_data = {
    "모델":       ["KoELECTRA", "TUNiB-Electra", "Ko-SRoBERTa"],
    "Exact":      [465, 471, 491],
    "Total":      [520, 520, 520],
    "Precision":  [0.865, 0.925, 0.933],
    "Recall":     [0.811, 0.784, 0.884],
    "F1":         [0.837, 0.849, 0.908],
    "평균시간(초)": [5.53, 4.63, 4.62],
}

llm_df       = pd.DataFrame(llm_data)
embedding_df = pd.DataFrame(embedding_data)

# ── 탭 구성 ───────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 LLM 성능 비교",
    "🧠 임베딩 모델 성능 비교",
    "⚡ 속도 비교",
    "📋 전체 요약",
])

# ══════════════════════════════════════════════════════════
# TAB 1: LLM 성능 비교
# ══════════════════════════════════════════════════════════
with tab1:
    st.subheader("LLM 모델 성능 비교 (50개 공고 기준)")

    # 테이블
    display_df = llm_df.copy()
    display_df["정확도"] = display_df.apply(
        lambda r: f"{r['Exact']}/{r['Total']} ({r['Exact']/r['Total']*100:.1f}%)", axis=1
    )
    st.dataframe(
        display_df[["모델", "정확도", "Precision", "Recall", "F1", "평균시간(초)"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Precision / Recall / F1 비교**")
        fig, ax = plt.subplots(figsize=(7, 4))
        x      = np.arange(len(llm_df))
        width  = 0.25
        ax.bar(x - width, llm_df["Precision"], width, label="Precision", color="#4C72B0")
        ax.bar(x,         llm_df["Recall"],    width, label="Recall",    color="#DD8452")
        ax.bar(x + width, llm_df["F1"],        width, label="F1",        color="#55A868")
        ax.set_xticks(x)
        ax.set_xticklabels(llm_df["모델"], rotation=15, ha="right", fontsize=9)
        ax.set_ylim(0, 1.1)
        ax.legend()
        ax.set_title("LLM 모델 성능 비교")
        ax.grid(axis="y", alpha=0.3)
        st.pyplot(fig)
        plt.close()

    with col2:
        st.markdown("**F1 Score 비교**")
        fig, ax = plt.subplots(figsize=(7, 4))
        colors  = ["#4C72B0", "#DD8452", "#55A868", "#C44E52"]
        bars    = ax.bar(llm_df["모델"], llm_df["F1"], color=colors)
        ax.set_ylim(0, 1.1)
        ax.set_title("F1 Score")
        ax.grid(axis="y", alpha=0.3)
        for bar, val in zip(bars, llm_df["F1"]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f"{val:.3f}", ha="center", fontsize=10, fontweight="bold")
        ax.set_xticklabels(llm_df["모델"], rotation=15, ha="right", fontsize=9)
        st.pyplot(fig)
        plt.close()

    # Epoch별 학습 곡선
    st.markdown("---")
    st.markdown("**KoELECTRA Epoch별 학습 곡선**")

    epoch_data = {
        "KoELECTRA": {
            "Loss":      [0.2738, 0.1472, 0.1167, 0.0887, 0.0769],
            "Precision": [0.689,  0.645,  0.874,  0.922,  0.865],
            "Recall":    [0.595,  0.668,  0.621,  0.742,  0.811],
            "F1":        [0.638,  0.656,  0.726,  0.822,  0.837],
        },
        "TUNiB-Electra": {
            "Loss":      [0.3147, 0.1579, 0.1369, 0.1078, 0.0822],
            "Precision": [0.743,  0.738,  0.931,  0.925,  0.892],
            "Recall":    [0.579,  0.668,  0.568,  0.784,  0.784],
            "F1":        [0.651,  0.702,  0.706,  0.849,  0.835],
        },
        "Ko-SRoBERTa": {
            "Loss":      [0.2279, 0.1019, 0.0766, 0.0675, 0.0501],
            "Precision": [0.757,  0.912,  0.945,  0.852,  0.933],
            "Recall":    [0.737,  0.768,  0.811,  0.847,  0.884],
            "F1":        [0.747,  0.834,  0.873,  0.850,  0.908],
        },
    }

    epochs = [1, 2, 3, 4, 5]
    colors_epoch = {"KoELECTRA": "#4C72B0", "TUNiB-Electra": "#DD8452", "Ko-SRoBERTa": "#55A868"}

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("**F1 Score 변화**")
        fig, ax = plt.subplots(figsize=(6, 4))
        for model_name, metrics in epoch_data.items():
            ax.plot(epochs, metrics["F1"], marker="o",
                    label=model_name, color=colors_epoch[model_name])
        ax.set_xlabel("Epoch")
        ax.set_ylabel("F1 Score")
        ax.set_ylim(0.5, 1.0)
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_title("Epoch별 F1 Score")
        st.pyplot(fig)
        plt.close()

    with col4:
        st.markdown("**Loss 변화**")
        fig, ax = plt.subplots(figsize=(6, 4))
        for model_name, metrics in epoch_data.items():
            ax.plot(epochs, metrics["Loss"], marker="o",
                    label=model_name, color=colors_epoch[model_name])
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Loss")
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_title("Epoch별 Loss")
        st.pyplot(fig)
        plt.close()

# ══════════════════════════════════════════════════════════
# TAB 2: 임베딩 모델 성능 비교
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("임베딩 모델 성능 비교 (520개 검증 데이터 기준)")

    display_df2 = embedding_df.copy()
    display_df2["정확도"] = display_df2.apply(
        lambda r: f"{r['Exact']}/{r['Total']} ({r['Exact']/r['Total']*100:.1f}%)", axis=1
    )
    st.dataframe(
        display_df2[["모델", "정확도", "Precision", "Recall", "F1", "평균시간(초)"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Precision / Recall / F1 비교**")
        fig, ax = plt.subplots(figsize=(7, 4))
        x      = np.arange(len(embedding_df))
        width  = 0.25
        ax.bar(x - width, embedding_df["Precision"], width, label="Precision", color="#4C72B0")
        ax.bar(x,         embedding_df["Recall"],    width, label="Recall",    color="#DD8452")
        ax.bar(x + width, embedding_df["F1"],        width, label="F1",        color="#55A868")
        ax.set_xticks(x)
        ax.set_xticklabels(embedding_df["모델"], fontsize=10)
        ax.set_ylim(0, 1.1)
        ax.legend()
        ax.set_title("임베딩 모델 성능 비교")
        ax.grid(axis="y", alpha=0.3)
        st.pyplot(fig)
        plt.close()

    with col2:
        st.markdown("**정확도(Exact Match) 비교**")
        fig, ax = plt.subplots(figsize=(7, 4))
        colors  = ["#4C72B0", "#DD8452", "#55A868"]
        exact_pct = [e/t*100 for e, t in zip(embedding_df["Exact"], embedding_df["Total"])]
        bars = ax.bar(embedding_df["모델"], exact_pct, color=colors)
        ax.set_ylim(0, 110)
        ax.set_ylabel("정확도 (%)")
        ax.set_title("Exact Match 정확도")
        ax.grid(axis="y", alpha=0.3)
        for bar, val, e, t in zip(bars, exact_pct, embedding_df["Exact"], embedding_df["Total"]):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f"{e}/{t}\n({val:.1f}%)", ha="center", fontsize=10, fontweight="bold")
        st.pyplot(fig)
        plt.close()

# ══════════════════════════════════════════════════════════
# TAB 3: 속도 비교
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("처리 속도 비교")

    all_models = llm_df["모델"].tolist() + embedding_df["모델"].tolist()
    all_times  = llm_df["평균시간(초)"].tolist() + embedding_df["평균시간(초)"].tolist()
    colors_all = (
        ["#4C72B0"] * len(llm_df) +
        ["#55A868"] * len(embedding_df)
    )

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.barh(all_models, all_times, color=colors_all)
    ax.set_xlabel("처리 시간 (초)")
    ax.set_title("모델별 처리 시간 비교")
    ax.grid(axis="x", alpha=0.3)
    for bar, val in zip(bars, all_times):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val:.2f}초", va="center", fontsize=9)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#4C72B0", label="LLM 모델"),
        Patch(facecolor="#55A868", label="임베딩 모델"),
    ]
    ax.legend(handles=legend_elements)
    st.pyplot(fig)
    plt.close()

    st.markdown("---")
    st.info("임베딩 모델은 LLM 대비 훨씬 빠르지만 학습 데이터가 필요합니다.")

# ══════════════════════════════════════════════════════════
# TAB 4: 전체 요약
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("전체 모델 성능 요약")

    all_data = {
        "모델":       llm_df["모델"].tolist() + embedding_df["모델"].tolist(),
        "유형":       ["LLM"]*len(llm_df) + ["임베딩"]*len(embedding_df),
        "Precision":  llm_df["Precision"].tolist() + embedding_df["Precision"].tolist(),
        "Recall":     llm_df["Recall"].tolist() + embedding_df["Recall"].tolist(),
        "F1":         llm_df["F1"].tolist() + embedding_df["F1"].tolist(),
        "평균시간(초)": llm_df["평균시간(초)"].tolist() + embedding_df["평균시간(초)"].tolist(),
    }
    all_df = pd.DataFrame(all_data).sort_values("F1", ascending=False).reset_index(drop=True)

    st.dataframe(all_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**전체 F1 Score 비교**")
        fig, ax = plt.subplots(figsize=(7, 5))
        colors_type = ["#4C72B0" if t == "LLM" else "#55A868" for t in all_df["유형"]]
        bars = ax.barh(all_df["모델"], all_df["F1"], color=colors_type)
        ax.set_xlim(0, 1.1)
        ax.set_xlabel("F1 Score")
        ax.set_title("전체 모델 F1 비교")
        ax.grid(axis="x", alpha=0.3)
        for bar, val in zip(bars, all_df["F1"]):
            ax.text(bar.get_width() + 0.01, bar.get_y() + bar.get_height()/2,
                    f"{val:.3f}", va="center", fontsize=9, fontweight="bold")
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor="#4C72B0", label="LLM"),
            Patch(facecolor="#55A868", label="임베딩"),
        ]
        ax.legend(handles=legend_elements)
        st.pyplot(fig)
        plt.close()

    with col2:
        st.markdown("**결론**")
        st.success("🏆 Rule+Watson : F1 1.000 (최고 성능)")
        st.info("🥈 Ko-SRoBERTa : F1 0.908 (임베딩 모델 최고)")
        st.warning("⚡ 속도: 임베딩 모델이 LLM보다 훨씬 빠름")
        st.markdown("""
**모델별 특징 요약:**
- **Rule+Watson** → 정확도 최고, 학습 데이터 불필요
- **Ko-SRoBERTa** → 임베딩 중 최고 성능, 빠른 속도
- **TUNiB-Electra** → Precision 높지만 Recall 낮음
- **KoELECTRA** → 3개 중 가장 낮은 성능
- **LLM only (Ollama)** → 느리고 성능도 낮음
        """)