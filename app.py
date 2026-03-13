import streamlit as st
import google.generativeai as genai
import json
import time

# --- 1. 페이지 설정 및 스타일 ---
st.set_page_config(
    page_title="고등학생 진로 탐색기",
    page_icon="🎓",
    layout="centered"
)

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: bold; color: #1f2937; text-align: center; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1.1rem; color: #6b7280; text-align: center; margin-bottom: 2rem; }
    .card { background-color: #f9fafb; padding: 1.5rem; border-radius: 0.8rem; border: 1px solid #e5e7eb; margin-bottom: 1.5rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); }
    .card-title { font-size: 1.4rem; font-weight: bold; color: #2563eb; margin-bottom: 0.8rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.3rem; }
    .section-title { font-weight: bold; color: #374151; margin-top: 1rem; display: flex; align-items: center; gap: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 백엔드 로직 (모델 관리 및 캐싱) ---

@st.cache_data(ttl=3600)
def get_available_models(api_key):
    """사용 가능한 최신 Gemini 모델 목록을 가져옴"""
    try:
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                models.append(m.name.replace('models/', ''))
        # flash 모델을 우선적으로 추천 (할당량 넉넉함)
        return sorted(models, key=lambda x: ("flash" not in x, x))
    except Exception:
        return ["gemini-1.5-flash", "gemini-1.5-pro"]

@st.cache_data(show_spinner=False)
def get_career_recommendation(api_key, model_name, user_data):
    """AI에게 학과 추천 요청 (재시도 로직 포함)"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    
    prompt = f"""
    고등학생 진로 상담가로서 다음 정보를 바탕으로 적합한 대학교 학과 3개를 추천해줘.
    - 희망 직업: {user_data['job']}
    - 관심 분야: {user_data['interest']}
    - 취미/특기: {user_data['hobby']}
    - 선호 과목: {user_data['subject']}

    반드시 아래 JSON 형식을 지켜서 응답해줘:
    [
        {{
            "majorName": "학과명",
            "introduction": "학과 소개",
            "reason": "추천 이유",
            "curriculum": ["과목1", "과목2"],
            "career": ["직업1", "직업2"]
        }}
    ]
    """

    max_retries = 3
    for i in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
        except Exception as e:
            if "429" in str(e) and i < max_retries - 1:
                time.sleep(5 * (i + 1)) # 지수 백오프
                continue
            raise e

# --- 3. 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.secrets.get("GOOGLE_API_KEY")
    
    if api_key:
        model_options = get_available_models(api_key)
        selected_model = st.selectbox("사용할 AI 모델", model_options, 
                                     help="무료 티어에서는 'flash' 모델이 가장 안정적입니다.")
    else:
        st.error("API 키가 없습니다. Secrets 설정을 확인하세요.")
        st.stop()

# --- 4. 메인 화면 및 입력 폼 ---
st.markdown('<div class="main-title">🎓 진로 탐색기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI가 당신의 기록을 분석해 최적의 학과를 추천합니다</div>', unsafe_allow_html=True)

with st.form("career_form"):
    col1, col2 = st.columns(2)
    with col1:
        job = st.text_input("🎯 희망 직업", placeholder="예: 데이터 과학자")
        interest = st.text_input("💡 관심 분야", placeholder="예: 기후 변화, 로봇")
    with col2:
        hobby = st.text_input("🎨 취미 및 특기", placeholder="예: 악기 연주, 운동")
        subject = st.text_input("📚 선호 과목", placeholder="예: 확률과 통계, 영어")
    
    submit_btn = st.form_submit_button("추천 학과 분석 시작 ✨", type="primary", use_container_width=True)

# --- 5. 결과 출력 섹션 ---
if submit_btn:
    if not (job and interest and hobby and subject):
        st.warning("모든 항목을 입력해야 정확한 분석이 가능합니다!")
    else:
        user_input_data = {"job": job, "interest": interest, "hobby": hobby, "subject": subject}
        
        try:
            with st.spinner(f"AI가 {selected_model} 모델을 통해 분석 중입니다..."):
                recommendations = get_career_recommendation(api_key, selected_model, user_input_data)
                st.session_state['results'] = recommendations
                st.balloons()
        except Exception as e:
            if "429" in str(e):
                st.error("현재 요청량이 너무 많습니다. 'flash' 모델로 변경하시거나 1분 뒤에 다시 시도해주세요.")
            else:
                st.error(f"분석 중 오류가 발생했습니다: {e}")

# 결과 표시 (세션 상태 활용)
if 'results' in st.session_state:
    st.divider()
    st.subheader("📋 AI 추천 결과")
    
    txt_output = "고등학생 진로 탐색 결과 보고서\n\n"
    
    for rec in st.session_state['results']:
        with st.container():
            st.markdown(f"""
            <div class="card">
                <div class="card-title">📍 {rec['majorName']}</div>
                <p><b>학과 소개:</b> {rec['introduction']}</p>
