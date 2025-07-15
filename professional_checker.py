import streamlit as st
import google.generativeai as genai
import hashlib
import os
import io
from docx import Document

# --- การตั้งค่าพื้นฐาน ---
st.set_page_config(
    page_title="ผู้ช่วยนักเขียน AI",
    page_icon="✍️",
    layout="wide"
)

# --- ส่วนจัดการพจนานุกรมส่วนตัว ---
DICTIONARY_FILE = "personal_dictionary.txt"

def load_dictionary():
    """โหลดคำศัพท์จากไฟล์"""
    if not os.path.exists(DICTIONARY_FILE):
        return set()
    with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
        return set(word.strip() for word in f if word.strip())

def save_dictionary(words):
    """บันทึกคำศัพท์ลงไฟล์"""
    with open(DICTIONARY_FILE, "w", encoding="utf-8") as f:
        for word in sorted(list(words)):
            f.write(f"{word}\n")

# --- ส่วนของการเชื่อมต่อกับ Gemini API ---
CORRECT_PASSWORD_HASH = "8c2e3c846b41be4a5e37349a7c36a254"

@st.cache_data(show_spinner=False)
def call_gemini_api(prompt: str, api_key: str):
    """ฟังก์ชันกลางสำหรับเรียกใช้ Gemini API พร้อม Error Handling"""
    try:
        genai.configure(api_key=api_key)
        request_options = {'timeout': 300} # รอสูงสุด 5 นาที
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, request_options=request_options)
        return response.text
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อกับ Gemini API: {e}", icon="🚨")
        return None

