# ชุดองค์ความรู้จากบทสนทนา
ผู้ริเริ่มแนวคิด: ธีรนาท บุตรดา (Teeranat Butda)
วันที่รวบรวม: 8 พฤศจิกายน 2569

ชุดนี้มีภาพรวม 11 หัวข้อ และโมดูลรายละเอียดเพิ่มเติมจากแหล่งที่ตรวจอ่านได้ ไม่ใช่การรับรองว่าครอบคลุมบทสนทนาทั้งหมด และยังไม่ใช่การแก้ Canonical ต้นฉบับ

## เนื้อหา
- [Meaning Space และการใช้เส้นทางเดิม](01-meaning-space.md)
- [แยกการคิด การลงมือ และการตรวจ](02-execution-verification.md)
- [เกณฑ์ Benchmark](03-benchmark.md)
- [Semantic Particle Field](04-semantic-particle-field.md)

- [Make END และการควบคุมงานตั้งแต่ Blueprint ถึงส่งมอบ](05-make-end.md)
- [ATHENA SME และความสัมพันธ์ทางธุรกิจ](06-sme-architecture.md)
- [แกนอ้างอิงความจริง](07-truth-reference-anchor.md)
- [BigMap ข้อมูลกลางและพิกัด](08-bigmap-data-coordinates.md)
- [Surface TIN และข้อมูลภูมิประเทศ](09-surface-tin.md)
- [OCR ใบอนุญาตและการเชื่อมแผนที่](10-permit-ocr.md)
- [เปรียบเทียบวิธีคิด 18 รูปแบบและ 18 Way Matrix](11-reasoning-methods-comparison.md)

## Meaning Space และ Semantic ฉบับรายละเอียด
- [Meaning Space และหน่วยความหมายในโครงสร้าง](semantic/meaning-space-structure.md)
- [Semantic Relations และที่อยู่ของความหมาย](semantic/semantic-relations-and-addresses.md)
- [แยกการนำเข้าความรู้จากการค้นคืน](semantic/semantic-ingestion-and-retrieval.md)
- [Intent Resonance และการคัดเส้นทาง](semantic/intent-resonance-and-ranking.md)
- [Semantic Gap และการค้นหาวิธีตามเงื่อนไข](semantic/semantic-gap-and-method-search.md)
- [การนำทางความหมายและข้อจำกัดของภาพฉาย](semantic/semantic-navigation-and-projection.md)

## Runtime และงาน GIS ฉบับรายละเอียด
- [การวาดขอบเขตด้วย Snap Preview และค่าระยะมุม](gis/survey-cad-snap-capture.md)
- [การเลือกวัตถุและแผงคุณสมบัติบนแผนที่มือถือ](gis/mobile-map-selection-ux.md)
- [การอนุมานท้องน้ำจากภาพโดยรักษาหลักฐานสำรวจ](gis/image-bathymetry-evidence.md)
- [สัญญาผลลัพธ์ CAD และ CSV ก่อนส่งออก](gis/cad-csv-preview-contract.md)
- [GEN MAP จากภาพดาวเทียมสู่แผนที่สังเขป](gis/gen-map-semantic-redraw.md)
- [Runtime อิสระ และขอบเขต Model / Tool Gateway](architecture/runtime-model-tool-boundaries.md)
- [Semantic Verification: สัญญาความหมายระหว่างเจตนา แผน และผลจริง](architecture/semantic-verification-contracts.md)
- [Checkpoint และ Provenance: ตรวจเส้นทางงานจากหลักฐาน](architecture/checkpoint-provenance.md)
- [สืบทอดเจตนาและสถานะ: ใช้ของเดิมโดยไม่ให้ของเก่าทับคำแก้ล่าสุด](architecture/intent-inheritance-current-state.md)
- [Experience Memory: จากการทำซ้ำสู่ความรู้ที่ตรวจและใช้ต่อได้](architecture/experience-learning-verification.md)

**ขนาดชุดปัจจุบัน:** 28 ไฟล์ Markdown ได้แก่ สารบัญ 1 ไฟล์ ภาพรวม 11 หัวข้อ และโมดูลรายละเอียด 16 หัวข้อ จำนวนไฟล์เป็นการจัดเอกสาร ไม่ใช่จำนวนองค์ความรู้ทั้งหมดที่มี

## ขอบเขตการรวบรวม
ตรวจบทสนทนาและเอกสารอ้างอิงที่ค้นคืนได้ถึงวันที่รวบรวม รวมทั้งแยกชุดวิธีคิด 18 รูปแบบจาก Matrix ที่ใช้ชื่อคล้ายกัน การค้นคืนไม่ได้ให้ประวัติทั้งหมดเป็นชุดที่ครบถ้วน จึงยังไม่รับรองว่าไม่มีหัวข้ออื่นตกหล่น บางเนื้อหาถูกละไว้ในต้นทาง และไม่มีผลตรวจ Runtime ใหม่ในการรวบรวมนี้

งานอัตลักษณ์พลังงานที่เผยแพร่แล้วให้ใช้ [energy-identity-framework](https://github.com/teeranatb-lab/energy-identity-framework) โดยไม่คัดซ้ำมาเป็นฉบับใหม่ ข้อมูลส่วนตัว ข้อมูลราชการรายกรณี และรายละเอียดที่ไม่อนุญาตให้เผยแพร่ไม่อยู่ในชุดนี้

## การเลือกฉบับใช้งาน
เลือกคำอธิบายล่าสุดที่ตรวจสอบต้นทางได้ในหัวข้อเดียวกัน วันที่ใหม่อย่างเดียวไม่ทำให้ร่างข้อเสนอมีอำนาจแทน Canonical ที่รับรองไว้แล้ว ไม่ลบ Archive ไม่เปลี่ยน Core 0 และไม่รวมแนวคิดต่างชนิดเพียงเพราะใช้ชื่อหรือเลข 18 เหมือนกัน

สถานะข้อเสนอทางสถาปัตยกรรมต้องแยกจากสถานะติดตั้งและผลทดสอบจริง ไม่มีการรัน Runtime หรือสร้างผล PASS ในการรวบรวมครั้งนี้

## สิทธิ์
คงการให้เครดิตผู้ริเริ่มและข้อจำกัดเดิม การจัดชุดเอกสารไม่ได้ให้สิทธิ์เชิงพาณิชย์ การฝึกโมเดล หรือสิทธิ์สร้างงานดัดแปลงเพิ่มเติม ดู [NOTICE ของคลังนี้](../../NOTICE.md) และ [PROVENANCE](../../PROVENANCE.md)

