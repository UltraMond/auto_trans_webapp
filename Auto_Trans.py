import streamlit as st
import google.generativeai as genai
import time
import zipfile
import io
import re
import pandas as pd  # 엑셀 기능을 위해 추가됨

# 1. 페이지 설정
st.set_page_config(page_title="Auto_Trans v22", layout="wide")

# 세션 상태 초기화
if "results" not in st.session_state:
    st.session_state.results = {}

# CSS: 결과창 높이 고정 및 스크롤
st.markdown("""
    <style>
    div[data-testid="stCode"] > div > pre:nth-of-type(1) { max-height: 45px !important; }
    .desc-box pre { max-height: 80px !important; }
    .srt-box pre { max-height: 120px !important; }
    pre { overflow-y: auto !important; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 설정
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
raw_langs = ["광둥어", "그리스어", "네덜란드어", "네팔어", "노르웨이어", "덴마크어", "독일어", "라틴어", "러시아어", "룩셈부르크어", "마오리어", "말레이어", "몽골어", "민난어", "베트남어", "벵골어", "세르비아어", "스와힐리어", "스웨덴어", "스페인어", "슬로바키아어", "슬로베니아어", "아랍어", "아이슬란드어", "아일랜드어", "영어", "우르두어", "우즈베크어", "우크라이나어", "이탈리아어", "인도네시아어", "일본어", "중국어(간체)", "중국어(번체)", "체코어", "태국어", "튀르키예어", "페르시아어", "포르투갈어", "포르투갈어(브라질)", "포르투갈어(포르투갈)", "폴란드어", "프랑스어", "핀란드어", "필리핀어", "하와이어", "헝가리어", "히브리어", "한국어"]
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
    prompt = f"Identify language. Return ONLY the name from list: {', '.join(languages)}. Text: {(title+srt)[:300]}"
    try: return model.generate_content(prompt).text.strip()
    except: return "Unknown"

def translate_content(title, desc, srt, target_lang, api_key, model_id):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_id)
    lang_name = target_lang.split('. ')[1]
    
    prompt = f"""
    You are a professional subtitle translator.
    Target Language: {lang_name}
    
    [INSTRUCTIONS]
    1. Translate the Title, Description, and SRT.
    2. Output ONLY the raw translated text separated by '|||'.
    3. DO NOT output conversational filler.
    4. DO NOT use markdown code blocks.
    5. DO NOT add labels like "Title:".
    6. Keep SRT timecodes exactly as they are.

    [FORMAT]
    Translated_Title|||Translated_Description|||Translated_SRT_Content

    [INPUT]
    Title: {title}
    Desc: {desc}
    SRT: {srt}
    """
    try:
        response = model.generate_content(prompt)
        parts = response.text.split('|||')
        
        title_clean = clean_text(parts[0]) if len(parts) > 0 else ""
        desc_clean = clean_text(parts[1]) if len(parts) > 1 else ""
        srt_clean = clean_text(parts[2]) if len(parts) > 2 else ""

        return {"title": title_clean, "desc": desc_clean, "srt": srt_clean}
    except Exception as e: return {"error": str(e)}

# 5. 메인 UI
st.title("🎬 Auto_Trans v22 (Excel Support)")

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

# 6. 실행 로직 (Fragment)
@st.fragment
def run_app():
    # 버튼 레이아웃: 번역 시작 | ZIP 다운로드 | 엑셀 다운로드
    btn_run, btn_zip, btn_excel = st.columns([1, 1, 1])
    
    if btn_run.button("🚀 번역 시작", type="primary", use_container_width=True):
        if not api_key or not (u_title or u_srt):
            st.error("설정 및 내용을 확인하세요.")
            return

        st.session_state.results = {} 
        
        with st.status("🔍 번역 진행 중...", expanded=True) as status:
            detected = detect_source_language(u_title, u_srt, api_key, target_model_id)
            st.write(f"감지됨: **{detected}** (제외)")
            
            targets = [l for l in selected_list if detected not in l]
            live_container = st.container()
            
            for lang in targets:
                res = translate_content(u_title, u_desc, u_srt, lang, api_key, target_model_id)
                st.session_state.results[lang] = res
                
                with live_container:
                    display_single_result(lang, res)
                time.sleep(0.5)
            
            status.update(label="완료!", state="complete", expanded=False)

    elif st.session_state.results:
        for lang, res in st.session_state.results.items():
            display_single_result(lang, res)

    # (1) ZIP 다운로드 (자막 파일)
    if st.session_state.results:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "a") as zf:
            for lang, data in st.session_state.results.items():
                if "srt" in data and data["srt"]: 
                    zf.writestr(f"{lang}.srt", data["srt"])
        btn_zip.download_button("📦 자막 ZIP 다운로드", data=zip_buf.getvalue(), file_name="Subtitles.zip", use_container_width=True)

    # (2) [NEW] 엑셀 다운로드 (제목 & 설명)
    if st.session_state.results:
        # 데이터프레임 생성
        excel_data = []
        for lang, data in st.session_state.results.items():
            excel_data.append({
                "언어": lang,
                "제목": data.get("title", ""),
                "내용": data.get("desc", "")
            })
        
        df = pd.DataFrame(excel_data)
        
        # 엑셀 파일 메모리에 쓰기
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Translations')
            # 컬럼 너비 자동 조절 (보기 좋게)
            worksheet = writer.sheets['Translations']
            worksheet.set_column('A:A', 20)  # 언어 컬럼
            worksheet.set_column('B:C', 60)  # 제목, 내용 컬럼
            
        excel_binary = excel_buffer.getvalue()
        
        btn_excel.download_button(
            label="📊 엑셀 통합 다운로드",
            data=excel_binary,
            file_name="YouTube_Metadata.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

def display_single_result(lang, res):
    with st.expander(f"✅ {lang} 완료", expanded=True):
        if "error" in res:
            st.error(res["error"])
        else:
            st.caption("제목")
            with st.container(height=60):
                st.code(res["title"], language="text")
            
            st.caption("설명")
            with st.container(height=110):
                st.code(res["desc"], language="text")
            
            st.caption("자막")
            with st.container(height=160):
                st.code(res["srt"], language="text")
            
            st.download_button(f"📥 {lang} 파일", res["srt"], file_name=f"{lang}.srt")

run_app()