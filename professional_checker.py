import streamlit as st
import google.generativeai as genai
import hashlib
import os
import io
import datetime

try:
    from docx import Document
except ImportError:
    st.error("ไม่พบไลบรารี python-docx, กรุณาติดตั้งด้วยคำสั่ง: pip install python-docx")
    st.stop()


# --- การตั้งค่าพื้นฐาน ---
st.set_page_config(
    page_title="ผู้ช่วยนักเขียน AI",
    page_icon="✍️",
    layout="wide"
)

# --- ส่วนจัดการไฟล์และข้อมูล ---
DICTIONARY_FILE = "personal_dictionary.txt"
LOG_FILE = "activity_log.txt"

def load_from_file(filename):
    if not os.path.exists(filename):
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_to_file(filename, data_list):
    with open(filename, "w", encoding="utf-8") as f:
        for item in sorted(data_list):
            f.write(f"{item}\n")

def add_log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] - {message}\n")

# --- ส่วนของการเชื่อมต่อกับ Gemini API ---
CORRECT_PASSWORD_HASH = "dc32ae59ec94f05bfe110b4aa7524db9"

@st.cache_data(show_spinner=False)
def call_gemini_api(prompt: str, api_key: str):
    try:
        genai.configure(api_key=api_key)
        request_options = {'timeout': 300}
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, request_options=request_options)
        return response.text
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อกับ Gemini API: {e}", icon="🚨")
        return None

def get_proofread_result(text_to_check: str, api_key: str, style: str, dictionary: set):
    style_instruction = "ปรับสำนวนการเขียนให้สละสลวย, ชัดเจน, และเป็นธรรมชาติ เหมาะสำหรับภาษาเขียนที่เป็นทางการ"
    if style == "ทั่วไป (Casual)":
        style_instruction = "ปรับสำนวนการเขียนให้อ่านง่าย เป็นธรรมชาติ เหมือนการสนทนาทั่วไป แต่ยังคงความถูกต้องทางไวยากรณ์"
    
    dictionary_instruction = ""
    if dictionary:
        dict_words = ", ".join(f"'{word}'" for word in dictionary)
        dictionary_instruction = f"**ข้อยกเว้น:** คำต่อไปนี้ถูกต้องเสมอและห้ามแก้ไขเด็ดขาด: {dict_words}"

    prompt = f"""
    คุณคือบรรณาธิการ (Editor) ภาษาไทยมืออาชีพ ภารกิจของคุณคือตรวจสอบและแก้ไขข้อความต่อไปนี้ให้สมบูรณ์แบบ
    **คำสั่ง:**
    1. **แก้ไข:** ตรวจหาและแก้ไขข้อผิดพลาดทั้งหมด (การสะกด, ไวยากรณ์, เว้นวรรค, ใช้คำผิด)
    2. **ปรับสำนวน:** {style_instruction}
    3. **สร้างรายงาน:** สรุปรายการแก้ไขทั้งหมด โดยระบุ "คำเดิม", "แก้ไขเป็น", และ "เหตุผล"
    4. {dictionary_instruction}
    **ข้อความต้นฉบับ:**
    ---
    {text_to_check}
    ---
    **รูปแบบผลลัพธ์ (สำคัญมาก):**
    [CORRECTED_TEXT_START]
    <ข้อความทั้งหมดที่แก้ไขแล้ว>
    [CORRECTED_TEXT_END]
    [EXPLANATION_START]
    - **คำเดิม:** '...' -> **แก้ไขเป็น:** '...' | **เหตุผล:** ...
    [EXPLANATION_END]
    """
    response_text = call_gemini_api(prompt, api_key)
    if response_text:
        try:
            corrected = response_text.split('[CORRECTED_TEXT_END]')[0].split('[CORRECTED_TEXT_START]')[1].strip()
            explanation = response_text.split('[EXPLANATION_END]')[0].split('[EXPLANATION_START]')[1].strip()
            add_log(f"ตรวจพิสูจน์อักษรสำเร็จ ({len(text_to_check)} ตัวอักษร)")
            return corrected, explanation
        except IndexError:
            st.error("AI ไม่ได้ตอบกลับตามรูปแบบที่กำหนด", icon="🧩")
            st.code(response_text)
            add_log("ตรวจพิสูจน์อักษรล้มเหลว: AI ตอบกลับผิดรูปแบบ")
            return None, None
    add_log("ตรวจพิสูจน์อักษรล้มเหลว: ไม่มีการตอบกลับจาก API")
    return None, None

