"""Curated developer regression set; NEVER describe as a blind independent benchmark."""
import json
import argparse
from pathlib import Path
from olgm.thai.nlu import ThaiIntentRouter
from olgm.thai.codegen import SafeCodeGenerator
from olgm.thai.responder import ThaiResponder

CASES=[
 ('สวัสดีค่ะ','greet'),('ขอบคุณมากครับ','thanks'),('ช่วยอธิบายเพิ่มอีกหน่อย','clarify'),
 ('ย่อความเนื้อหานี้','summarize'),('ตรวจคำผิดในประโยค','spellcheck'),
 ('เรียนรู้ภาษาไทยด้วยตัวอย่าง','thai_learn'),('ความหมายของคำว่าธารา','definition'),
 ('คำไวพจน์ของคำนี้','synonyms'),('ทำไมจึงเกิดผลนี้','cause'),
 ('ขอวิเคราะห์ผลกระทบ','effect'),('เปรียบเทียบทางเลือก','compare'),
 ('จำแนกประเภทของวัสดุ','classify'),('ตรวจสอบหลักฐาน','verify'),
 ('ช่วยวางแผนระบบ','plan'),('เพิ่มประสิทธิภาพฐานข้อมูล','optimize'),
 ('คำนวณ 5 บวก 4','calculate'),('หาค่าเฉลี่ย','statistics'),
 ('แปลงหน่วยเมตรเป็นเซนติเมตร','unit_convert'),
 ('เขียนโค้ดภาษา Python','code_write'),('แก้บั๊กในโปรแกรม','code_fix'),
 ('ทดสอบโค้ดด้วย pytest','code_test'),('ออกแบบ API','api_design'),
 ('อธิปไตยทางปัญญา','olgm_sovereign'),('ตรวจสอบแก่นความหมาย','olgm_meaning'),
 ('Core 0 เป็นอะไร','olgm_core0'),('ต้องล็อกเจตนา','olgm_intent_lock'),
 ('ใช้ CANTI ควบคุมคำสั่ง','olgm_canti'),
 ('เหตุผลความจำเป็นจัดซื้อ','procurement_need'),('ทะเบียนครุภัณฑ์','procurement_assets'),
 ('รับเข้าคลังวัสดุ','procurement_inventory'),('ตรวจรับพัสดุ','procurement_inspection'),
 ('น้ำมันเชื้อเพลิง fleet card','procurement_fuel'),
 ('เปลี่ยน CRS เป็น WGS84','gis_crs'),('ส่งออกเป็น DXF','gis_export'),
 ('คำนวณระยะทาง','gis_distance'),('ข้อมูลส่วนบุคคล PDPA','privacy'),
 ('ประเมินความเสี่ยง','risk'),('สร้าง PDF','documents_pdf'),
 ('เฝ้าระวังสถานะระบบ','monitoring'),('วัด latency','performance'),
 ('คลื่นสายรุ้งนอกความรู้','UNKNOWN'),('ห้ามเขียนโค้ด','UNKNOWN'),
]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output');args=p.parse_args()
    router=ThaiIntentRouter()
    details=[]
    for prompt,expected in CASES:
        got=router.detect(prompt)
        top1=got['intent'] or 'UNKNOWN'
        top3=[x['key'] for x in got['candidates'][:3]]
        details.append({'prompt':prompt,'expected':expected,'predicted':top1,
                        'top1_correct':top1==expected,
                        'top3_correct':expected in top3 or expected=='UNKNOWN' and top1=='UNKNOWN'})
    report={'evaluation_type':'CURATED_DEVELOPER_REGRESSION_NOT_BLIND',
           'cases':len(details),'top1_correct':sum(x['top1_correct'] for x in details),
           'top3_correct':sum(x['top3_correct'] for x in details),
           'top1_rate':round(sum(x['top1_correct'] for x in details)/len(details),4),
           'top3_rate':round(sum(x['top3_correct'] for x in details)/len(details),4),
           'details':details,
           'claim':'This metric is only for manually selected phrases, not general Thai understanding.'}
    if args.output:
        o=Path(args.output);o.parent.mkdir(parents=True,exist_ok=True)
        o.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='details'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
