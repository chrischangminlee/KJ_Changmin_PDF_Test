import streamlit as st
import pandas as pd
import io
import os
import unicodedata
from PyPDF2 import PdfReader
from services.pdf_service import annotate_pdf_with_page_numbers, convert_pdf_to_images, extract_single_page_pdf
from services.gemini_service import extract_category_from_page, consolidate_items_with_llm, split_items_one_per_line

def run_upload_step():
    st.header("PDF 업로드 및 항목 선택")

    # 예시 PDF 로드 기능
    def load_example_pdf(example_pdf_path: str):
        """주어진 경로의 예시 PDF 파일을 로드하여 바이트로 반환"""
        try:
            with open(example_pdf_path, "rb") as f:
                return f.read()
        except Exception as e:
            st.error(f"예시 PDF 로드 실패: {e}")
            return None

    # 파일명 정규화 기반 경로 탐색 유틸
    def resolve_example_pdf_path(dir_path: str, target_filename_nfc: str):
        """디렉토리 내 파일명을 유니코드 정규화(NFC/NFD)하여 대상 파일을 탐색"""
        try:
            for name in os.listdir(dir_path):
                # 파일명 비교 시 NFC 기준으로 비교
                if unicodedata.normalize('NFC', name) == target_filename_nfc:
                    return os.path.join(dir_path, name)
                # 보수적으로 NFD 비교도 수행
                if unicodedata.normalize('NFD', name) == unicodedata.normalize('NFD', target_filename_nfc):
                    return os.path.join(dir_path, name)
        except FileNotFoundError:
            return None
        return None

    # 예시 PDF 불러오기 / 제거 버튼
    st.write("예시 PDF를 활용하거나, PDF를 불러오세요")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.session_state.get('example_pdf_loaded', False):
            if st.button("🗑️ 예시 PDF 제거", type="secondary"):
                st.session_state['example_pdf_loaded'] = False
                for k in ['example_pdf_bytes', 'example_pdf_label', 'example_pdf_path']:
                    if k in st.session_state:
                        del st.session_state[k]
                st.rerun()
        else:
            # 좌/우에 두 개의 예시 PDF 불러오기 버튼 배치
            pass
    if not st.session_state.get('example_pdf_loaded', False):
        with col2:
            if st.button("📄 예시 PDF (구본명_경력증명서) 불러오기", type="secondary", key="load_example_gubm"):
                target = "구본명_경력증명서(24.09.12).pdf"
                path = resolve_example_pdf_path("Filereference", target)
                if not path:
                    st.error(f"예시 PDF 로드 실패: Filereference 폴더에서 '{target}' 파일을 찾을 수 없습니다.")
                    st.stop()
                example_pdf_bytes = load_example_pdf(path)
                if example_pdf_bytes:
                    st.session_state['example_pdf_loaded'] = True
                    st.session_state['example_pdf_bytes'] = example_pdf_bytes
                    st.session_state['example_pdf_label'] = "구본명_경력증명서"
                    st.session_state['example_pdf_path'] = path
                    st.success("✅ 예시 PDF가 로드되었습니다!")
                    st.rerun()
        with col3:
            if st.button("📄 예시 PDF (윤덕철_경력증명서) 불러오기", type="secondary", key="load_example_yundc"):
                target = "윤덕철_경력증명서(23.11.13).pdf"
                path = resolve_example_pdf_path("Filereference", target)
                if not path:
                    st.error(f"예시 PDF 로드 실패: Filereference 폴더에서 '{target}' 파일을 찾을 수 없습니다.")
                    st.stop()
                example_pdf_bytes = load_example_pdf(path)
                if example_pdf_bytes:
                    st.session_state['example_pdf_loaded'] = True
                    st.session_state['example_pdf_bytes'] = example_pdf_bytes
                    st.session_state['example_pdf_label'] = "윤덕철_경력증명서"
                    st.session_state['example_pdf_path'] = path
                    st.success("✅ 예시 PDF가 로드되었습니다!")
                    st.rerun()

    with st.form("upload_form"):
        col3, col4 = st.columns(2)
        with col3:
            if st.session_state.get('example_pdf_loaded', False):
                selected_label = st.session_state.get('example_pdf_label', '예시 PDF')
                st.info(f"📄 **예시 PDF ({selected_label})** 가 선택되었습니다.")
                pdf_file = None
            else:
                pdf_file = st.file_uploader("PDF 파일을 선택하세요", type=['pdf'])

        with col4:
            category = st.selectbox(
                "추출 항목 선택",
                [
                    "등급",
                    "기술자격",
                    "학력",
                    "근무처",
                    "상훈",
                    "벌점 및 제재사항",
                    "교육훈련",
                ],
            )

        submitted = st.form_submit_button("추출 시작", type="primary")

    if submitted:
        # PDF 파일 확인
        if st.session_state.get('example_pdf_loaded', False):
            pdf_bytes_to_process = st.session_state['example_pdf_bytes']
        elif pdf_file:
            pdf_bytes_to_process = pdf_file.read()
        else:
            st.error("PDF 파일을 선택하거나 예시 PDF를 로드해주세요.")
            st.stop()

        # 각 단계별 placeholder 생성
        step1_placeholder = st.empty()
        step2_placeholder = st.empty()
        step3_placeholder = st.empty()
        
        try:
            # 세션 초기화
            st.session_state.analysis_results = []
            st.session_state.category = category

            # 1단계: PDF 페이지 번호 삽입
            step1_placeholder.info("📝 **1/3단계:** PDF에 페이지 번호 삽입 중...")
            numbered_bytes = annotate_pdf_with_page_numbers(pdf_bytes_to_process)
            st.session_state.original_pdf_bytes = numbered_bytes
            step1_placeholder.success("📝 **1/3단계:** PDF에 페이지 번호 삽입 완료 ✅")

            # 2단계: PDF를 이미지로 변환
            step2_placeholder.info("🖼️ **2/3단계:** PDF를 이미지로 변환 중...")
            st.session_state.pdf_images = convert_pdf_to_images(numbered_bytes)
            
            if not st.session_state.pdf_images:
                step2_placeholder.warning("🖼️ **2/3단계:** PDF 이미지 변환 실패 ⚠️ (분석은 계속 진행)")
            else:
                step2_placeholder.success("🖼️ **2/3단계:** PDF를 이미지로 변환 완료 ✅")

            # 3단계: 페이지별 AI 추출 실행
            step3_placeholder.info("🤖 **3/3단계:** 페이지별 정보 추출 중... (시간이 다소 걸릴 수 있습니다)")

            status_placeholder = st.empty()
            reader = PdfReader(io.BytesIO(numbered_bytes))
            total_pages = len(reader.pages)
            page_results = {}
            progress = st.progress(0)

            for page_num in range(1, total_pages + 1):
                progress.progress(page_num / total_pages)
                status_placeholder.info(f"📄 페이지 {page_num}/{total_pages} 처리 중...")
                single_page_bytes = extract_single_page_pdf(numbered_bytes, page_num)
                if not single_page_bytes:
                    continue
                try:
                    items = extract_category_from_page(single_page_bytes, category, status_placeholder)
                    if items:
                        page_results[page_num] = items
                except Exception as e:
                    status_placeholder.warning(f"⚠️ 페이지 {page_num} 처리 실패: {e}")
                    continue

            progress.empty()
            status_placeholder.empty()

            st.session_state.page_results = page_results

            step3_placeholder.success("🤖 **3/3단계:** 페이지별 정보 추출 완료 ✅")

            # 모든 진행 단계 블록 제거
            step1_placeholder.empty()
            step2_placeholder.empty()
            step3_placeholder.empty()
            
            # 결과 표시
            if not st.session_state.page_results:
                st.warning("관련 항목을 찾지 못했습니다.")
            else:
                display_extraction_results()

        except Exception as e:
            import traceback
            # 모든 진행 단계 블록 제거
            step1_placeholder.empty()
            step2_placeholder.empty()
            step3_placeholder.empty()
            
            st.error(f"❌ **오류 발생:** {str(e)}")
            
            # 디버깅을 위한 상세 오류 정보
            st.error("상세 오류 정보:")
            st.code(traceback.format_exc())
            st.error("위 오류가 지속되면 페이지를 새로고침하고 다시 시도해주세요.")
    
    # 이전 추출 결과가 있으면 표시
    elif hasattr(st.session_state, 'page_results') and st.session_state.page_results:
        display_extraction_results()