def get_analysis_result(text_to_check: str, api_key: str):
    prompt = f"""
    คุณคือ นักวิเคราะห์เนื้อหา (Content Analyst) วิเคราะห์ข้อความต่อไปนี้และให้ผลลัพธ์ตามหัวข้อ
    **ข้อความที่ต้องการวิเคราะห์:**
    ---
    {text_to_check}
    ---
    **รูปแบบผลลัพธ์:**
    [SUMMARY_START]<สรุปใจความสำคัญ 2-3 ประโยค>[SUMMARY_END]
    [TONE_START]<วิเคราะห์โทนโดยรวมของเนื้อหา พร้อมเหตุผล>[TONE_END]
    [READABILITY_START]<ให้คะแนนความน่าอ่านจาก 1-10 พร้อมคำแนะนำ>[READABILITY_END]
    """
    response_text = call_gemini_api(prompt, api_key)
    if response_text:
        try:
            summary = response_text.split('[SUMMARY_END]')[0].split('[SUMMARY_START]')[1].strip()
            tone = response_text.split('[TONE_END]')[0].split('[TONE_START]')[1].strip()
            readability = response_text.split('[READABILITY_END]')[0].split('[READABILITY_START]')[1].strip()
            add_log(f"วิเคราะห์บทความสำเร็จ ({len(text_to_check)} ตัวอักษร)")
            return summary, tone, readability
        except IndexError:
            st.error("AI ไม่ได้ตอบกลับตามรูปแบบที่กำหนด", icon="🧩")
            st.code(response_text)
            add_log("วิเคราะห์บทความล้มเหลว: AI ตอบกลับผิดรูปแบบ")
            return None, None, None
    add_log("วิเคราะห์บทความล้มเหลว: ไม่มีการตอบกลับจาก API")
    return None, None, None

