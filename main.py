import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# =========================
# Streamlit 기본 설정
# =========================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =========================
# 한글 폰트 (CSS)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 기본 정보
# =========================
DATA_DIR = Path(__file__).parent / "data"

SCHOOL_EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,  # 최적
    "아라고": 4.0,
    "동산고": 8.0,
}

SCHOOL_COLOR = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728",
}

# =========================
# 유틸: NFC/NFD 파일 탐색
# =========================
def find_file_by_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for f in directory.iterdir():
        if not f.is_file():
            continue
        name_nfc = unicodedata.normalize("NFC", f.name)
        name_nfd = unicodedata.normalize("NFD", f.name)

        if name_nfc == target_nfc or name_nfd == target_nfd:
            return f
    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    env_data = {}

    for school in SCHOOL_EC_INFO.keys():
        filename = f"{school}_환경데이터.csv"
        file_path = find_file_by_name(DATA_DIR, filename)

        if file_path is None:
            st.error(f"환경 데이터 파일을 찾을 수 없습니다: {filename}")
            return None

        df = pd.read_csv(file_path)
        df["school"] = school
        env_data[school] = df

    return env_data

@st.cache_data
def load_growth_data():
    xlsx_path = None
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() == ".xlsx":
            xlsx_path = f
            break

    if xlsx_path is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    excel = pd.ExcelFile(xlsx_path, engine="openpyxl")
    growth_data = {}

    for sheet in excel.sheet_names:
        df = excel.parse(sheet)
        df["school"] = sheet
        df["ec"] = SCHOOL_EC_INFO.get(sheet, None)
        growth_data[sheet] = df

    return growth_data

# =========================
# 데이터 로딩 실행
# =========================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# =========================
# 사이드바
# =========================
st.sidebar.title("학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_EC_INFO.keys())
)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

# =========================
# 탭 구성
# =========================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# Tab 1: 실험 개요
# ======================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown(
        """
        본 연구는 **극지식물의 생육에 최적화된 EC(Electrical Conductivity) 농도**를 도출하기 위해  
        4개 학교에서 서로 다른 EC 조건 하에 동일한 작물을 재배하고,  
        환경 데이터와 생육 결과를 비교·분석한 연구이다.
        """
    )

    # 학교별 EC 조건 표
    overview_rows = []
    total_plants = 0

    for school, df in growth_data.items():
        count = len(df)
        total_plants += count
        overview_rows.append({
            "학교명": school,
            "EC 목표": SCHOOL_EC_INFO[school],
            "개체수": count,
            "색상": SCHOOL_COLOR[school]
        })

    overview_df = pd.DataFrame(overview_rows)
    st.dataframe(overview_df, use_container_width=True)

    # 주요 지표 카드
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()
    optimal_ec = 2.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", f"{total_plants} 개")
    c2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.1f} %")
    c4.metric("최적 EC", f"{optimal_ec}")

# ======================================================
# Tab 2: 환경 데이터
# ======================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    # 평균 계산
    avg_rows = []
    for school, df in env_data.items():
        avg_rows.append({
            "school": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec_measured": df["ec"].mean(),
            "ec_target": SCHOOL_EC_INFO[school]
        })
    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=avg_df["school"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["school"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["school"], y=avg_df["ph"], row=2, col=1)

    fig.add_bar(
        x=avg_df["school"],
        y=avg_df["ec_target"],
        name="목표 EC",
        row=2, col=2
    )
    fig.add_bar(
        x=avg_df["school"],
        y=avg_df["ec_measured"],
        name="실측 EC",
        row=2, col=2
    )

    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        barmode="group"
    )

    st.plotly_chart(fig, use_container_width=True)

    # 시계열
    st.subheader("환경 변화 시계열")

    if school_option == "전체":
        schools_to_plot = env_data.keys()
    else:
        schools_to_plot = [school_option]

    for school in schools_to_plot:
        df = env_data[school]
        fig_ts = go.Figure()

        fig_ts.add_scatter(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], name="EC")

        fig_ts.add_hline(
            y=SCHOOL_EC_INFO[school],
            line_dash="dash",
            annotation_text="목표 EC"
        )

        fig_ts.update_layout(
            title=f"{school} 환경 변화",
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )

        st.plotly_chart(fig_ts, use_container_width=True)

    # 원본 데이터 + 다운로드
    with st.expander("환경 데이터 원본 보기 / 다운로드"):
        all_env_df = pd.concat(env_data.values(), ignore_index=True)
        st.dataframe(all_env_df, use_container_width=True)

        buffer = io.BytesIO()
        all_env_df.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ======================================================
# Tab 3: 생육 결과
# ======================================================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    growth_all = pd.concat(growth_data.values(), ignore_index=True)
    ec_group = growth_all.groupby("ec")["생중량(g)"].mean().reset_index()

    max_ec = ec_group.loc[ec_group["생중량(g)"].idxmax(), "ec"]

    c = st.columns(len(ec_group))
    for i, row in ec_group.iterrows():
        label = "⭐ 최적" if row["ec"] == max_ec else ""
        c[i].metric(f"EC {row['ec']}", f"{row['생중량(g)']:.2f} g", label)

    # EC별 비교 그래프
    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "평균 생중량",
            "평균 잎 수",
            "평균 지상부 길이",
            "개체수"
        )
    )

    fig2.add_bar(
        x=ec_group["ec"],
        y=ec_group["생중량(g)"],
        row=1, col=1
    )

    fig2.add_bar(
        x=growth_all.groupby("ec")["잎 수(장)"].mean().index,
        y=growth_all.groupby("ec")["잎 수(장)"].mean().values,
        row=1, col=2
    )

    fig2.add_bar(
        x=growth_all.groupby("ec")["지상부 길이(mm)"].mean().index,
        y=growth_all.groupby("ec")["지상부 길이(mm)"].mean().values,
        row=2, col=1
    )

    fig2.add_bar(
        x=growth_all.groupby("ec").size().index,
        y=growth_all.groupby("ec").size().values,
        row=2, col=2
    )

    fig2.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )

    st.plotly_chart(fig2, use_container_width=True)

    # 분포
    st.subheader("학교별 생중량 분포")
    fig_box = px.box(
        growth_all,
        x="school",
        y="생중량(g)",
        color="school"
    )
    fig_box.update_layout(
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig_box, use_container_width=True)

    # 상관관계
    st.subheader("상관관계 분석")
    c1, c2 = st.columns(2)

    with c1:
        fig_sc1 = px.scatter(
            growth_all,
            x="잎 수(장)",
            y="생중량(g)",
            color="school"
        )
        fig_sc1.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig_sc1, use_container_width=True)

    with c2:
        fig_sc2 = px.scatter(
            growth_all,
            x="지상부 길이(mm)",
            y="생중량(g)",
            color="school"
        )
        fig_sc2.update_layout(font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"))
        st.plotly_chart(fig_sc2, use_container_width=True)

    # 원본 데이터 + XLSX 다운로드
    with st.expander("생육 데이터 원본 보기 / 다운로드"):
        st.dataframe(growth_all, use_container_width=True)

        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