def display_analysis_results():
    """분석 결과를 테이블 형태로 표시"""
    st.header("📊 분석 결과")
    st.write(f"**원본 질문:** {st.session_state.user_prompt}")
    
    # 개선된 프롬프트가 있으면 표시
    if hasattr(st.session_state, 'refined_prompt') and st.session_state.refined_prompt != st.session_state.user_prompt:
        st.write(f"**분석에 사용된 질문:** {st.session_state.refined_prompt}")
    
    # 최종 요약은 아래에서 테이블 생성 후 표시
    
    # 결과 데이터 준비 - 상과 중 모두 포함
    table_data = []
    for page_num in st.session_state.relevant_pages:
        if page_num in st.session_state.page_info:
            info = st.session_state.page_info[page_num]
            # 답변이 비어있는 경우 처리
            answer = info['page_response']
            if not answer or answer.strip() == "":
                answer = "관련 내용이 포함된 페이지"
            
            table_data.append({
                '페이지': page_num,
                '답변': answer,
                '관련도': info['relevance'],
            })
    
    if table_data:
        # 2단계: 답변 검증 (refined_prompt에 실제로 답변하는지 확인)
        if hasattr(st.session_state, 'refined_prompt'):
            validation_placeholder = st.empty()
            validated_data = validate_answers_with_prompt(
                table_data,
                st.session_state.refined_prompt,
                validation_placeholder
            )
            validation_placeholder.empty()
            
            # 검증된 데이터로 업데이트
            table_data = validated_data
        
        # 3단계: 최종 요약 생성 (검증된 답변들로만)
        if table_data and hasattr(st.session_state, 'refined_prompt'):
            summary_placeholder = st.empty()
            final_summary = generate_final_summary(
                table_data,
                st.session_state.refined_prompt,
                summary_placeholder
            )
            summary_placeholder.empty()
            st.session_state.final_summary = final_summary
            
        # 최종 요약 표시
        if hasattr(st.session_state, 'final_summary') and st.session_state.final_summary:
            st.markdown("### 📋 최종 답변")
            st.info(st.session_state.final_summary)
            st.divider()
    
    if table_data:
        # DataFrame 생성
        df = pd.DataFrame(table_data)
        
        # 테이블 표시
        st.markdown("### 📊 분석 결과 테이블")
        
        # 테이블과 버튼을 함께 표시
        col_headers = st.columns([1, 7, 2])
        with col_headers[0]:
            st.markdown("**페이지**")
        with col_headers[1]:
            st.markdown("**답변**")
        with col_headers[2]:
            st.markdown("**상세보기 (하단에 표기됩니다)**")
        
        # 구분선
        st.markdown("---")
        
        # 각 행 표시
        for _, row in df.iterrows():
            cols = st.columns([1, 7, 2])
            
            with cols[0]:
                st.write(f"{row['페이지']}")
            
            with cols[1]:
                st.write(row['답변'])
            
            with cols[2]:
                # 미리보기 버튼
                if st.button("🔍 미리보기", key=f"preview_{row['페이지']}"):
                    st.session_state.preview_page = row['페이지']
                    st.session_state.preview_data = row
        
        st.markdown("---")
        
        # CSV 다운로드 버튼 추가
        csv_buffer = io.StringIO()
        # 관련도 컬럼 제외하고 CSV 생성
        df_csv = df[['페이지', '답변']]
        df_csv.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_data = csv_buffer.getvalue().encode('utf-8-sig')
        
        st.download_button(
            label="📥 페이지 별 결과 CSV 형태로 다운받기",
            data=csv_data,
            file_name=f"분석결과_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv;charset=utf-8-sig",
            type="primary"
        )

        st.markdown("---")
        
        # 미리보기 표시
        if hasattr(st.session_state, 'preview_page') and st.session_state.preview_page:
            st.markdown("---")
            
            # 미리보기 섹션
            st.markdown("### 📄 페이지 {} 미리보기".format(st.session_state.preview_page))
            
            page_num = st.session_state.preview_page
            page_data = st.session_state.preview_data
            
            # 닫기 버튼과 정보를 한 줄에 표시
            col1, col2, col3 = st.columns([4, 4, 1])
            with col1:
                st.write(f"**관련도:** {'🔴 상' if page_data['관련도'] == '상' else '🟡 중'}")
            with col2:
                st.write(f"**답변:** {page_data['답변']}")
            with col3:
                if st.button("❌ 닫기", key="close_preview"):
                    del st.session_state.preview_page
                    del st.session_state.preview_data
                    st.rerun()
            
            # 이미지 표시
            if hasattr(st.session_state, 'pdf_images') and st.session_state.pdf_images:
                page_idx = page_num - 1
                if 0 <= page_idx < len(st.session_state.pdf_images):
                    st.image(
                        st.session_state.pdf_images[page_idx], 
                        caption=f"페이지 {page_num}", 
                        use_column_width=True
                    )
            
        
        
        # 사용 팁
        st.info("💡 **팁:** '👁️ 보기' 버튼을 클릭하면 해당 페이지를 미리볼 수 있습니다.")
    
    else:
        st.warning("⚠️ 직접적인 답변이 포함된 페이지가 없습니다. (관련도 '상' 페이지가 없음)")
    
    # 새로운 분석 시작 버튼
    if st.button("🔄 새로운 분석 시작", type="primary"):
        # 세션 상태 초기화
        for key in ['relevant_pages', 'page_info', 'user_prompt', 'refined_prompt', 'final_summary',
                    'original_pdf_bytes', 'pdf_images', 'example_pdf_loaded', 'example_pdf_bytes',
                    'page_results', 'page_results_norm', 'category']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()


