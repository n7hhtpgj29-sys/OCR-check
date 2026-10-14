Customs OCR v1.2 COMPLETE
ไฟล์ทั้งหมดพร้อมใช้งานสำหรับ GitHub repository OCR-check
วิธีง่าย: ใช้ UPDATE_GITHUB.bat (ต้องมี Git for Windows และสิทธิ์เข้าถึง repo)
หรืออัปโหลดไฟล์ด้วย GitHub ตามโครงสร้าง .github/workflows/main.yml
จากนั้น Actions > Run workflow แล้วดาวน์โหลด Artifact
เครื่องปลายทางไม่ต้องมี Python แต่ยังต้อง build exe ด้วย GitHub Actions
หมายเหตุ: PDF สแกนภาพยังไม่รองรับ OCR Offline; ต้องเพิ่ม Tesseract engine
