import streamlit as st
import google.generativeai as genai
import time
import zipfile
import io

# 1. 페이지 설정 및 세션 상태 초기화
st.set_page_config(page_title="Auto_Trans v19", layout="wide")

if "results" not in st.session_state:
    st.session_state.results = {}
if "running" not in st.session_state:
    st.session_state.running = False

# 2. 사이드바: 유료 키 입력 및 모델 고정
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Gemini API Key (유료)", type="password", help="Google AI Studio에서 발급받은 유료 결제가 연결된 키를 입력하세요.")
    
    # [핵심 변경] Gemini 2.0 Flash 모델 고정
    target_model_id = "gemini-2.0-flash" 
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("⚡ Gemini 2.0 Flash 연결됨")
        except Exception as e:
            st.error(f"API 키 확인 필요: {e}")
            
    st.info(f"사용 모델: {target_model_id}")
    st.caption("유료 티어 사용 시 더 빠르고 안정적인 번역이 가능합니다.")

# 3. 언어 리스트 자동 정렬 및 넘버링
raw_langs = ["광둥어", "그리스어", "네덜란드어", "네팔어", "노르웨이어", "덴마크어", "독일어", "라틴어", "러시아어", "룩셈부르크어", "마오리어", "말레이어", "몽골어", "민난어", "베트남어", "벵골어", "세르비아어", "스와힐리어", "스웨덴어", "스페인어", "슬로바키아어", "슬로베니아어", "아랍어", "아이슬란드어", "아일랜드어", "영어", "우르두어", "우즈베크어", "우크라이나어", "이탈리아어", "인도네시아어", "일본어", "중국어(간체)", "중국어(번체)", "체코어", "태국어", "튀르키예어", "페르시아어", "포르투갈어", "포르투갈어(브라질)", "포르투갈어(포르투갈)", "폴란드어", "프랑스어", "핀란드어", "필리핀어", "하와이어", "헝가리어", "히브리어", "한국어"]
languages = [f"{i+1:02d}. {lang}" for i, lang in enumerate(sorted(raw_langs))]

# 4. 기능 함수
def detect_source_language(title, srt, api_key, model_id):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    sample = (title + srt)[:300]
    prompt = f"Identify the language. Return only the name from this list: {', '.join(languages)}. Text: {sample}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except: return "Unknown"

def translate_content(title, desc, srt, target_lang, api_key, model_id):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    lang_name = target_lang.split('. ')[1]
    prompt = f"Translate the following YouTube content into {lang_name}. Separate sections with '|||'. Format: Title ||| Description ||| SRT. Keep timecodes and sequence numbers exactly as they are.\n\n[Title]: {title}\n[Description]: {desc}\n[SRT]: {srt}"
    try:
        response = model.generate_content(prompt)
        parts = response.text.split('|||')
        return {
            "title": parts[0].strip() if len(parts) > 0 else "",
            "desc": parts[1].strip() if len(parts) > 1 else "",
            "srt": parts[2].strip() if len(parts) > 2 else ""
        }
    except Exception as e: return {"error": str(e)}

# 5. 메인 UI
st.title("🎬 Auto_Trans v19 (Gemini 2.0 Flash)")

col_in, col_opt = st.columns([2, 1])

with col_in:
    st.subheader("📝 데이터 입력")
    u_title = st.text_input("유튜브 제목", key="input_title")
    u_desc = st.text_area("유튜브 설명", height=100, key="input_desc")
    u_srt = st.text_area("SRT 자막", height=450, key="input_srt")

with col_opt:
    st.subheader("🌐 언어 선택")
    select_all = st.checkbox("전체 선택")
    with st.container(height=615): 
        selected_list = [l for l in languages if st.checkbox(l, value=select_all)]

st.markdown("---")

@st.fragment
def run_translation():
    btn_run, btn_zip = st.columns(2)
    
    if btn_run.button("🚀 번역 시작", type="primary", use_container_width=True):
        if not api_key or not (u_title or u_srt):
            st.error("API 키와 번역할 내용을 입력하세요.")
            return

        st.session_state.results = {}
        st.session_state.running = True
        
        with st.status("🔍 Gemini 2.0 Flash 엔진 가동 중...", expanded=True) as status:
            detected_lang = detect_source_language(u_title, u_srt, api_key, target_model_id)
            st.write(f"💡 감지된 원본 언어: **{detected_lang}** (번역에서 자동 제외)")
            
            final_targets = [l for l in selected_list if detected_lang not in l]
            results_container = st.container()
            
            for i, lang in enumerate(final_targets):
                res = translate_content(u_title, u_desc, u_srt, lang, api_key, target_model_id)
                st.session_state.results[lang] = res
                
                with results_container:
                    with st.expander(f"✅ {lang} 번역 완료", expanded=True):
                        if "error" in res: st.error(res["error"])
                        else:
                            st.write("**제목**")
                            st.code(res["title"], language="text")
                            st.write("**설명**")
                            st.code(res["desc"], language="text")
                            st.write("**SRT**")
                            st.code(res["srt"], language="text")
                            st.download_button(f"{lang} SRT 다운로드", res["srt"], file_name=f"{lang}.srt", key=f"dl_{lang}")
                
                # 유료 키는 속도가 빠르므로 대기 시간을 0.5초로 단축 가능
                time.sleep(0.5)
            
            status.update(label="🎉 모든 번역 작업이 완료되었습니다!", state="complete", expanded=False)
        st.session_state.running = False

    if st.session_state.results:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "a") as zf:
            for lang, data in st.session_state.results.items():
                if "srt" in data: zf.writestr(f"{lang}.srt", data["srt"])
        
        btn_zip.download_button("📦 모든 SRT 자막 ZIP 다운로드", data=zip_buf.getvalue(), 
                                file_name="Subtitles_Only.zip", use_container_width=True)

run_translation()