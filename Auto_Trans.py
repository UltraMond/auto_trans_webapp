import streamlit as st
import google.generativeai as genai
import time
import zipfile
import io
import re
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="Auto Trans", layout="wide")

# 세션 상태 초기화
if "results" not in st.session_state:
    st.session_state.results = {}
if "mode" not in st.session_state:
    st.session_state.mode = "all"

# CSS
st.markdown("""
    <style>
    div[data-testid="stCode"] > div > pre:nth-of-type(1) { max-height: 45px !important; }
    .desc-box pre { max-height: 80px !important; }
    .srt-box pre { max-height: 120px !important; }
    pre { overflow-y: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Gemini API Key (유료)", type="password")
    target_model_id = "gemini-2.0-flash" 
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            st.success("⚡ Gemini 2.0 Flash 연결됨")
        except Exception as e:
            st.error(f"키 오류: {e}")
    st.info(f"모델: {target_model_id}")

# 3. 언어 리스트
raw_langs = [
    "광둥어", "그리스어", "네덜란드어", "네팔어", "노르웨이어", "덴마크어", "독일어", "라틴어", "러시아어", 
    "룩셈부르크어", "마오리어", "말레이어", "몽골어", "민난어", "베트남어", "벵골어", "세르비아어", "스와힐리어", 
    "스웨덴어", "스페인어", "슬로바키아어", "슬로베니아어", "아랍어", "아이슬란드어", "아일랜드어", "영어", 
    "우르두어", "우즈베크어", "우크라이나어", "이탈리아어", "인도네시아어", "일본어", "중국어(간체)", 
    "중국어(번체)", "체코어", "태국어", "튀르키예어", "페르시아어", "포르투갈어", "포르투갈어(브라질)", 
    "포르투갈어(포르투갈)", "폴란드어", "프랑스어", "핀란드어", "필리핀어", "하와이어", "한국어", "헝가리어", 
    "히브리어", "힌디어"
]
languages = [f"{i+1:02d}. {lang}" for i, lang in enumerate(sorted(raw_langs))]

# 4. 기능 함수
def clean_text(text):
    if not text: return ""
    text = text.replace("```srt", "").replace("```json", "").replace("```", "")
    for label in ["[Title]:", "Title:", "[Desc]:", "Description:", "[SRT]:", "SRT:", "---TITLE---", "---DESC---", "---SRT---"]:
        text = text.replace(label, "")
    return text.strip()

def detect_source_language(title, srt, api_key, model_id):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    text_sample = (title + srt)[:300]
    prompt = f"Identify language. Return ONLY the name from list: {', '.join(languages)}. Text: {text_sample}"
    try: return model.generate_content(prompt).text.strip()
    except: return "Unknown"

# ▼▼▼▼▼ 수정된 핵심 부분 ▼▼▼▼▼
def translate_content(title, desc, srt, target_lang, api_key, model_id, mode="all"):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    lang_name = target_lang.split('. ')[1]
    
    # [핵심 변경사항] 프롬프트에 '강력한 현지화' 및 '혼용 금지' 규칙 추가
    common_instruction = f"""
    [CRITICAL RULES]
    1. **NO MIXED SCRIPTS:** The output must be 100% in {lang_name}. Do NOT leave any Korean (Hangul) or English characters.
    2. **LOCALIZATION:** Translate specific food names or cultural terms into their meaning in {lang_name}.
       - Example: "소고기무국" -> "Beef Radish Soup" (translated to {lang_name})
       - Example: "석화구이" -> "Grilled Oysters" (translated to {lang_name})
       - DO NOT transliterate/sound them out.
    3. **TITLE LENGTH:** Translated Title must be UNDER 99 CHARACTERS.
    4. **PRESERVE VISUALS:** Keep ALL emojis, special characters (@, #, $, %), and punctuation exactly as they are.
    """
    
    if mode == "all":
        prompt = f"""
        You are a professional video translator.
        Translate the following metadata and subtitles to naturally spoken **{lang_name}**.
        {common_instruction}
        
        Output ONLY raw text separated by '|||'.
        Format: Title|||Description|||SRT
        Keep SRT timecodes exactly.
        
        [INPUT]
        Title: {title}
        Desc: {desc}
        SRT: {srt}
        """
    elif mode == "meta":
        prompt = f"""
        Translate the following metadata to naturally spoken **{lang_name}**.
        {common_instruction}
        
        Output ONLY raw text separated by '|||'.
        Format: Title|||Description
        
        [INPUT]
        Title: {title}
        Desc: {desc}
        """
    elif mode == "srt":
        prompt = f"""
        Translate the following SRT subtitles to naturally spoken **{lang_name}**.
        {common_instruction}
        
        Output ONLY raw SRT content.
        Keep timecodes exactly.
        
        [INPUT]
        SRT: {srt}
        """
# ▲▲▲▲▲ 수정 끝 ▲▲▲▲▲

    try:
        response = model.generate_content(prompt)
        text = response.text
        
        if mode == "all":
            parts = text.split('|||')
            return {
                "title": clean_text(parts[0]) if len(parts) > 0 else "",
                "desc": clean_text(parts[1]) if len(parts) > 1 else "",
                "srt": clean_text(parts[2]) if len(parts) > 2 else ""
            }
        elif mode == "meta":
            parts = text.split('|||')
            return {
                "title": clean_text(parts[0]) if len(parts) > 0 else "",
                "desc": clean_text(parts[1]) if len(parts) > 1 else "",
                "srt": "" 
            }
        elif mode == "srt":
            return {
                "title": "", 
                "desc": "",
                "srt": clean_text(text)
            }
            
    except Exception as e: return {"error": str(e)}

# 5. 메인 UI
st.title("🎬 Auto Trans")

col_in, col_opt = st.columns([2, 1])
with col_in:
    st.subheader("📝 데이터 입력")
    u_title = st.text_input("유튜브 제목", key="title")
    u_desc = st.text_area("유튜브 설명", height=100, key="desc")
    u_srt = st.text_area("SRT 자막", height=450, key="srt")

with col_opt:
    st.subheader("🌐 언어 선택")
    select_all = st.checkbox("전체 선택")
    with st.container(height=615):
        selected_list = [l for l in languages if st.checkbox(l, value=select_all)]

st.markdown("---")

# 6. 실행 로직
@st.fragment
def run_app():
    col1, col2, col3 = st.columns(3)
    
    start_mode = None
    if col1.button("🚀 전체 번역 (All)", type="primary", use_container_width=True):
        start_mode = "all"
    elif col2.button("📝 제목+설명만 (Meta)", use_container_width=True):
        start_mode = "meta"
    elif col3.button("💬 자막만 (SRT)", use_container_width=True):
        start_mode = "srt"

    if start_mode:
        if not api_key:
            st.error("API 키를 입력하세요.")
            return
        if start_mode == "srt" and not u_srt:
            st.error("자막(SRT) 내용을 입력해주세요.")
            return
        if start_mode == "meta" and not u_title:
            st.error("제목을 입력해주세요.")
            return
            
        st.session_state.results = {}
        st.session_state.mode = start_mode
        
        with st.status(f"🔍 {start_mode.upper()} 모드 작업 시작...", expanded=True) as status:
            input_sample = u_srt if start_mode == "srt" else u_title + u_desc
            detected = detect_source_language(u_title, input_sample, api_key, target_model_id)
            st.write(f"감지됨: **{detected}** (자동 제외)")
            
            targets = [l for l in selected_list if detected not in l]
            total_targets = len(targets)
            
            progress_bar = st.progress(0, text="작업 준비 중...")
            
            live_container = st.container()
            
            for i, lang in enumerate(targets):
                res = translate_content(u_title, u_desc, u_srt, lang, api_key, target_model_id, start_mode)
                st.session_state.results[lang] = res
                
                with live_container:
                    display_single_result(lang, res, start_mode)
                
                # 진행률 업데이트
                if total_targets > 0:
                    percent = (i + 1) / total_targets
                    progress_bar.progress(percent, text=f"⏳ 진행률: {int(percent*100)}% ({lang} 완료)")
                
                time.sleep(0.5)
            
            status.update(label="🎉 모든 작업이 완료되었습니다!", state="complete", expanded=False)

    elif st.session_state.results:
        current_mode = st.session_state.get("mode", "all")
        for lang, res in st.session_state.results.items():
            display_single_result(lang, res, current_mode)

    # 다운로드 버튼
    if st.session_state.results:
        st.markdown("---")
        d_col1, d_col2 = st.columns(2)
        
        has_srt = any(data.get("srt") for data in st.session_state.results.values())
        if has_srt:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "a") as zf:
                for lang, data in st.session_state.results.items():
                    if data.get("srt"): 
                        zf.writestr(f"{lang}.srt", data["srt"])
            d_col1.download_button("📦 자막 ZIP 다운로드", data=zip_buf.getvalue(), file_name="Subtitles.zip", use_container_width=True)

        has_meta = any(data.get("title") for data in st.session_state.results.values())
        if has_meta:
            excel_data = []
            for lang, data in st.session_state.results.items():
                if data.get("title") or data.get("desc"):
                    excel_data.append({
                        "언어": lang,
                        "제목": data.get("title", ""),
                        "내용": data.get("desc", "")
                    })
            if excel_data:
                df = pd.DataFrame(excel_data)
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Translations')
                    worksheet = writer.sheets['Translations']
                    worksheet.set_column('A:A', 20)
                    worksheet.set_column('B:C', 60)
                d_col2.download_button("📊 엑셀 통합 다운로드", data=excel_buffer.getvalue(), file_name="Metadata.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

def display_single_result(lang, res, mode):
    with st.expander(f"✅ {lang} 완료", expanded=True):
        if "error" in res:
            st.error(res["error"])  
        else:
            if mode in ["all", "meta"] and res.get("title"):
                st.caption(f"제목 ({len(res['title'])}자)")
                with st.container(height=60):
                    st.code(res["title"], language="text")
                
                st.caption("설명")
                with st.container(height=110):
                    st.code(res["desc"], language="text")
            
            if mode in ["all", "srt"] and res.get("srt"):
                st.caption("자막")
                with st.container(height=160):
                    st.code(res["srt"], language="text")
                st.download_button(f"📥 {lang} 자막", res["srt"], file_name=f"{lang}.srt")

run_app()