def display_extraction_results():
    """페이지별 추출 결과를 테이블과 미리보기, CSV로 제공"""
    st.header("📊 추출 결과")
    st.write(f"**추출 항목:** {st.session_state.get('category', '')}")

    # 페이지별 결과 LLM 정규화(한 항목당 1줄) - 최초 1회 수행 후 세션에 캐시
    if 'page_results_norm' not in st.session_state:
        norm = {}
        status_ph = st.empty()
        pages = sorted(st.session_state.page_results.keys())
        progress = st.progress(0)
        for idx, page_num in enumerate(pages):
            progress.progress((idx + 1) / len(pages))
            status_ph.info(f"🧩 페이지 {page_num} 항목 정리 중…")
            items = st.session_state.page_results.get(page_num, [])
            norm_items = split_items_one_per_line(items, st.session_state.get('category', ''), status_ph)
            norm[page_num] = norm_items
        progress.empty()
        status_ph.empty()
        st.session_state.page_results_norm = norm

    # 페이지별 결과 구성 (정규화 결과 사용)
    rows = []
    for page_num, items in sorted(st.session_state.page_results_norm.items()):
        rows.append({
            '페이지': page_num,
            '추출 결과': "\n".join(items) if items else ""
        })

    if not rows:
        st.warning("표시할 결과가 없습니다.")
        return

    df = pd.DataFrame(rows)

    st.markdown("### 📊 페이지별 결과")
    col_headers = st.columns([1, 7, 2])
    with col_headers[0]:
        st.markdown("**페이지**")
    with col_headers[1]:
        st.markdown("**추출 결과**")
    with col_headers[2]:
        st.markdown("**상세보기 (하단에 표기됩니다)**")

    st.markdown("---")

    for _, row in df.iterrows():
        cols = st.columns([1, 7, 2])
        with cols[0]:
            st.write(f"{row['페이지']}")
        with cols[1]:
            st.text(row['추출 결과'])
        with cols[2]:
            if st.button("🔍 미리보기", key=f"preview_{row['페이지']}"):
                st.session_state.preview_page = row['페이지']
                st.session_state.preview_data = row

    st.markdown("---")

    # CSV 다운로드
    csv_buffer = io.StringIO()
    df_csv = df[['페이지', '추출 결과']]
    df_csv.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_data = csv_buffer.getvalue().encode('utf-8-sig')

    st.download_button(
        label="📥 페이지 별 결과 CSV 형태로 다운받기",
        data=csv_data,
        file_name=f"추출결과_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv;charset=utf-8-sig",
        type="primary"
    )

    st.markdown("---")

    # 미리보기
    if hasattr(st.session_state, 'preview_page') and st.session_state.preview_page:
        st.markdown("---")
        st.markdown("### 📄 페이지 {} 미리보기".format(st.session_state.preview_page))
        page_num = st.session_state.preview_page
        page_data = st.session_state.preview_data
        col1, col2 = st.columns([8, 1])
        with col1:
            st.markdown("**추출 결과:**")
            st.text(page_data['추출 결과'])
        with col2:
            if st.button("❌ 닫기", key="close_preview"):
                del st.session_state.preview_page
                del st.session_state.preview_data
                st.rerun()

        if hasattr(st.session_state, 'pdf_images') and st.session_state.pdf_images:
            page_idx = page_num - 1
            if 0 <= page_idx < len(st.session_state.pdf_images):
                st.image(
                    st.session_state.pdf_images[page_idx], 
                    caption=f"페이지 {page_num}", 
                    use_column_width=True
                )

    # 최종 취합 + LLM 정리 결과
    st.markdown("### 📋 최종 취합 결과")
    all_items = []
    # 정규화된 결과를 취합
    for items in st.session_state.page_results_norm.values():
        all_items.extend(items)

    if not all_items:
        st.write("없음")
        return

    # 원본 취합값(정규화 전, 페이지별 추출 원문)과 LLM 정리 결과를 함께 제공
    raw_items = []
    for items in st.session_state.page_results.values():
        raw_items.extend(items)
    with st.expander("원본 취합 목록 보기", expanded=False):
        st.text("\n".join(raw_items))

    status_ph = st.empty()
    consolidated = consolidate_items_with_llm(all_items, st.session_state.get('category', ''), status_ph)
    status_ph.empty()

    st.markdown("#### 🧠 LLM 정리 결과 (정규화/중복 제거, 항목당 1줄)")
    if consolidated:
        # 줄바꿈 렌더링을 위해 마크다운 목록 사용
        st.markdown("\n".join([f"- {x}" for x in consolidated]))
    else:
        st.write("정리 결과가 없습니다.")
