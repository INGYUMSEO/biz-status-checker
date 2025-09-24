
# 📄 국세청 사업자등록 상태 조회 (Streamlit)

국세청 오픈API로 여러 사업자등록번호의 **상태(계속/휴업/폐업)** 및 **과세유형** 등을 일괄 조회하고, 결과를 **엑셀로 다운로드**하는 웹 앱입니다.  
대용량 엑셀도 **시트/헤더/컬럼 지정 + 50~100건 배치 호출 + 대기 조절**로 안정적으로 처리합니다.

---

## 📦 구성
- `streamlit_app.py` – 앱 메인 코드  
- `requirements.txt` – 의존 라이브러리  
- `.streamlit/config.toml` *(선택)* – 업로드 용량 상향  
- `.streamlit/secrets.toml` *(로컬 전용)

- ⚠️ 로컬 테스트용 .streamlit/secrets.toml(SERVICE_KEY) 를 통하여 샘플데이터 및 여러 데이터 테스트 확인 완료
  
---

## 🔑 API 키
- **로컬**: `.streamlit/secrets.toml`
  ```toml
  SERVICE_KEY="디코딩된_공공데이터포털_API키"
  
Streamlit Cloud: App → Edit secrets에 동일 키 이름 등록

🖱️ 사용 방법

서비스키 입력(또는 secrets 자동 로드)

엑셀 업로드(.xlsx) → 시트 선택 → 헤더 행(0/1/2)

사업자번호 컬럼 지정(필수), 업체명 컬럼(선택)

⚙️ 고급 설정: 배치 크기(50~100), 대기(0.5~1.0s) 조절

진행률 확인 → 결과 표 확인 → 엑셀 다운로드


📥 입력 형식 예시
- 업체명	사업자번호
- ㈜샘플	1234567890

하이픈 등은 자동 제거, 숫자만 10자리로 보정합니다. 


📤 출력 컬럼 설명
컬럼	의미
업체명	입력에서 선택한 업체명(선택)
사업자번호	입력 원본 사업자번호
사업자등록번호_norm	숫자만 10자리로 정규화
b_no	응답의 사업자등록번호
b_stt	납세자상태(명칭): 계속/휴업/폐업 등
b_stt_cd	납세자상태 코드(예: 01 계속, 02 휴업, 03 폐업)
tax_type	과세유형(명칭): 일반/간이/면세 등
tax_type_cd	과세유형 코드
end_dt	폐업일자(YYYYMMDD)
utcc_yn	단위과세전환폐업 여부(Y/N)
tax_type_change_dt	최근 과세유형 전환일(YYYYMMDD)
invoice_apply_dt	세금계산서 적용일(YYYYMMDD)
rbf_tax_type	직전 과세유형(명칭)
rbf_tax_type_cd	직전 과세유형 코드

⚙️ 팁

중복/결측 제거 후 조회하면 빨라집니다.

429/지연 시 배치 ↓, 대기 ↑ 로 조정.

업로드 한도 상향(선택): .streamlit/config.toml



