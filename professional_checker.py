import streamlit as st
import google.generativeai as genai
import textwrap

# --- ตั้งค่าหน้าเว็บหลัก ---
st.set_page_config(
    page_title="เครื่องมือพิสูจน์อักษรภาษาไทย AI",
    page_icon="✍️",
    layout="wide"
)

# --- ส่วนของการเชื่อมต่อกับ Gemini API ---

@st.cache_data(show_spinner=False) # Cache a result to prevent re-running on every interaction
def proofread_with_gemini(text_to_check: str, api_key: str):
    """
    ส่งข้อความให้ Gemini ตรวจและแก้ไข พร้อมคำอธิบายอย่างละเอียด
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prompt ที่ออกแบบมาอย่างดีเพื่อให้ AI ทำหน้าที่เป็นบรรณาธิการมืออาชีพ
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
        
        # การแยกส่วนข้อมูลจาก Response ที่มีโครงสร้างชัดเจน
        response_text = response.text
        
        corrected_text_part = response_text.split('[CORRECTED_TEXT_END]')[0].split('[CORRECTED_TEXT_START]')[1].strip()
        explanation_part = response_text.split('[EXPLANATION_END]')[0].split('[EXPLANATION_START]')[1].strip()
        
        return corrected_text_part, explanation_part

    except Exception as e:
        # จัดการข้อผิดพลาดที่อาจเกิดขึ้น เช่น API Key ไม่ถูกต้อง หรือปัญหาจากเซิร์ฟเวอร์
        st.error(f"เกิดข้อผิดพลาดในการเชื่อมต่อกับ Gemini API: {e}", icon="🚨")
        return None, None

# --- ส่วนของหน้าตาโปรแกรม (Streamlit UI) ---

# ใช้ session_state เพื่อเก็บค่าระหว่างการทำงาน
if 'corrected_text' not in st.session_state:
    st.session_state.corrected_text = ""
if 'explanation' not in st.session_state:
    st.session_state.explanation = ""

# --- Sidebar สำหรับใส่ API Key ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า")
    st.markdown("รับ Google AI API Key ได้ที่ [aistudio.google.com](https://aistudio.google.com/)")
    # ใส่ API Key ของคุณเป็นค่าเริ่มต้น
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

with col2:
    st.subheader("ฉบับแก้ไขโดย AI")
    # ใช้ st.empty() เพื่อให้สามารถอัปเดตเนื้อหาในภายหลังได้
    output_container = st.container(height=368, border=True)
    with output_container:
        st.markdown(st.session_state.corrected_text)


# --- ปุ่มและส่วนแสดงผลคำอธิบาย ---
if st.button("ตรวจพิสูจน์อักษร", type="primary", use_container_width=True):
    if not input_text:
        st.warning("กรุณาป้อนข้อความที่ต้องการตรวจสอบก่อน", icon="⚠️")
    elif not api_key_input:
        st.warning("กรุณาใส่ API Key ในช่องด้านซ้ายมือ", icon="🔑")
    else:
        with st.spinner("AI กำลังวิเคราะห์และแก้ไขข้อความ..."):
            corrected_text, explanation = proofread_with_gemini(input_text, api_key_input)
        
        if corrected_text is not None and explanation is not None:
            # เก็บผลลัพธ์ไว้ใน session_state
            st.session_state.corrected_text = corrected_text
            st.session_state.explanation = explanation
            
            # อัปเดตเนื้อหาใน output container
            with output_container:
                st.markdown(st.session_state.corrected_text)
            
            # แสดง Expander สำหรับดูคำอธิบาย
            with st.expander("📄 ดูคำอธิบายการแก้ไขทั้งหมด", expanded=True):
                st.markdown(st.session_state.explanation)
        # หากมี Error จะถูกแสดงผลโดยตรงจากฟังก์ชัน proofread_with_gemini

# --- Footer ---
st.divider()
st.markdown("โปรแกรมนี้เป็นโปรเจกต์สาธิตการใช้งาน Generative AI เพื่อการพิสูจน์อักษร")