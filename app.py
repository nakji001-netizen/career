import streamlit as st
import google.generativeai as genai
import json

# --- 1. 페이지 설정 및 디자인 (CSS) ---
st.set_page_config(
    page_title="고등학생 진로 탐색기",
    page_icon="🎓",
    layout="centered"
)

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: bold; color: #1e3a8a; text-align: center; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1.1rem; color: #4b5563; text-align: center; margin-bottom: 2rem; }
    .card { background-color: #ffffff; padding: 1.5rem; border-radius: 0.8rem; border: 1px solid #e5e7eb; 
            margin-bottom: 1.2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .card-title { font-size: 1.4rem; font-weight: bold; color: #2563eb; margin-bottom: 0.6rem; border-bottom: 2px solid #eff6ff; padding-bottom: 0.3rem;}
    .section-title { font-weight: bold; color: #374151; margin-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 모델 자동 선택 함수 (버전 변화 대응) ---
def get_best_model():
    try:
        # 사용 가능한 모델 목록 가져오기
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 'flash' 포함 모델 중 실험판(exp) 제외하고 정렬
        flash_models = sorted([m for m in available_models if 'flash' in m.lower() and 'exp' not in m.lower()])
        
        if flash_models:
            return flash_models[-1].replace("models/", "") # 최신 버전 반환
        return "gemini-1.5-flash" # 찾지 못할 경우 기본값
    except Exception:
        return "gemini-1.5-flash" # API 호출 실패 시 기본값

# --- 3. 사이드바: API 설정 ---
with st.sidebar:
    st.header("⚙️ 설정")
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        selected_model = get_best_model()
        st.success("✅ API 연결 성공")
        st.info(f"🤖 모델: {selected_model}")
    except Exception:
        st.error("⚠️ Secrets에 GOOGLE_API_KEY가 필요합니다.")
        api_key = None

# --- 4. 메인 화면: 입력 폼 ---
st.markdown('<div class="main-title">🎓 진로 탐색기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">당신의 꿈을 데이터로 분석하여 최적의 학과를 제안합니다.</div>', unsafe_allow_html=True)

with st.form("career_form"):
    col1, col2 = st.columns(2)
    with col1:
        job = st.text_input("🎯 희망 직업", placeholder="예: 로봇 공학자")
        interest = st.text_input("💡 관심 분야", placeholder="예: 자율주행, AI")
    with col2:
        hobby = st.text_input("🎨 취미 및 특기", placeholder="예: 프라모델 조립")
        subject = st.text_input("📚 선호 과목", placeholder="예: 물리, 수학")
    
    submit_btn = st.form_submit_button("학과 추천받기 ✨", type="primary", use_container_width=True)

# --- 5. 분석 로직 ---
if submit_btn:
    if not api_key:
        st.error("API 키가 설정되지 않았습니다.")
    elif not (job and interest and hobby and subject):
        st.warning("모든 항목을 입력해 주세요.")
    else:
        try:
            # [보완] 응답 스키마 설정: 모델이 바뀌어도 JSON 구조를 강제함
            generation_config = {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "majorName": {"type": "string"},
                            "introduction": {"type": "string"},
                            "reason": {"type": "string"},
                            "curriculum": {"type": "array", "items": {"type": "string"}},
                            "career": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["majorName", "introduction", "reason", "curriculum", "career"]
                    }
                }
            }

            model = genai.GenerativeModel(model_name=selected_model, generation_config=generation_config)
            
            prompt = f"희망직업: {job}, 관심분야: {interest}, 취미: {hobby}, 선호과목: {subject} 정보를 바탕으로 적합한 대학교 학과 3개를 추천해줘."

            with st.spinner("AI가 최적의 진로를 분석 중입니다..."):
                # --- 들여쓰기 오류 수정 완료 구역 ---
                response = model.generate_content(prompt)
                recommendations = json.loads(response.text)
                st.session_state['recommendations'] = recommendations
                # ---------------------------------

        except Exception as e:
            st.error(f"오류가 발생했습니다: {str(e)}")

# --- 6. 결과 표시 및 다운로드 ---
if 'recommendations' in st.session_state:
    data = st.session_state['recommendations']
    st.divider()
    
    report_text = "=== 진로 탐색 결과 보고서 ===\n\n"
    
    for rec in data:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📍 {rec['majorName']}</div>
            <p>{rec['introduction']}</p>
            <div class="section-title">✨ 추천 이유</div>
            <p>{rec['reason']}</p>
            <div class="section-title">📚 주요 커리큘럼</div>
            <p style="color: #6b7280; font-size: 0.9rem;">{', '.join(rec['curriculum'])}</p>
            <div class="section-title">🚀 졸업 후 진로</div>
            <p style="color: #6b7280; font-size: 0.9rem;">{', '.join(rec['career'])}</p>
        </div>
        """, unsafe_allow_html=True)
        
        report_text += f"▶ 학과: {rec['majorName']}\n- 이유: {rec['reason']}\n- 진로: {', '.join(rec['career'])}\n\n"

    st.download_button(
        label="📄 결과 보고서(.txt) 다운로드",
        data=report_text,
        file_name="career_report.txt",
        mime="text/plain",
        use_container_width=True
    )
