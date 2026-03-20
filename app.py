import streamlit as st
import google.generativeai as genai
import json
import time

# --- 1. 페이지 설정 및 디자인 ---
st.set_page_config(
    page_title="고등학생 진로 탐색기",
    page_icon="🎓",
    layout="centered"
)

st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: bold; color: #1e3a8a; text-align: center; margin-bottom: 0.5rem; }
    .sub-title { font-size: 1.1rem; color: #4b5563; text-align: center; margin-bottom: 2rem; }
    .section-title { font-weight: bold; color: #374151; margin-top: 1rem; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 로직 함수 ---

def get_best_model():
    """사용 가능한 최신 Flash 모델을 자동 탐색"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = sorted([m for m in available_models if 'flash' in m.lower() and 'exp' not in m.lower()])
        
        if flash_models:
            return flash_models[-1].replace("models/", "")
        return "gemini-2.5-flash"
    except Exception:
        return "gemini-2.5-flash"

@st.cache_data(show_spinner=False, ttl=86400)
def get_career_recommendations(model_name, job, interest, hobby, subject):
    """API 호출 최적화(캐싱) 및 에러 방어 로직이 적용된 분석 함수"""
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

    model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
    prompt = f"희망직업: {job}, 관심분야: {interest}, 취미: {hobby}, 선호과목: {subject} 정보를 바탕으로 적합한 대학교 학과 3개를 추천해줘."

    max_retries = 3
    for i in range(max_retries):
        try:
            response = model.generate_content(prompt)
            if not response.text:
                raise ValueError("AI가 콘텐츠를 생성하지 못했습니다.")
            # 개선 3: JSON 디코딩 에러 방어
            return json.loads(response.text)
        except json.JSONDecodeError:
            raise ValueError("AI 응답을 분석하는 중 오류가 발생했습니다. 다시 시도해 주세요.")
        except Exception as e:
            if "429" in str(e) and i < max_retries - 1:
                time.sleep(3 * (i + 1))
                continue
            else:
                raise e

# --- 3. 사이드바: API 설정 ---
# 개선 2: 변수 초기화를 통해 잠재적인 NameError 방지
api_key = None
selected_model = "모델 확인 불가"

with st.sidebar:
    st.header("⚙️ 시스템 설정")
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        if not api_key:
            st.error("⚠️ Secrets에 API 키가 없습니다.")
        else:
            genai.configure(api_key=api_key)
            selected_model = get_best_model()
            st.success("✅ API 연결 성공")
            st.info(f"🤖 사용 모델: **{selected_model}**")
    except Exception as e:
        st.error(f"⚠️ API 연결 오류: {e}")

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

# --- 5. 분석 실행 및 결과 표시 ---
if submit_btn:
    if not api_key:
        st.error("API 키가 설정되지 않았습니다. 좌측 사이드바 설정을 확인해 주세요.")
    # 개선 1: .strip()을 사용해 공백만 입력한 경우를 빈칸으로 간주하여 차단
    elif not (job.strip() and interest.strip() and hobby.strip() and subject.strip()):
        st.warning("⚠️ 모든 항목에 내용을 정확히 입력해 주세요.")
    else:
        with st.spinner(f"AI({selected_model})가 최적의 진로를 분석 중입니다..."):
            try:
                recommendations = get_career_recommendations(selected_model, job, interest, hobby, subject)
                st.session_state['recommendations'] = recommendations
            except ValueError as ve:
                st.error(f"⚠️ {ve}")
            except Exception as e:
                if "429" in str(e):
                    st.error("🚀 현재 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
                else:
                    st.error(f"오류가 발생했습니다: {str(e)}")

# --- 6. 결과 렌더링 및 다운로드 ---
if 'recommendations' in st.session_state:
    data = st.session_state['recommendations']
    st.divider()
    
    report_text = "=== 진로 탐색 결과 보고서 ===\n\n"
    
    for rec in data:
        with st.container(border=True):
            st.markdown(f"### 📍 {rec['majorName']}")
            st.markdown(rec['introduction'])
            
            st.markdown("#### ✨ 추천 이유")
            st.info(rec['reason'])
            
            st.markdown("#### 📚 주요 커리큘럼")
            st.caption(f"{', '.join(rec['curriculum'])}")
            
            st.markdown("#### 🚀 졸업 후 진로")
            st.caption(f"{', '.join(rec['career'])}")
        
        report_text += f"▶ 학과: {rec['majorName']}\n- 이유: {rec['reason']}\n- 진로: {', '.join(rec['career'])}\n\n"

    st.download_button(
        label="📄 결과 보고서(.txt) 다운로드",
        data=report_text,
        file_name="career_report.txt",
        mime="text/plain",
        use_container_width=True
    )
