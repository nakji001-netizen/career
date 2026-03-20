import streamlit as st
import google.generativeai as genai
import json

# --- 1. 페이지 설정 및 스타일 ---
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
    .section-title { font-weight: bold; color: #374151; margin-top: 1rem; display: flex; align-items: center; gap: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 모델 자동 선택 함수 (유지보수 핵심) ---
def get_best_flash_model():
    try:
        # 지원하는 모델 목록 가져오기
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 1순위: 'flash' 포함된 정식 버전 중 최신 버전
        flash_models = sorted([m for m in available_models if 'flash' in m.lower() and 'exp' not in m.lower()])
        if flash_models:
            return flash_models[-1]
        
        # 2순위: 'flash'가 없으면 전체 목록 중 최신 모델
        return available_models[-1]
    except Exception:
        # 3순위: API 호출 실패 시 현재 기준 안정화 버전 강제 지정
        return "models/gemini-2.0-flash"

# --- 3. 사이드바 설정 ---
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        selected_model_path = get_best_flash_model()
        selected_model_name = selected_model_path.replace("models/", "")
        
        st.success("✅ API 연결 성공")
        st.info(f"🤖 사용 모델: **{selected_model_name}**")
    except Exception as e:
        st.error("⚠️ API 키를 확인해주세요.")
        api_key = None

# --- 4. 메인 UI ---
st.markdown('<div class="main-title">🎓 진로 탐색기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">당신의 관심사와 강점을 바탕으로 최적의 학과를 추천합니다.</div>', unsafe_allow_html=True)

with st.form("career_form"):
    col1, col2 = st.columns(2)
    with col1:
        job = st.text_input("🎯 희망 직업", placeholder="예: 데이터 과학자")
        interest = st.text_input("💡 관심 분야", placeholder="예: 기후 변화, 심리학")
    with col2:
        hobby = st.text_input("🎨 취미 및 특기", placeholder="예: 악기 연주, 코딩")
        subject = st.text_input("📚 선호 과목", placeholder="예: 확률과 통계, 영어")
    
    submit_btn = st.form_submit_button("학과 추천받기 ✨", type="primary", use_container_width=True)

# --- 5. 로직 실행 ---
if submit_btn:
    if not api_key:
        st.error("API Key 설정이 필요합니다.")
    elif not (job and interest and hobby and subject):
        st.warning("모든 필드를 입력해주세요.")
    else:
        try:
            # [핵심] JSON 스키마 강제 정의: 모델이 바뀌어도 구조를 유지하게 함
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

            model = genai.GenerativeModel(
                model_name=selected_model_name,
                generation_config=generation_config
            )

            prompt = f"""
            당신은 고등학생을 위한 전문 진로 상담가입니다. 다음 정보를 바탕으로 가장 적합한 대학교 학과 3개를 추천하세요.
            - 희망 직업: {job}
            - 관심 분야: {interest}
            - 취미/특기: {hobby}
            - 선호 과목: {subject}
            """

            with st.spinner("AI가 최적의 진로를 분석 중입니다..."):
