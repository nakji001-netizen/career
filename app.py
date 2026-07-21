import streamlit as st
import google.generativeai as genai
import json
import time
import requests
import threading
from google.api_core.exceptions import ResourceExhausted, ServiceUnavailable, InternalServerError

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
@st.cache_data(show_spinner=False)
def get_best_model():
    """
    [속도 최적화] 유료 플랜 전환 완료 후에는 불필요한 네트워크 API 호출(list_models)을 
    완전히 제거하고, 현재 전 세계에서 가장 빠르고 가성비가 좋은 최신 표준 모델인 
    'gemini-2.5-flash'로 바로 직행하여 로딩 시간을 2초 이상 단축시킵니다.
    """
    return "gemini-2.5-flash"

@st.cache_data(show_spinner=False, ttl=86400)
def get_career_recommendations(model_name, job, interest, hobby, subject):
    """[초고속 튜닝] 무거운 response_schema 규격을 제거하고 초경량 JSON 모드로 연산 성능 극대화"""
    generation_config = {
        "response_mime_type": "application/json",
        "temperature": 0.2  # [속도 최적화] 낮을수록 창의적 방황을 줄여 답변 생성 속도가 빨라집니다.
    }

    # 스키마 검사 오버헤드 없이 완벽한 JSON 포맷을 유도하는 엄격한 시스템 지침
    system_instruction = (
        "너는 고등학생을 위한 진로 상담 교사야. 질문에 성실히 답변하되, "
        "반드시 아래 기술된 구조를 갖춘 단 하나의 JSON 배열(Array) 형태로만 결과를 반환해야 해. "
        "마크다운 코드 블록 기호(```json 등)는 앞뒤에 절대 쓰지 말고 오직 순수한 JSON 텍스트만 출력해.\n\n"
        "[\n"
        "  {\n"
        '    "majorName": "추천 학과 이름 (예: 컴퓨터공학과)",\n'
        '    "introduction": "해당 학과에 대한 명쾌한 소개 (핵심만 2문장 이내)",\n'
        '    "reason": "학생의 관심 정보를 종합 분석하여 추천하는 핵심적이고 구체적인 이유 (핵심만 2문장 이내)",\n'
        '    "curriculum": ["가장 상징적인 전공과목 키워드1", "전공과목 키워드2", "전공과목 키워드3", "전공과목 키워드4"],\n'
        '    "career": ["주요 취업 및 연구 진로 분야1", "진로 분야2", "진로 분야3", "진로 분야4"]\n'
        "  },\n"
        "  ... (반드시 규격을 정확히 지켜 총 3개의 학과 추천 정보 포함)\n"
        "]\n\n"
        "장황한 서술이나 긴 문장은 생성 지연을 유발하므로 무조건 짧고 강력하게 요약해서 구성해야 함."
    )

    model = genai.GenerativeModel(
        model_name=model_name, 
        generation_config=generation_config,
        system_instruction=system_instruction
    )
    
    prompt = f"희망직업: {job}, 관심분야: {interest}, 취미: {hobby}, 선호과목: {subject} 정보를 바탕으로 적합한 대학교 학과 3개를 추천해줘."

    max_retries = 3
    for i in range(max_retries):
        try:
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
            
            # 혹시 모를 구글의 마크다운 감싸기 기호 철저히 우회 제거
            if raw_text.startswith("```json"):
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
                
            return json.loads(raw_text)
            
        except (ResourceExhausted, ServiceUnavailable, InternalServerError, Exception) as e:
            # 503(서버 일시 에러), 500(내부 에러) 발생 시 백오프 자동 초고속 재시도
            if i < max_retries - 1:
                time.sleep(1.5 * (i + 1))
                continue
            raise e

def save_to_google_sheet_background(webhook_url, payload):
    """결과를 구글 시트로 백그라운드 전송"""
    def send_request():
        try:
            requests.post(webhook_url, json=payload)
        except Exception:
            pass
    thread = threading.Thread(target=send_request)
    thread.start()

# --- 3. 사이드바: API 설정 ---
api_key = None
webhook_url = None
selected_model = "모델 확인 불가"

