import streamlit as st
import pandas as pd
import requests, time, io
from typing import List

# ---- 기본 설정
st.set_page_config(page_title="사업자등록 상태 조회", layout="centered")
st.title("📄 국세청 사업자등록 상태 조회 서비스")

# ---- API 키 입력(우선: secrets, 없으면 입력창으로)
service_key = st.secrets.get("SERVICE_KEY", "")
service_key = st.text_input("🔑 공공데이터포털 서비스키(디코딩된 값)", value=service_key, type="password")

API_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"
HEADERS = {"Content-Type": "application/json; charset=utf-8"}

# ---- 엑셀 업로드
uploaded_file = st.file_uploader("📁 엑셀 파일 업로드 (.xlsx)", type="xlsx")

# ---- 유틸
def pick_biz_column(df: pd.DataFrame) -> str:
    """사업자번호 컬럼 자동 탐지"""
    candidates = ["사업자등록번호", "사업자번호"]
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        if "사업자" in c and "번" in c:
            return c
    raise KeyError("사업자번호 컬럼을 찾을 수 없습니다. (예: '사업자등록번호' 또는 '사업자번호')")

def normalize_biznos(s: pd.Series) -> pd.Series:
    """숫자만 남기고 10자리로 zfill"""
    return (s.astype(str).str.replace(r"\D", "", regex=True).str.zfill(10))

def batched(lst: List[str], size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i+size]

def call_api(bnos: List[str], retries: int = 3, wait: float = 1.0):
    payload = {"b_no": bnos}
    for attempt in range(1, retries+1):
        try:
            resp = requests.post(API_URL,
                                 headers=HEADERS,
                                 params={"serviceKey": service_key},
                                 json=payload,
                                 timeout=20)
            if resp.status_code == 200:
                return resp.json().get("data", [])
            else:
                st.warning(f"요청 실패 {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            st.warning(f"예외 발생(시도 {attempt}/{retries}): {e}")
        time.sleep(wait * attempt)  # 지수 백오프
    return []

# ---- 본 로직
if uploaded_file:
    if not service_key:
        st.error("서비스키를 입력해주세요.")
        st.stop()

    # ========= [대용량 안전 로더] : 시트/헤더/컬럼 지정 + 필요한 컬럼만 로드 =========
    file_bytes = uploaded_file.getvalue()
    excel_io = io.BytesIO(file_bytes)

    # 시트 선택
    xls = pd.ExcelFile(excel_io, engine="openpyxl")
    sheet = st.selectbox("시트 선택", xls.sheet_names)

    # 헤더 자동 추정(0/1/2) + 수동 선택 허용
    def guess_header_row(bytes_data, sheet_name):
        for h in [0, 1, 2]:
            tmp = pd.read_excel(io.BytesIO(bytes_data), sheet_name=sheet_name, nrows=50, header=h, dtype=str)
            try:
                _ = pick_biz_column(tmp)
                return h
            except Exception:
                pass
        return 0

    header_guess = guess_header_row(file_bytes, sheet)
    header = st.selectbox("헤더 행 선택", [0, 1, 2], index=header_guess)

    # 미리보기로 컬럼 후보 확인
    preview = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, nrows=200, header=header, dtype=str)
    try:
        auto_biz_col = pick_biz_column(preview)
    except Exception:
        auto_biz_col = preview.columns[0]  # 아무거나 기본값

    biz_col = st.selectbox(
        "사업자번호 컬럼",
        preview.columns.tolist(),
        index=(preview.columns.tolist().index(auto_biz_col) if auto_biz_col in preview.columns else 0),
    )

    name_col = st.selectbox(
        "업체명 컬럼(선택)",
        ["<없음>"] + preview.columns.tolist(),
        index=(preview.columns.tolist().index("업체명")+1 if "업체명" in preview.columns else 0),
    )

    usecols = [biz_col] + ([] if name_col == "<없음>" else [name_col])

    # 본 로드: 필요한 컬럼만, 문자열로 읽기(메모리/속도 ↑)
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=header, usecols=usecols, dtype=str, engine="openpyxl")
    st.info(f"건수: {len(df):,} | 결측: {df[biz_col].isna().sum():,} | 중복: {df[biz_col].duplicated().sum():,}")

    # ========= [정규화/조회/병합/다운로드] 기존 로직 계속 사용 =========
    df = df.copy()
    df["사업자등록번호_norm"] = normalize_biznos(df[biz_col])
    biz_nums = df["사업자등록번호_norm"].dropna().tolist()
    if not biz_nums:
        st.error("사업자번호가 비어 있습니다.")
        st.stop()

    # 고급 설정(레이트리밋 조절) - 덮어쓰기 금지!
    with st.expander("⚙️ 고급 설정", expanded=False):
        chunk_size = st.slider("요청 배치 크기", 50, 500, 100, 50)
        extra_delay = st.slider("호출 간 대기(초)", 0.0, 2.0, 0.5, 0.1)

    results = []
    progress = st.progress(0, text="🔍 조회 준비 중...")
    done, total = 0, len(biz_nums)

    for chunk in batched(biz_nums, chunk_size):
        data = call_api(chunk)
        results.extend(data)
        done += len(chunk)
        progress.progress(min(done/total, 1.0), text=f"조회 중... {done}/{total}")
        time.sleep(extra_delay)  # 추가 대기(선택)

    result_df = pd.DataFrame(results)
    merged_df = df.merge(result_df, left_on="사업자등록번호_norm", right_on="b_no", how="left")

    st.success("✅ 조회 완료")

    # 표시 컬럼 구성(업체명 컬럼명이 '업체명'이 아닐 수도 있으니 동적으로)
    show_cols = []
    if name_col != "<없음>" and name_col in merged_df.columns:
        show_cols.append(name_col)
    show_cols += [biz_col, "사업자등록번호_norm"]
    for c in ["b_stt", "tax_type", "end_dt"]:
        if c in merged_df.columns:
            show_cols.append(c)

    st.dataframe(merged_df[show_cols] if show_cols else merged_df, use_container_width=True)

    # 안전한 엑셀 다운로드
    buf = io.BytesIO()
    merged_df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    st.download_button(
        label="💾 결과 엑셀 다운로드",
        data=buf.getvalue(),
        file_name="사업자등록상태_조회결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