def init_session_state():
    state_defaults = {
        'corrected_text': "", 'explanation': "", 'analysis_results': None,
        'authenticated': False, 'dictionary': set(load_from_file(DICTIONARY_FILE))
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- ส่วนของหน้าตาโปรแกรม (Streamlit UI) ---
with st.sidebar:
    st.title("เครื่องมือและตัวเลือก")
    
    # --- พจนานุกรมส่วนตัว (อยู่บนสุด) ---
    st.subheader("📚 พจนานุกรมส่วนตัว")
    with st.form("dict_form", clear_on_submit=True):
        new_word = st.text_input("เพิ่มคำที่ต้องการยกเว้น")
        submitted = st.form_submit_button("เพิ่มคำ")
        if submitted and new_word and new_word not in st.session_state.dictionary:
            st.session_state.dictionary.add(new_word)
            save_to_file(DICTIONARY_FILE, st.session_state.dictionary)
            st.success(f"เพิ่มคำว่า '{new_word}'")
                
    if st.session_state.dictionary:
        with st.expander("แสดง/ลบคำในพจนานุกรม"):
            for word in sorted(list(st.session_state.dictionary)):
                c1, c2 = st.columns([3, 1])
                c1.write(f"- {word}")
                if c2.button("ลบ", key=f"del_{word}", use_container_width=True):
                    st.session_state.dictionary.remove(word)
                    save_to_file(DICTIONARY_FILE, st.session_state.dictionary)
                    st.rerun()
    
    st.divider()

    # --- ส่วนตั้งค่า (พับเก็บได้) ---
    with st.expander("⚙️ ตั้งค่า API", expanded=False):
        password_input = st.text_input("รหัสผ่านสำหรับแก้ไขคีย์", type="password", key="pwd_input")
        if st.button("ปลดล็อก"):
            if password_input and hashlib.md5(password_input.encode()).hexdigest() == CORRECT_PASSWORD_HASH:
                st.session_state.authenticated = True
                st.success("ปลดล็อกสำเร็จ!")
            else:
                st.session_state.authenticated = False
                st.error("รหัสผ่านไม่ถูกต้อง")
        
        api_key_input = st.text_input(
            "Google AI API Key", type="password", 
            value="AIzaSyCFcpERGjX-Y890v61yn7RbQHNsTqg0dTQ",
            disabled=not st.session_state.authenticated,
            key="api_key_widget"
        )
        st.caption("รับคีย์ได้ที่ [aistudio.google.com](https://aistudio.google.com/)")

    # --- ส่วนประวัติการทำงาน (Log) ---
    st.divider()
    with st.expander("📝 ประวัติการทำงาน (Log)", expanded=False):
        logs = load_from_file(LOG_FILE)
        if logs:
            log_text = "\n".join(logs[::-1]) # แสดง log ล่าสุดก่อน
            st.text_area("Log", value=log_text, height=200, disabled=True)
            if st.button("ล้างประวัติ"):
                save_to_file(LOG_FILE, [])
                st.rerun()
        else:
            st.info("ยังไม่มีประวัติการทำงาน")


st.title("✍️ ผู้ช่วยนักเขียน AI อัจฉริยะ")
st.markdown("พิสูจน์อักษร, วิเคราะห์คุณภาพ, และปรับปรุงงานเขียนภาษาไทยของคุณ")

uploaded_file = st.file_uploader("หรืออัปโหลดเอกสาร (.txt / .docx)", type=['txt', 'docx'])
if uploaded_file:
    try:
        if uploaded_file.type == "text/plain":
            st.session_state.input_text = uploaded_file.getvalue().decode("utf-8")
        else:
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            st.session_state.input_text = "\n".join([p.text for p in doc.paragraphs])
        st.success("อ่านไฟล์เรียบร้อยแล้ว!")
        st.session_state.corrected_text, st.session_state.explanation, st.session_state.analysis_results = "", "", None
    except Exception as e:
        st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")

col1, col2 = st.columns(2, gap="medium")
with col1:
    st.subheader("ข้อความต้นฉบับ")
    input_text = st.text_area("ป้อนข้อความ...", height=300, key="input_text")
    
    caption_col, button_col = st.columns([4, 1])
    with caption_col:
        char_count, word_count = len(input_text), len(input_text.split())
        st.caption(f"จำนวนตัวอักษร: {char_count} | จำนวนคำ (โดยประมาณ): {word_count}")
    with button_col:
        if st.button("🧹 ล้าง", use_container_width=True, help="ล้างข้อความทั้งหมด"):
            st.session_state.input_text = ""
            st.session_state.corrected_text, st.session_state.explanation, st.session_state.analysis_results = "", "", None
            st.rerun()
            
    st.markdown("---")
    
    st.write("**เครื่องมือควบคุม:**")
    control_cols = st.columns([1.5, 2.5, 2.5])
    editing_style = control_cols[0].selectbox("สไตล์การแก้", ("ทางการ (Formal)", "ทั่วไป (Casual)"), label_visibility="collapsed")

    if control_cols[1].button("✅ ตรวจพิสูจน์อักษร", type="primary", use_container_width=True):
        if input_text and api_key_input:
            with st.spinner("AI กำลังตรวจพิสูจน์อักษร..."):
                corrected, explanation = get_proofread_result(input_text, api_key_input, editing_style, st.session_state.dictionary)
            st.session_state.corrected_text = corrected or ""
            st.session_state.explanation = explanation or ""
            st.session_state.analysis_results = None
            st.rerun()
        else:
            st.warning("กรุณาป้อนข้อความและ API Key")

    if control_cols[2].button("✨ วิเคราะห์บทความ", use_container_width=True):
        if input_text and api_key_input:
            with st.spinner("AI กำลังวิเคราะห์บทความ..."):
                summary, tone, readability = get_analysis_result(input_text, api_key_input)
            st.session_state.analysis_results = {"summary": summary, "tone": tone, "readability": readability}
            st.session_state.corrected_text, st.session_state.explanation = "", ""
            st.rerun()
        else:
            st.warning("กรุณาป้อนข้อความและ API Key")

with col2:
    st.subheader("ฉบับแก้ไขโดย AI")
    output_container = st.container(height=405, border=True)
    output_container.markdown(st.session_state.corrected_text)

st.divider()
if st.session_state.analysis_results and all(st.session_state.analysis_results.values()):
    st.subheader("ผลการวิเคราะห์บทความ")
    res = st.session_state.analysis_results
    st.success(f"**สรุปใจความสำคัญ:** {res['summary']}", icon="🎯")
    st.info(f"**โทนของเนื้อหา:** {res['tone']}", icon="🗣️")
    st.warning(f"**คะแนนความน่าอ่าน:** {res['readability']}", icon="⭐")

if st.session_state.explanation:
    with st.expander("📄 ดูคำอธิบายการแก้ไขทั้งหมด", expanded=True):
        st.markdown(st.session_state.explanation)
    
    download_cols = st.columns(2)
    download_cols[0].download_button("📥 ดาวน์โหลดฉบับแก้ไข (.txt)", st.session_state.corrected_text, "corrected_text.txt", use_container_width=True)
    download_cols[1].download_button("📥 ดาวน์โหลดคำอธิบาย (.txt)", st.session_state.explanation, "explanation.txt", use_container_width=True)

st.divider()
st.markdown("สร้างโดย **WH41E**")