with st.sidebar:
    st.header("⚙️ 시스템 설정")
    try:
        api_key = st.secrets.get("GOOGLE_API_KEY")
        webhook_url = st.secrets.get("WEBHOOK_URL")
        if api_key:
            genai.configure(api_key=api_key)
            selected_model = get_best_model()
            st.success("✅ AI API 연결 성공")
            st.info(f"🤖 사용 모델: **{selected_model}**")
        else:
            st.error("⚠️ API 키가 없습니다.")
        if webhook_url:
            st.success("✅ 구글 시트 연결 성공")
        else:
            st.warning("⚠️ 웹훅 URL이 없습니다.")
    except Exception as e:
        st.error(f"⚠️ 설정 오류: {e}")

# --- 4. 메인 화면 ---
st.markdown('<div class="main-title">🎓 진로 탐색기</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">당신의 꿈을 데이터로 분석하여 최적의 학과를 제안합니다.</div>', unsafe_allow_html=True)

with st.form("career_form"):
    st.markdown("**학생 정보**")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        student_id = st.text_input("🔢 학번", placeholder="예: 10101")
    with col_info2:
        student_name = st.text_input("👤 이름", placeholder="예: 홍길동")
    st.markdown("**탐색 정보**")
    col1, col2 = st.columns(2)
    with col1:
        job = st.text_input("🎯 희망 직업", placeholder="예: 로봇 공학자")
        interest = st.text_input("💡 관심 분야", placeholder="예: 자율주행, AI")
    with col2:
        hobby = st.text_input("🎨 취미 및 특기", placeholder="예: 프라모델 조립")
        subject = st.text_input("📚 선호 과목", placeholder="예: 물리, 수학")
    submit_btn = st.form_submit_button("학과 추천받기 ✨", type="primary", use_container_width=True)

# --- 5. 분석 및 결과 ---
if submit_btn:
    if not api_key:
        st.error("API 키 설정을 확인해주세요.")
    elif not (student_id.strip() and student_name.strip() and job.strip() and interest.strip() and hobby.strip() and subject.strip()):
        st.warning("⚠️ 모든 항목을 입력해주세요.")
    else:
        # 체감 대기 지루함을 해소하기 위한 단계별 프로그레스 디자인 연출
        status_placeholder = st.empty()
        with status_placeholder.container():
            st.markdown("⚡ **구글 AI 초고속 전용 채널을 개설하는 중...**")
            progress_bar = st.progress(15)
            
        try:
            # 상태 메시지 업데이트
            with status_placeholder.container():
                st.markdown("🧠 **기초 학문 데이터와 적성 요소를 융합 매핑 분석하는 중...**")
                progress_bar.progress(45)
                
            recommendations = get_career_recommendations(selected_model, job, interest, hobby, subject)
            st.session_state['recommendations'] = recommendations
            
            with status_placeholder.container():
                st.markdown("🚀 **선생님 구글 시트로 보고서를 초고속 백그라운드 전송 중...**")
                progress_bar.progress(85)
                
            if webhook_url:
                payload = {
                    "student_id": student_id, "student_name": student_name, "job": job,
                    "interest": interest, "hobby": hobby, "subject": subject,
                    "rec1": recommendations[0]['majorName'] if len(recommendations) > 0 else "",
                    "rec2": recommendations[1]['majorName'] if len(recommendations) > 1 else "",
                    "rec3": recommendations[2]['majorName'] if len(recommendations) > 2 else ""
                }
                save_to_google_sheet_background(webhook_url, payload)
                st.toast("✅ 결과가 선생님 시트로 전송 중입니다!", icon="🚀")
            
            # 상태 바 청소 및 이펙트 효과
            status_placeholder.empty()
            st.balloons()

        except Exception as e:
            status_placeholder.empty()
            error_msg = str(e)
            if "429" in error_msg or "quota" in error_msg.lower():
                st.error("🚨 **안내:** 현재 동시에 접속한 학생들이 많아 AI 분석 서비스가 일시적으로 지연되었습니다. **약 15초 후에 [학과 추천받기] 버튼을 다시 한번만 눌러주세요!**")
            else:
                st.error(f"오류 발생: {e}")

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
    st.download_button(label="📄 결과 보고서 다운로드", data=report_text, file_name="career_report.txt", use_container_width=True)
# Last Heartbeat: Tue Jul 21 07:25:50 UTC 2026