def get_proofread_result(text_to_check, api_key, style, dictionary):
    """สร้าง Prompt และเรียก API สำหรับการพิสูจน์อักษร"""
    style_instruction = "ปรับสำนวนการเขียนให้สละสลวย, ชัดเจน, และเป็นธรรมชาติ เหมาะสำหรับภาษาเขียนที่เป็นทางการ"
    if style == "ทั่วไป (Casual)":
        style_instruction = "ปรับสำนวนการเขียนให้อ่านง่าย เป็นธรรมชาติ เหมือนการสนทนาทั่วไป แต่ยังคงความถูกต้องทางไวยากรณ์"
    
    dictionary_instruction = ""
    if dictionary:
        dict_words = ", ".join(f"'{word}'" for word in dictionary)
        dictionary_instruction = f"**ข้อยกเว้น:** คำต่อไปนี้ถูกต้องเสมอและห้ามแก้ไข: {dict_words}"

    prompt = f"""
    คุณคือบรรณาธิการ (Editor) ภาษาไทยมืออาชีพที่มีความเชี่ยวชาญสูงสุด 
    ภารกิจของคุณคือการตรวจสอบและแก้ไขข้อความต่อไปนี้ให้สมบูรณ์แบบที่สุด

    **คำสั่ง:**
    1. **แก้ไขข้อความ:** ตรวจหาและแก้ไขข้อผิดพลาดทั้งหมด รวมถึงการสะกดคำ, ไวยากรณ์, การเว้นวรรค, และการใช้คำผิดบริบท
    2. **ปรับสำนวน:** {style_instruction}
    3. **สร้างรายงาน:** สรุปรายการแก้ไขทั้งหมด โดยระบุ "คำเดิม", "คำที่แก้ไข", และ "เหตุผล" ที่แก้ไขอย่างสั้นกระชับและเข้าใจง่าย
    4. {dictionary_instruction}

    **ข้อความต้นฉบับ:**
    ---
    {text_to_check}
    ---

    **รูปแบบผลลัพธ์ที่ต้องการ (สำคัญมาก):**
    กรุณาตอบกลับในรูปแบบตามโครงสร้างด้านล่างนี้เท่านั้น:
    [CORRECTED_TEXT_START]
    <ข้อความทั้งหมดที่ผ่านการแก้ไขแล้ว>
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
            return corrected, explanation
        except IndexError:
            st.error("AI ไม่ได้ตอบกลับตามรูปแบบที่กำหนด อาจเกิดปัญหาชั่วคราว ลองใหม่อีกครั้ง", icon=" B")
            st.code(response_text) # แสดงผลดิบที่ได้รับมา
            return None, None
    return None, None

def get_analysis_result(text_to_check, api_key):
    """สร้าง Prompt และเรียก API สำหรับการวิเคราะห์บทความ"""
    prompt = f"""
    คุณคือ นักวิเคราะห์เนื้อหา (Content Analyst) ที่มีความเชี่ยวชาญ 
    วิเคราะห์ข้อความต่อไปนี้และให้ผลลัพธ์ตามหัวข้อที่กำหนด

    **ข้อความที่ต้องการวิเคราะห์:**
    ---
    {text_to_check}
    ---
    
    **รูปแบบผลลัพธ์ที่ต้องการ:**
    [SUMMARY_START]
    <สรุปใจความสำคัญของบทความนี้ภายใน 2-3 ประโยค>
    [SUMMARY_END]
    [TONE_START]
    <วิเคราะห์โทนโดยรวมของเนื้อหา (เช่น ทางการ, เป็นกันเอง, เชิงบวก, จริงจัง) พร้อมให้เหตุผลประกอบสั้นๆ>
    [TONE_END]
    [READABILITY_START]
    <ให้คะแนนความน่าอ่านจาก 1 ถึง 10 (1=อ่านยากมาก, 10=อ่านง่ายมาก) พร้อมคำแนะนำเพื่อปรับปรุง>
    [READABILITY_END]
    """
    response_text = call_gemini_api(prompt, api_key)
    if response_text:
        try:
            summary = response_text.split('[SUMMARY_END]')[0].split('[SUMMARY_START]')[1].strip()
            tone = response_text.split('[TONE_END]')[0].split('[TONE_START]')[1].strip()
            readability = response_text.split('[READABILITY_END]')[0].split('[READABILITY_START]')[1].strip()
            return summary, tone, readability
        except IndexError:
            st.error("AI ไม่ได้ตอบกลับตามรูปแบบที่กำหนด อาจเกิดปัญหาชั่วคราว ลองใหม่อีกครั้ง", icon=" B")
            st.code(response_text)
            return None, None, None
    return None, None, None


# --- ส่วนของหน้าตาโปรแกรม (Streamlit UI) ---

# ใช้ session_state เพื่อเก็บค่าระหว่างการทำงาน
if 'input_text' not in st.session_state: st.session_state.input_text = ""
if 'corrected_text' not in st.session_state: st.session_state.corrected_text = ""
if 'explanation' not in st.session_state: st.session_state.explanation = ""
if 'analysis_results' not in st.session_state: st.session_state.analysis_results = None
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'dictionary' not in st.session_state: st.session_state.dictionary = load_dictionary()

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ ตั้งค่าและเครื่องมือ")
    
    st.subheader("API Key Configuration")
    password_input = st.text_input("รหัสผ่านสำหรับแก้ไขคีย์", type="password")
    if st.button("ยืนยันรหัสผ่าน"):
        if hashlib.md5(password_input.encode()).hexdigest() == CORRECT_PASSWORD_HASH:
            st.session_state.authenticated = True
            st.success("ยืนยันสำเร็จ!")
        else:
            st.session_state.authenticated = False
            st.error("รหัสผ่านไม่ถูกต้อง")
            
    api_key_input = st.text_input(
        "Google AI API Key", type="password", 
        value="AIzaSyCFcpERGjX-Y890v61yn7RbQHNsTqg0dTQ",
        disabled=not st.session_state.authenticated
    )
    st.caption("รับคีย์ได้ที่ [aistudio.google.com](https://aistudio.google.com/)")
    
    st.divider()
    
    # --- พจนานุกรมส่วนตัว ---
    st.subheader("📚 พจนานุกรมส่วนตัว")
    new_word = st.text_input("เพิ่มคำที่ต้องการยกเว้น", help="เช่น ชื่อแบรนด์, ศัพท์เทคนิค")
    if st.button("เพิ่มคำ"):
        if new_word and new_word not in st.session_state.dictionary:
            st.session_state.dictionary.add(new_word)
            save_dictionary(st.session_state.dictionary)
            st.success(f"เพิ่มคำว่า '{new_word}' เรียบร้อยแล้ว")
    
    if st.session_state.dictionary:
        with st.expander("แสดง/ลบคำในพจนานุกรม"):
            for word in sorted(list(st.session_state.dictionary)):
                col1, col2 = st.columns([3, 1])
                col1.write(word)
                if col2.button("ลบ", key=f"del_{word}"):
                    st.session_state.dictionary.remove(word)
                    save_dictionary(st.session_state.dictionary)
                    st.rerun()

# --- หน้าหลัก ---
st.title("✍️ ผู้ช่วยนักเขียน AI อัจฉริยะ")
st.markdown("พิสูจน์อักษร, วิเคราะห์คุณภาพ, และปรับปรุงงานเขียนภาษาไทยของคุณ")

# --- ส่วนอัปโหลดไฟล์ ---
uploaded_file = st.file_uploader("หรืออัปโหลดเอกสาร (.txt / .docx)", type=['txt', 'docx'])
if uploaded_file is not None:
    try:
        if uploaded_file.type == "text/plain":
            st.session_state.input_text = uploaded_file.getvalue().decode("utf-8")
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(io.BytesIO(uploaded_file.getvalue()))
            st.session_state.input_text = "\n".join([para.text for para in doc.paragraphs])
        st.success("อ่านไฟล์เรียบร้อยแล้ว!")
    except Exception as e:
        st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")

# --- Layout แบบ 2 คอลัมน์ ---
col1, col2 = st.columns(2, gap="medium")
with col1:
    st.subheader("ข้อความต้นฉบับ")
    input_text = st.text_area("ป้อนข้อความ...", height=350, key="input_text")
    char_count, word_count = len(input_text), len(input_text.split())
    st.caption(f"จำนวนตัวอักษร: {char_count} | จำนวนคำ (โดยประมาณ): {word_count}")

with col2:
    st.subheader("ฉบับแก้ไขโดย AI")
    output_container = st.container(height=368, border=True)
    output_container.markdown(st.session_state.corrected_text)

# --- ส่วนของปุ่มควบคุม ---
control_cols = st.columns([1.5, 2, 2, 1])
editing_style = control_cols[0].selectbox("สไตล์การแก้", ("ทางการ", "ทั่วไป"), label_visibility="collapsed")

if control_cols[1].button("✅ ตรวจพิสูจน์อักษร", type="primary", use_container_width=True):
    if input_text and api_key_input:
        with st.spinner("AI กำลังตรวจพิสูจน์อักษร..."):
            corrected, explanation = get_proofread_result(input_text, api_key_input, editing_style, st.session_state.dictionary)
        st.session_state.corrected_text = corrected if corrected else ""
        st.session_state.explanation = explanation if explanation else ""
        st.session_state.analysis_results = None # ล้างผลวิเคราะห์เก่า
        st.rerun()
    else:
        st.warning("กรุณาป้อนข้อความและ API Key ก่อน")

if control_cols[2].button("✨ วิเคราะห์บทความ", use_container_width=True):
    if input_text and api_key_input:
        with st.spinner("AI กำลังวิเคราะห์บทความ..."):
            summary, tone, readability = get_analysis_result(input_text, api_key_input)
        st.session_state.analysis_results = {"summary": summary, "tone": tone, "readability": readability}
        st.rerun()
    else:
        st.warning("กรุณาป้อนข้อความและ API Key ก่อน")

if control_cols[3].button("🧹 ล้าง", use_container_width=True):
    st.session_state.input_text = ""
    st.session_state.corrected_text = ""
    st.session_state.explanation = ""
    st.session_state.analysis_results = None
    st.rerun()

# --- ส่วนแสดงผลลัพธ์ ---
st.divider()
if st.session_state.analysis_results:
    st.subheader("ผลการวิเคราะห์บทความ")
    res = st.session_state.analysis_results
    if res["summary"]:
        st.success("**สรุปใจความสำคัญ**", icon="🎯")
        st.write(res["summary"])
    if res["tone"]:
        st.info("**โทนของเนื้อหา**", icon="🗣️")
        st.write(res["tone"])
    if res["readability"]:
        st.warning("**คะแนนความน่าอ่าน**", icon="⭐")
        st.write(res["readability"])

if st.session_state.explanation:
    with st.expander("📄 ดูคำอธิบายการแก้ไขทั้งหมด", expanded=True):
        st.markdown(st.session_state.explanation)
    
    download_cols = st.columns(2)
    download_cols[0].download_button("📥 ดาวน์โหลดฉบับแก้ไข (.txt)", st.session_state.corrected_text, "corrected.txt", use_container_width=True)
    download_cols[1].download_button("📥 ดาวน์โหลดคำอธิบาย (.txt)", st.session_state.explanation, "explanation.txt", use_container_width=True)

# --- Footer ---
st.divider()
st.markdown("สร้างโดย **WH41E**")