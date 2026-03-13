import streamlit as st
import google.generativeai as genai
import json

# --- 페이지 설정 ---
st.set_page_config(
    page_title="고등학생 진로 탐색기",
    page_icon="🎓",
    layout="centered"
)

# --- 스타일링 (CSS) ---
st.markdown("""
    <style>
    .main-title {
        font-size: 3rem;
        font-weight: bold;
        color: #1f2937;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        font-size: 1.2rem;
        color: #6b7280;
        text-align: center;
        margin-bottom: 2rem;
    }
    .card {
        background-color: #f9fafb;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .card-title {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2563eb;
        margin-bottom: 0.5rem;
    }
    .section-title {
        font-weight: bold;
        color: #374151;
        margin-top: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바: 설정 및 자동 모델 선택 ---
with st.sidebar:
    st.header("⚙️ 설정")
    
    # 1. Secrets에서 API 키 가져오기
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        api_key = None
    
    selected_model = None

    # API 키가 있을 때만 모델 목록 불러오기 실행
    if not api_key:
        st.error("⚠️ Secrets 설정이 필요합니다. (API 키 누락)")
    else:
        try:
            # GenAI 설정 (모델 목록을 불러오기 위해 먼저 인증)
            genai.configure(api_key=api_key)
            
            # API에서 지원하는 전체 모델 목록 가져오기
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # 'flash'가 포함된 모델만 필터링하고 실험버전(exp) 제외 후 정렬 (최신 버전이 맨 뒤로 옴)
            flash_models = [m for m in available_models if 'flash' in m.lower() and 'exp' not in m.lower()]
            
            if flash_models:
                # 가장 마지막(최신) 모델 선택 후 'models/' 접두사 제거
                selected_model = sorted(flash_models)[-1].replace("models/", "")
            else:
                # 안전망: 검색 실패 시 기본값 (현재 시점 최신 안정화 버전)
                selected_model = "gemini-2.5-flash"
                
            st.success("✅ API 연결 성공!")
            st.info(f"✨ 자동 선택된 최신 모델:\n**{selected_model}**")
            
        except Exception as e:
            st.error(f"모델 목록 로드 실패: {str(e)}")
            selected_model = "gemini-2.5-flash"

# --- 메인 화면 ---
st.markdown('<div class="main-title">진로 탐색기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">당신의 꿈에 맞는 학과를 찾아보세요</div>', unsafe_allow_html=True)

# --- 입력 폼 ---
with st.form("career_form"):
    job = st.text_input("희망 직업", placeholder="예: 소프트웨어 개발자")
    interest = st.text_input("관심 분야", placeholder="예: 인공지능, 환경")
    hobby = st.text_input("취미 및 특기", placeholder="예: 코딩, 그림 그리기")
    subject = st.text_input("선호 과목", placeholder="예: 수학, 과학")
    
    submit_btn = st.form_submit_button("학과 추천받기", type="primary", use_container_width=True)

# --- 결과 처리 로직 ---
if submit_btn:
    if not api_key:
        st.error("⚠️ API Key가 설정되지 않았습니다. Streamlit Cloud의 Secrets 설정을 확인해주세요.")
    elif not selected_model:
        st.error("⚠️ 사용할 수 있는 AI 모델을 찾지 못했습니다.")
    elif not (job and interest and hobby and subject):
        st.warning("⚠️ 모든 항목을 입력해주세요.")
    else:
        try:
            # 모델 인스턴스 생성 (위에서 자동 검색된 최신 모델 사용)
            model = genai.GenerativeModel(model_name=selected_model)
            
            # 프롬프트 구성
            user_prompt = f"""
            당신은 고등학생을 위한 친절하고 전문적인 진로 상담가입니다. 
            사용자가 입력한 정보는 다음과 같습니다.
            - 희망 직업: {job}
            - 관심 분야: {interest}
            - 취미 및 특기: {hobby}
            - 선호 과목: {subject}
            
            이 정보를 바탕으로 고등학생에게 적합한 대학교 학과 3개를 추천해줘.
            반드시 아래 JSON 스키마를 엄격히 준수해서 응답해줘. 마크다운 태그(```json) 없이 순수 JSON 텍스트만 출력해.
            
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
            
            with st.spinner(f"AI({selected_model})가 분석 중입니다..."):
                response = model.generate_content(
                    user_prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # 결과 텍스트 파싱
                result_text = response.text
                recommendations = json.loads(result_text)
                
                # 세션 상태에 저장
                st.session_state['recommendations'] = recommendations
                
        except Exception as e:
            st.error(f"결과를 생성하는 중 오류가 발생했습니다: {str(e)}")

# --- 결과 표시 및 다운로드 ---
if 'recommendations' in st.session_state:
    data = st.session_state['recommendations']
    
    st.divider()
    st.subheader("📋 추천 결과")
    
    txt_output = "고등학생 진로 탐색 결과\n\n"
    
    for rec in data:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">{rec['majorName']}</div>
            <p>{rec['introduction']}</p>
            <div class="section-title">✨ 추천 이유</div>
            <p>{rec['reason']}</p>
            <div class="section-title">📚 주요 커리큘럼</div>
            <ul style="margin-top:0;">
                {''.join(f'<li>{item}</li>' for item in rec['curriculum'])}
            </ul>
            <div class="section-title">🚀 졸업 후 진로</div>
            <ul style="margin-top:0;">
                {''.join(f'<li>{item}</li>' for item in rec['career'])}
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        txt_output += f"========================================\n"
        txt_output += f"▶ 추천 학과: {rec['majorName']}\n"
        txt_output += f"========================================\n"
        txt_output += f"※ 학과 소개: {rec['introduction']}\n"
        txt_output += f"※ 추천 이유: {rec['reason']}\n"
        txt_output += f"※ 주요 커리큘럼: {', '.join(rec['curriculum'])}\n"
        txt_output += f"※ 졸업 후 진로: {', '.join(rec['career'])}\n\n"

    st.download_button(
        label="📥 결과 다운로드 (.txt)",
        data=txt_output,
        file_name="진로_탐색_결과.txt",
        mime="text/plain",
        type="primary"
    )
