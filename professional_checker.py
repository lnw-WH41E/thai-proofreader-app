import streamlit as st
import google.generativeai as genai
import hashlib
import os
import io
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
CORRECT_PASSWORD_HASH = "8c2e3c846b41be4a5e37349a7c36a254"  # MD5 hash for 'Ewhale@123'

@st.cache_data(show_spinner=False)
def call_gemini_api(prompt: str, api_key: str):
    """ฟังก์ชันกลางสำหรับเรียกใช้ Gemini API พร้อม Error Handling"""
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
    """สร้าง Prompt และเรียก API สำหรับการพิสูจน์อักษร"""
    style_instruction = "ปรับสำนวนการเขียนให้สละสลวย, ชัดเจน, และเป็นธรรมชาติ เหมาะสำหรับภาษาเขียนที่เป็นทางการ"
    if style == "ทั่วไป (Casual)":
        style_instruction = "ปรับสำนวนการเขียนให้อ่านง่าย เป็นธรรมชาติ เหมือนการสนทนาทั่วไป แต่ยังคงความถูกต้องทางไวยากรณ์"
    
    dictionary_instruction = ""
    if dictionary:
        dict_words = ", ".join(f"'{word}'" for word in dictionary)
        dictionary_instruction = f"**ข้อยกเว้น:** คำต่อไปนี้ถูกต้องเสมอและห้ามแก้ไขเด็ดขาด: {dict_words}"

    prompt = f"""
    คุณคือบรรณาธิการ (Editor) ภาษาไทยมืออาชีพที่มีความเชี่ยวชาญสูงสุด
    ภารกิจของคุณคือการตรวจสอบและแก้ไขข้อความต่อไปนี้ให้สมบูรณ์แบบที่สุด

    **คำสั่ง:**
    1. **แก้ไขข้อความ:** ตรวจหาและแก้ไขข้อผิดพลาดทั้งหมด
    2. **ปรับสำนวน:** {style_instruction}
    3. **สร้างรายงาน:** สรุปรายการแก้ไขทั้งหมด โดยระบุ "คำเดิม", "คำที่แก้ไข", และ "เหตุผล"
    4. {dictionary_instruction}

    **ข้อความต้นฉบับ:**
    ---
    {text_to_check}
    ---

    **รูปแบบผลลัพธ์ที่ต้องการ (สำคัญมาก):**
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
            st.error("AI ไม่ได้ตอบกลับตามรูปแบบที่กำหนด อาจเกิดปัญหาชั่วคราว ลองใหม่อีกครั้ง", icon="🧩")
            st.code(response_text)
            return None, None
    return None, None

def get_analysis_result(text_to_check: str, api_key: str):
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
            st.error("AI ไม่ได้ตอบกลับตามรูปแบบที่กำหนด อาจเกิดปัญหาชั่วคราว ลองใหม่อีกครั้ง", icon="🧩")
            st.code(response_text)
            return None, None, None
    return None, None, None

# --- ส่วนจัดการ Session State ---
def init_session_state():
    """Initialize session state variables if they don't exist."""
    state_defaults = {
        'corrected_text': "",
        'explanation': "",
        'analysis_results': None,
        'authenticated': False,
        'dictionary': load_dictionary()
    }
    for key, value in state_defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# --- ส่วนของหน้าตาโปรแกรม (Streamlit UI) ---

# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ ตั้งค่าและเครื่องมือ")
    
    st.subheader("API Key Configuration")
    password_input = st.text_input("รหัสผ่านสำหรับแก้ไขคีย์", type="password")
    if st.button("ยืนยันรหัสผ่าน"):
        if password_input:
            hashed_password = hashlib.md5(password_input.encode()).hexdigest()
            if hashed_password == CORRECT_PASSWORD_HASH:
                st.session_state.authenticated = True
                st.success("ยืนยันสำเร็จ!")
            else:
                st.session_state.authenticated = False
                st.error("รหัสผ่านไม่ถูกต้อง")
        else:
            st.warning("กรุณาป้อนรหัสผ่าน")
            
    api_key_input = st.text_input(
        "Google AI API Key", type="password", 
        value="AIzaSyCFcpERGjX-Y890v61yn7RbQHNsTqg0dTQ",
        disabled=not st.session_state.authenticated
    )
    st.caption("รับคีย์ได้ที่ [aistudio.google.com](https://aistudio.google.com/)")
    
    st.divider()
    
    st.subheader("📚 พจนานุกรมส่วนตัว")
    with st.form("dict_form", clear_on_submit=True):
        new_word = st.text_input("เพิ่มคำที่ต้องการยกเว้น")
        submitted = st.form_submit_button("เพิ่มคำ")
        if submitted and new_word:
            if new_word not in st.session_state.dictionary:
                st.session_state.dictionary.add(new_word)
                save_dictionary(st.session_state.dictionary)
                st.success(f"เพิ่มคำว่า '{new_word}' เรียบร้อยแล้ว")
                
    if st.session_state.dictionary:
        with st.expander("แสดง/ลบคำในพจนานุกรม"):
            for word in sorted(list(st.session_state.dictionary)):
                col1, col2 = st.columns([3, 1])
                col1.write(f"- {word}")
                if col2.button("ลบ", key=f"del_{word}", use_container_width=True):
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
        # Clear previous results when a new file is uploaded
        st.session_state.corrected_text = ""
        st.session_state.explanation = ""
        st.session_state.analysis_results = None
    except Exception as e:
        st.error(f"ไม่สามารถอ่านไฟล์ได้: {e}")

