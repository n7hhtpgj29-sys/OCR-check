Customs OCR Windows 10 Portable — ชุดสร้าง EXE (ยังไม่ใช่ EXE สำเร็จรูป)

เครื่องปลายทาง Windows 10 x64: ไม่ต้องติดตั้ง Python หรือเชื่อมต่ออินเทอร์เน็ต
เครื่อง Build: ใช้ GitHub Actions Windows runner ซึ่งต้องเชื่อมต่ออินเทอร์เน็ต

ขั้นตอนสร้างไฟล์ EXE
1) สร้าง GitHub repository แบบ Private
2) อัปโหลดไฟล์และโฟลเดอร์ทั้งหมดใน ZIP นี้ไปที่ repository โดยคง .github/workflows/build-windows.yml
3) เข้าแท็บ Actions -> Build Customs OCR Windows 10 Portable -> Run workflow
4) รอ build เสร็จ ดาวน์โหลด artifact CustomsOCR_Win10_Portable
5) แตก ZIP ที่ดาวน์โหลด แล้วคัดลอกโฟลเดอร์ CustomsOCR ไปยัง Windows 10 x64
6) ดับเบิลคลิก CustomsOCR.exe เปิดหน้า http://127.0.0.1:8501
7) เปิด sample.pdf เพื่อทดสอบ

หมายเหตุ:
- โปรแกรมเปิดเว็บในเครื่องตัวเองเท่านั้น; ไม่ส่งข้อมูลไป Cloud
- มี Tesseract ภาษาไทย/อังกฤษอยู่ในโฟลเดอร์หลัง Build
- Build ต้องทดสอบจริงบน Windows 10; อาจติดปัญหา antivirus/IT policy
- ข้อมูล OCR เป็นการอ่านอัตโนมัติ ต้องตรวจทานก่อนนำเข้า System
- กฎดึงข้อมูลใน v1.1 ยังอิงโครงสร้างใบขนตัวอย่าง; เอกสารรูปแบบอื่นอาจอ่านไม่ครบ
- ชุดนี้ไม่ได้รวม EXE ที่ Build เสร็จแล้ว เพราะสร้าง Windows binary ในสภาพแวดล้อมปัจจุบันไม่ได้
