Customs OCR v2.0 — Multi-Forwarder (prototype)
1) อัปโหลดไฟล์ทั้งหมดใน ZIP ไปยัง GitHub repository root โดยคงโครงสร้าง .github/workflows/main.yml และ templates/
2) Actions > Build Customs OCR v2 Windows Portable > Run workflow
3) ดาวน์โหลด Artifact CustomsOCR_v2_Win10_Portable แล้วแตก ZIP ทั้งชุด เปิด CustomsOCR.exe
4) เครื่องปลายทางไม่ต้องลง Python แต่ Windows Defender/IT อาจบล็อก EXE; ให้ IT ตรวจและอนุญาตตามนโยบาย
5) Forwarder detection ใช้ชื่อ/alias + layout anchors จากไฟล์ templates/*.json
6) หากไม่พบ template ระบบใช้ generic rules และต้องตรวจทานทุกช่อง
7) Summary ดึงโดยค้นจากหน้าท้ายย้อนกลับ หากไม่ใช่หน้าสุดท้ายจะไม่เติมค่าอัตโนมัติ
8) ทุกค่าแสดง candidate page และให้แก้ก่อนกด Approve
ข้อจำกัด: PDF แบบสแกนภาพล้วนยังไม่มี OCR engine ติดมาด้วย; ต้องเพิ่ม Tesseract/Windows OCR ในรุ่นต่อไป
ข้อจำกัด: Generic rules ยังไม่รับประกันการอ่านครบสำหรับเอกสารจากทุก Forwarder; ต้องทดสอบ PDF จริง
ข้อจำกัด: Excel ใช้โครงสร้าง Upload_Data แบบทั่วไป ยังต้อง map กับคอลัมน์จริงของระบบปลายทาง
การแก้ template JSON: กำหนด forwarder_aliases, layout_anchors, rules.<Field>.labels, pattern, scope
ไม่มีการ hardcode ค่า RTCMASTER/JP/TEST-001