# --- Layout แบบ 2 คอลัมน์ ---
col1, col2 = st.columns(2, gap="medium")
with col1:
    st.subheader("ข้อความต้นฉบับ")
    input_text = st.text_area("ป้อนข้อความ...", height=300, key="input_text")
    char_count, word_count = len(input_text), len(input_text.split())
    st.caption(f"จำนวนตัวอักษร: {char_count} | จำนวนคำ (โดยประมาณ): {word_count}")
    
    st.markdown("---") # เส้นคั่น
    
    # --- ส่วนของปุ่มควบคุม (ย้ายมาไว้ตรงนี้) ---
    st.write("**เครื่องมือควบคุม:**")
    control_cols = st.columns([1.5, 2, 2, 1])
    editing_style = control_cols[0].selectbox("สไตล์การแก้", ("ทางการ (Formal)", "ทั่วไป (Casual)"), label_visibility="collapsed")

    if control_cols[1].button("✅ ตรวจพิสูจน์อักษร", type="primary", use_container_width=True):
        if input_text and api_key_input:
            with st.spinner("AI กำลังตรวจพิสูจน์อักษร..."):
                corrected, explanation = get_proofread_result(input_text, api_key_input, editing_style, st.session_state.dictionary)
            st.session_state.corrected_text = corrected if corrected else ""
            st.session_state.explanation = explanation if explanation else ""
            st.session_state.analysis_results = None
            st.rerun()
        else:
            st.warning("กรุณาป้อนข้อความและ API Key ก่อน")

    if control_cols[2].button("✨ วิเคราะห์บทความ", use_container_width=True):
        if input_text and api_key_input:
            with st.spinner("AI กำลังวิเคราะห์บทความ..."):
                summary, tone, readability = get_analysis_result(input_text, api_key_input)
            st.session_state.analysis_results = {"summary": summary, "tone": tone, "readability": readability}
            st.session_state.corrected_text = ""
            st.session_state.explanation = ""
            st.rerun()
        else:
            st.warning("กรุณาป้อนข้อความและ API Key ก่อน")

    if control_cols[3].button("🧹 ล้าง", use_container_width=True):
        # This is the correct way to clear states to avoid errors
        st.session_state.input_text = ""
        st.session_state.corrected_text = ""
        st.session_state.explanation = ""
        st.session_state.analysis_results = None
        st.rerun()

with col2:
    st.subheader("ฉบับแก้ไขโดย AI")
    output_container = st.container(height=405, border=True)
    output_container.markdown(st.session_state.corrected_text)

# --- ส่วนแสดงผลลัพธ์ ---
st.divider()

# Display Analysis Results if they exist
if st.session_state.analysis_results and all(st.session_state.analysis_results.values()):
    st.subheader("ผลการวิเคราะห์บทความ")
    res = st.session_state.analysis_results
    st.success(f"**สรุปใจความสำคัญ:** {res['summary']}", icon="🎯")
    st.info(f"**โทนของเนื้อหา:** {res['tone']}", icon="🗣️")
    st.warning(f"**คะแนนความน่าอ่าน:** {res['readability']}", icon="⭐")

# Display Proofreading Explanation if it exists
if st.session_state.explanation:
    with st.expander("📄 ดูคำอธิบายการแก้ไขทั้งหมด", expanded=True):
        st.markdown(st.session_state.explanation)
    
    download_cols = st.columns(2)
    download_cols[0].download_button("📥 ดาวน์โหลดฉบับแก้ไข (.txt)", st.session_state.corrected_text, "corrected_text.txt", use_container_width=True)
    download_cols[1].download_button("📥 ดาวน์โหลดคำอธิบาย (.txt)", st.session_state.explanation, "explanation.txt", use_container_width=True)

# --- Footer ---
st.divider()
st.markdown("สร้างโดย **WH41E**")