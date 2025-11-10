import streamlit as st
import config
from utils.session_state import init_session_state
from components.upload_step import run_upload_step

# 세션 초기화
init_session_state()

# 사이드바 제거: 소개/사용방법/링크 섹션 비활성화

# 메인 타이틀
st.title("PDF AI 분석 도구")
st.markdown("""
PDF 문서에서 원하는 항목만 안전하게 추출하기 위해 페이지 단위의 단계적 접근을 사용합니다.  

**단계적 접근:**  
1️⃣ **항목 선택**: 등급/기술자격/학력/근무처/상훈/벌점·제재/교육훈련 중 하나를 선택  
2️⃣ **페이지 준비**: 각 페이지 좌상단에 물리 페이지 번호를 삽입하고 미리보기 이미지를 생성  
3️⃣ **페이지별 추출**: PDF를 1페이지씩 개별 API 호출로 처리하여 선택한 항목만 JSON으로 추출  
4️⃣ **최종 취합**: 모든 페이지의 추출값을 페이지 순서대로 합쳐 표/CSV와 함께 ‘최종 취합 결과’로 제공  

페이지별 추출 결과는 테이블과 CSV로 제공되며, 페이지 이미지를 미리볼 수 있습니다.
""")

# PDF 업로드 및 분석 실행
run_upload_step()
