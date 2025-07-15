import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Test Configuration ---
APP_URL = "https://lnw-wh41e-thai-proofreader-app-professional-checker-euze7e.streamlit.app/"
TEST_SENTENCE = "เดืนทางไปเทียวทะเลกับเพือนๆ สนุกมากๆเลยคัฟ"
EXPECTED_CORRECTION = "เดินทางไปเที่ยวทะเลกับเพื่อนๆ สนุกมากๆเลยครับ"

def run_proofread_test():
    """
    ฟังก์ชันหลักสำหรับรันการทดสอบการพิสูจน์อักษรอัตโนมัติ
    """
    driver = None  # Initialize driver to None
    try:
        # --- 1. Setup WebDriver ---
        print(">>> [1/6] กำลังตั้งค่า WebDriver...")
        options = webdriver.ChromeOptions()
        
        # --- *** การแก้ไข: เพิ่ม Options เพื่อเพิ่มความเสถียร (ชุดสุดท้าย) *** ---
        options.add_argument("--headless")  #  <-- รันแบบไม่แสดงหน้าจอเพื่อความเสถียรสูงสุด
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions") # ปิดส่วนขยายทั้งหมด
        options.add_argument("--start-maximized") # เริ่มแบบเต็มจอ
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.get(APP_URL)
        print(">>> [2/6] เปิดแอปพลิเคชันสำเร็จ, รอให้แอปโหลดสักครู่...")
        
        # --- *** เพิ่ม: รอ 5 วินาทีเพื่อให้แอป Streamlit โหลดสมบูรณ์ *** ---
        time.sleep(5) 

        # --- 2. Input Text ---
        # รอจนกว่าช่อง text area จะพร้อมใช้งาน แล้วพิมพ์ประโยคทดสอบเข้าไป
        wait = WebDriverWait(driver, 45) # เพิ่มเวลารอเป็น 45 วินาที เผื่อแอปโหลดช้า
        text_area = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "textarea[aria-label='ป้อนข้อความ...']")))
        text_area.send_keys(TEST_SENTENCE)
        print(f">>> [3/6] ป้อนข้อความทดสอบ: '{TEST_SENTENCE}'")

        # --- 3. Click Proofread Button ---
        # ค้นหาและคลิกปุ่ม "ตรวจพิสูจน์อักษร"
        proofread_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='✅ ตรวจพิสูจน์อักษร']]")))
        proofread_button.click()
        print(">>> [4/6] คลิกปุ่มตรวจพิสูจน์อักษรแล้ว, AI กำลังประมวลผล...")

        # --- 4. Wait for and Get Results ---
        # รอให้ผลลัพธ์แสดงในกล่องด้านขวา
        output_container_xpath = "(//div[contains(@data-testid, 'stVerticalBlock')])[2]//div[contains(@data-testid, 'stMarkdownContainer')]"
        
        wait.until(
            EC.text_to_be_present_in_element(
                (By.XPATH, output_container_xpath), 
                "เดินทาง" # รอจนกว่าคำว่า 'เดินทาง' จะปรากฏขึ้น
            )
        )
        time.sleep(1) 
        
        # ดึงข้อความที่แก้ไขแล้ว
        corrected_text_element = driver.find_element(By.XPATH, output_container_xpath)
        corrected_text = corrected_text_element.text.strip()
        print(">>> [5/6] ได้รับผลลัพธ์จาก AI เรียบร้อยแล้ว")
        
        # --- 5. Verify the result ---
        print("\n" + "="*30)
        print("      ผลการทดสอบอัตโนมัติ")
        print("="*30)
        print(f"ข้อความต้นฉบับ:\n  '{TEST_SENTENCE}'")
        print(f"\nข้อความที่แก้ไขโดย AI:\n  '{corrected_text}'")
        print(f"\nข้อความที่คาดหวัง:\n  '{EXPECTED_CORRECTION}'")
        print("="*30)

        if corrected_text == EXPECTED_CORRECTION:
            print("✅ PASSED: ผลลัพธ์การแก้ไขถูกต้อง!")
        else:
            print("❌ FAILED: ผลลัพธ์การแก้ไขไม่ตรงกับที่คาดหวัง")
        print("="*30 + "\n")

    except Exception as e:
        print(f"\n[ERROR] เกิดข้อผิดพลาดระหว่างการทดสอบ: {e}")

    finally:
        # --- 6. Teardown ---
        if driver:
            print(">>> [6/6] ปิดเบราว์เซอร์")
            driver.quit()

if __name__ == "__main__":
    run_proofread_test()
