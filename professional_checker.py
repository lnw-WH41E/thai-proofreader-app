import streamlit as st
import google.generativeai as genai

# --- ตั้งค่าหน้าเว็บหลัก ---
st.set_page_config(
    page_title="เครื่องมือพิสูจน์อักษรภาษาไทย AI",
    page_icon="✍️",
    layout="wide"
)

# --- ส่วนของการเชื่อมต่อกับ Gemini API ---

@st.cache_data(show_spinner=False)
def proofread_with_gemini(text_to_check: str, api_key: str):
    """
    ส่งข้อความให้ Gemini ตรวจและแก้ไข พร้อมคำอธิบายอย่างละเอียด
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        คุณคือบรรณาธิการ (Editor) ภาษาไทยมืออาชีพที่มีความเชี่ยวชาญสูงสุด 
        ภารกิจของคุณคือการตรวจสอบและแก้ไขข้อความต่อไปนี้ให้สมบูรณ์แบบที่สุด

        **คำสั่ง:**
        1.  **แก้ไขข้อความ:** ตรวจหาและแก้ไขข้อผิดพลาดทั้งหมด รวมถึงการสะกดคำ, ไวยากรณ์, การเว้นวรรค, และการใช้คำผิดบริบท
        2.  **ปรับสำนวน:** ปรับแก้สำนวนการเขียนให้สละสลวย, ชัดเจน, และเป็นธรรมชาติ เหมาะสำหรับภาษาเขียนที่เป็นทางการ
        3.  **สร้างรายงาน:** สรุปรายการแก้ไขทั้งหมด โดยระบุ "คำเดิม", "คำที่แก้ไข", และ "เหตุผล" ที่แก้ไขอย่างสั้นกระชับและเข้าใจง่าย

        **ข้อความต้นฉบับ:**
        ---
        {text_to_check}
        ---

        **รูปแบบผลลัพธ์ที่ต้องการ (สำคัญมาก):**
        กรุณาตอบกลับในรูปแบบตามโครงสร้างด้านล่างนี้เท่านั้น ห้ามมีข้อความอื่นนอกเหนือจากนี้:

        [CORRECTED_TEXT_START]
        <ข้อความทั้งหมดที่ผ่านการแก้ไขและปรับสำนวนแล้ว>
        [CORRECTED_TEXT_END]

        [EXPLANATION_START]
        - **คำเดิม:** '...' -> **แก้ไขเป็น:** '...' | **เหตุผล:** ...
        - **ไวยากรณ์:** '...' -> **แก้ไขเป็น:** '...' | **เหตุผล:** ...
        [EXPLANATION_END]
        """
        
        response = model.generate_content(prompt)
        response_text = response.text
        
        corrected_text_part = response_text.split('[CORRECTED_TEXT_END]')[0].split('[CORRECTED_TEXT_START]')[1].strip()
        explanation_part = response_text.split('[EXPLANATION_END]')[0].split('[EXPLANATION_START]')[1].strip()
        
        return corrected_text_part, explanation_part

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อกับ Gemini API: {e}", icon="🚨")
        return None, None

# --- ส่วนของหน้าตาโปรแกรม (Streamlit UI) ---

# Initialize session state for non-widget values only
if 'corrected_text' not in st.session_state:
    st.session_state.corrected_text = ""
if 'explanation' not in st.session_state:
    st.session_state.explanation = ""

# --- Sidebar สำหรับใส่ API Key ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.markdown("รับ Google AI API Key ได้ที่ [aistudio.google.com](https://aistudio.google.com/)")
    api_key_input = st.text_input(
        "Google AI API Key", 
        type="password", 
        value="AIzaSyCFcpERGjX-Y890v61yn7RbQHNsTqg0dTQ"
    )

# --- หน้าหลัก ---
st.title("✍️ เครื่องมือพิสูจน์อักษรภาษาไทย AI ระดับมืออาชีพ")
st.markdown("ขับเคลื่อนโดย **Google Gemini 1.5 Flash**")

# --- Layout แบบ 2 คอลัมน์ ---
col1, col2 = st.columns(2, gap="medium")

with col1:
    st.subheader("ข้อความต้นฉบับ")
    input_text = st.text_area(
        "ป้อนข้อความที่ต้องการตรวจ...", 
        height=350, 
        key="input_text",
        placeholder="ตัวอย่าง: เดืนไปเทียวทะเลกับเพือนๆ สนุกมากๆเลยคัฟ"
    )

    # --- *** ย้ายปุ่มควบคุมมาไว้ตรงนี้ *** ---
    btn_col1, btn_col2 = st.columns([4, 1]) # แบ่งพื้นที่ให้ปุ่มแรกใหญ่กว่า

    with btn_col1:
        if st.button("ตรวจพิสูจน์อักษร", type="primary", use_container_width=True):
            if input_text and api_key_input:
                with st.spinner("AI กำลังวิเคราะห์และแก้ไขข้อความ..."):
                    corrected_text, explanation = proofread_with_gemini(input_text, api_key_input)
                
                if corrected_text is not None and explanation is not None:
                    st.session_state.corrected_text = corrected_text
                    st.session_state.explanation = explanation
                    st.rerun() # สั่งให้รีเฟรชหน้าจอเพื่อแสดงผล
            else:
                st.warning("กรุณาป้อนข้อความและ API Key ก่อน")

    with btn_col2:
        if st.button("ล้าง", use_container_width=True):
            # ลบ key ของ widget และค่าอื่นๆ ใน session state
            if "input_text" in st.session_state:
                del st.session_state["input_text"]
            st.session_state.corrected_text = ""
            st.session_state.explanation = ""
            st.rerun()

with col2:
    st.subheader("ฉบับแก้ไขโดย AI")
    output_container = st.container(height=405, border=True) # ปรับความสูงให้สมดุล
    with output_container:
        st.markdown(st.session_state.corrected_text)

# --- ส่วนแสดงผลคำอธิบาย ---
if st.session_state.explanation:
    st.divider()
    with st.expander("📄 ดูคำอธิบายการแก้ไขทั้งหมด", expanded=True):
        st.markdown(st.session_state.explanation)
        
# --- Footer ---
st.divider()
st.markdown("สร้างโดย **WH41E**")