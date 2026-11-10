# OLGM Ultimate — S-10 Production Acceptance Runbook v0.9

## สถานะการตรวจรับ

**ยังไม่ผ่าน S-10 Production.** โค้ดและผลทดสอบในแพ็กเกจนี้เป็นหลักฐานระดับ local engineering เท่านั้น ไม่มีการแสร้งว่ายืนยันตัวตน Origin, สภาพแวดล้อม X-admin, โมเดลที่ฝึกจริง หรือความถูกต้องของข้อเท็จจริงแล้ว

สถานะต้องแยกออกเป็น 4 ระดับ: (1) IMPLEMENTED (2) LOCAL TEST PASSED (3) EXTERNAL/PRODUCTION TEST PASSED (4) ORIGIN + INDEPENDENT REVIEWER SIGNED ACCEPTANCE. ระดับสุดท้ายเกิดหลังตรวจหลักฐานครบทั้ง 20 เกณฑ์เท่านั้น

## ขอบเขตอธิปไตยทางปัญญา

- Core 0 เป็นขอบเขตแนวคิด ไม่ใช่ endpoint ที่ AI แก้ไขได้
- Origin ให้สิทธิ์เฉพาะด้วยช่องทางยืนยันตัวตนอิสระ; `--actor` หรือชื่อใน Prompt ไม่ใช่หลักฐานอำนาจ
- Canonical/Archive เดิมต้องไม่ถูกแก้ไขโดย Runtime; ทุก Delta มี lineage และการอนุมัติ
- ข้อมูลที่ AI เรียนรู้มี source, license, classification และ approval; ปฏิเสธ external model egress จาก production HTTP API จนมี policy และ origin release
- Code mutation ใน Production ปิดไว้; G-06 ใช้งานใน Development/Staging ได้ตาม Signed Approval เท่านั้น

## วิธีใช้บน X-admin / เครื่องเป้าหมาย

1. ให้ผู้ดูแลเชื่อม X-admin เข้ากับเครื่องมือบริหารที่ได้รับอนุญาตอีกครั้ง (ตรวจ ณ รอบนี้เครื่อง Offline) และตรวจชื่อเครื่อง/OS/Python/Disk/Port/นโยบาย Firewall จริง
2. ตรวจ SHA-256 ของ ZIP จากผู้ส่งมอบก่อนแตกไฟล์ ห้ามทับ Canonical/Archive และฐานข้อมูลจริง; ทดสอบใน staging ก่อน
3. ทำ snapshot สำรองฐานข้อมูลจริงไปปลายทางแยกที่ได้รับอนุญาต ก่อนปรับใช้งานและเก็บหลักฐานเวลา/ผู้ทำ
4. ตั้งค่าตัวแปร `OLGM_DB` ไปยัง DB ของ staging; ตั้ง `OLGM_HTTP_TOKEN` เป็นความลับที่สุ่มอย่างปลอดภัยจากแหล่งภายนอก; อย่าใส่ token ในอีเมลหรือ log
5. ใช้ `deploy/windows/preflight.ps1` บน PowerShell หรือ `deploy/linux/preflight.sh` บน Linux; ผล `BLOCKED` เป็นสิ่งที่ถูกต้องตราบใดที่หลักฐานภายนอกยังขาด
6. รัน `python runtime.py s10-capture --output docs/LOCAL_TEST_CAPTURE_MACHINE.json` ใน Staging; ห้ามนำผลทดสอบบนคอมพิวเตอร์อื่นอ้างเป็นผล X-admin
7. รัน `python runtime.py s10-evaluate --test-capture docs/LOCAL_TEST_CAPTURE_MACHINE.json --output docs/S10_MACHINE_REPORT.json` แล้วกรอกแต่ละเกณฑ์จาก `docs/S10_V09_ACCEPTANCE_MATRIX.json` โดยผู้ประเมินที่ตรวจสอบตัวตนได้
8. ประเมิน endpoint ที่เข้าถึงจริง: Reverse Proxy TLS, IdP/RBAC, rate limits, audit logs, vulnerability scans; API ปัจจุบันผูกไว้กับ loopback เท่านั้นและไม่ใช่ production identity gateway
9. ประเมิน T06 Live Model, T17 Adapter training/Blind evaluation, T19 Fact Verification, G06 Novel Capability, Thai Heldout; รายงานคะแนนจาก raw evidence ไม่ใช้คะแนนตัวอย่างที่สร้างขึ้น
10. ให้ Origin และผู้ตรวจอิสระลงนามที่ผูกกับ package hash, policy version, หลักฐานรายข้อ และรายการข้อยกเว้น ก่อนมีการอนุมัติปล่อยใช้จริง

## ข้อที่ระบบนี้ตรวจได้เอง

`production-preflight` ตรวจรูปแบบ Token (ไม่ใช่การพิสูจน์ entropy), การจำกัด listener, integrity ของ SQLite, grant ที่ยังใช้งานอยู่, hash chain, checkpoint ledger, canonical ledger และการกู้คืนฐานข้อมูลใน tempfile ไม่แก้ข้อมูลจริง

## ข้อที่ไม่อาจตรวจรับจากโค้ดอย่างเดียว

Identity of Origin, PDPA compliance, public-facing TLS, off-site anchors, off-site backup RTO/RPO, independent benchmark, actual models and weights, external action effects, and independent signoff — ต้องมีหลักฐานจากระบบเป้าหมายและผู้รับผิดชอบจริง

## ข้อบ่งชี้ข้อจำกัด

- `OLGM_ENV=production` ปิด CLI สำหรับการ grant-dev, key enrollment แบบทดสอบ, การแก้ Canonical, การ execute เขียนข้อมูล/แก้โค้ดและการอนุมัติแบบ developer; การใช้งาน Production แบบเขียนจริงต้องสร้างและตรวจ Identity/Policy Gateway แยกต่างหาก **ยังไม่ได้เปิดให้ใช้งานจริง**
- API แบบ loopback ยังไม่ใช่ HTTPS Internet/LAN service; ไม่ควรเปิด Port ออกภายนอก
- `S-10` ยัง `NOT_PASSED` โดยออกแบบให้ fail-closed และจะไม่ยอมรับเพียงไฟล์เขียนว่า `PASS`
- ข้อกำหนดตามระเบียบกฎหมายหรือมาตรฐานสากลต้องมีผู้เชี่ยวชาญและหน่วยงานมีอำนาจประเมิน ไม่ใช่ผลรับรองจากตัวโปรแกรมเอง
