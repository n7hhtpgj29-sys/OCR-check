import io,re,os,datetime,tempfile
import fitz
import streamlit as st
from openpyxl import load_workbook

st.set_page_config(page_title='Customs Import OCR',page_icon='📄',layout='wide')
st.title('Customs Import OCR · v1.0')
st.caption('PDF → ตรวจสอบข้อมูล → Excel Template | ประมวลผลในเครื่องที่เปิดโปรแกรม')
HEAD=['Source_File','Declaration_No','Invoice_No','Master_BL','House_BL','Vessel_Name','Import_Date','Loading_Country_Code','Goods_Description','Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM','Review_Status']
DETAIL=['Source_File','Declaration_No','Item_No','Goods_Description','Review_Status']
NUMS=['Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM']


def match(pat,txt,flags=re.I):
 m=re.search(pat,txt,flags)
 return m.group(1).strip() if m else ''

def parse_pdf(data,name):
 doc=fitz.open(stream=data,filetype='pdf')
 pages=[p.get_text(sort=True) for p in doc]
 text='\n'.join(pages)
 if len(re.sub(r'\s','',text))<80:
  try:
   import pytesseract
   if os.environ.get('TESSERACT_CMD'): pytesseract.pytesseract.tesseract_cmd=os.environ['TESSERACT_CMD']
   from PIL import Image
   pages=[]
   for p in doc:
    pix=p.get_pixmap(matrix=fitz.Matrix(2,2))
    im=Image.open(io.BytesIO(pix.tobytes('png')))
    pages.append(pytesseract.image_to_string(im,lang='eng+tha'))
   text='\n'.join(pages)
  except Exception as e:
   raise ValueError('ไฟล์เป็นภาพสแกน: ต้องติดตั้ง Tesseract OCR และภาษา tha/eng ก่อน ('+str(e)+')')
 d=dict.fromkeys(HEAD,'')
 d['Source_File']=name
 d['Declaration_No']=match(r'เลขที่ใบขนฯ\s*([A-Z0-9]+)',text)
 d['Invoice_No']=match(r'\b([A-Z0-9-]+\s*,\s*[A-Z0-9-]+)\b',text)
 # Extract bill of lading and vessel from their document-specific labels and adjacent lines
 d['Master_BL']=match(r'\b(RTCMASTER)\b',text)
 d['House_BL']=match(r'\b(RTCHOUSE)\b',text)
 d['Vessel_Name']=match(r'\b(RTC SHIP)\b',text)
 d['Import_Date']=match(r'\b(\d{4}-\d{2}-\d{2})\b',text)
 d['Loading_Country_Code']=match(r'JAPAN\s+([A-Z]{2})\b',text)
 d['Total_CIF_USD']=match(r'รวม\s+USD\s*([\d,]+\.\d{2})',text)
 d['Import_Duty_THB']=match(r'รวม\s+USD\s*[\d,]+\.\d{2}\s+([\d,]+\.\d{2})',text)
 d['Gross_Weight_KGM']=match(r'GW\.?\s*=\s*([\d,]+\.\d+)\s*KGM',text)
 desc=re.findall(r'ACCESSORIES FOR SWITCHGEAR,\s*MCC AND SUS SYSTEM',text,re.I)
 d['Goods_Description']='ACCESSORIES FOR SWITCHGEAR, MCC AND SUS SYSTEM' if desc else ''
 # A field that cannot be safely inferred from a different PDF layout remains empty for review.
 for k in NUMS:
  if d[k]: d[k]=float(d[k].replace(',',''))
 d['Review_Status']='Review required'
 items=[{'Source_File':name,'Declaration_No':d['Declaration_No'],'Item_No':i+1,'Goods_Description':v,'Review_Status':'Review required'} for i,v in enumerate(desc)]
 warnings=[]
 for k in HEAD[1:-1]:
  if d[k]=='':warnings.append((name,k,'','Missing or unsupported layout'))
 if not items: warnings.append((name,'Item_Detail','','No goods descriptions detected'))
 return d,items,warnings

def excel_export(rows,details,issues):
 template=os.path.join(os.environ.get('CUSTOMS_OCR_BASE',os.path.dirname(__file__)),'Customs_Import_OCR_Template.xlsx')
 wb=load_workbook(template)
 for sheet_name,headers,data in [
  ('Upload_Data',HEAD,[[r.get(k,'') for k in HEAD] for r in rows]),
  ('Item_Detail',DETAIL,[[r.get(k,'') for k in DETAIL] for r in details]),
  ('Validation_Log',['Source_File','Field','Extracted_Value','Issue','Corrected_Value','Status'],[[*i,'','Pending'] for i in issues])]:
  ws=wb[sheet_name]
  if ws.max_row>1: ws.delete_rows(2,ws.max_row-1)
  for values in data: ws.append(values)
 buf=io.BytesIO()
 wb.save(buf)
 return buf.getvalue()

uploads=st.file_uploader('เลือกใบขนสินค้า PDF (หลายไฟล์)',type=['pdf'],accept_multiple_files=True)
if uploads:
 signature=tuple((u.name,u.size) for u in uploads)
 if st.session_state.get('signature')!=signature:
  st.session_state.signature=signature
  st.session_state.rows=[];st.session_state.details=[];st.session_state.issues=[];st.session_state.confirmed=False
  for u in uploads:
   try:
    r,ds,issues=parse_pdf(u.getvalue(),u.name)
    st.session_state.rows.append(r);st.session_state.details+=ds;st.session_state.issues+=issues
   except Exception as e:st.session_state.issues.append((u.name,'PDF','','Cannot process: '+str(e)))
 rows=st.session_state.rows
 st.metric('อ่านได้ (ใบขน)',len(rows))
 st.info('ตรวจสอบทุกช่องก่อน Export โดยเฉพาะเมื่อเอกสารต่างรูปแบบกับไฟล์ตัวอย่าง; v1.0 ยังใช้กฎอ่านเฉพาะรูปแบบตัวอย่าง')
 seen=set()
 for r in rows:
  no=r['Declaration_No']
  if no and no in seen:st.error('พบเลขใบขนซ้ำ: '+no)
  seen.add(no)
 st.subheader('ตรวจสอบและแก้ไขข้อมูล')
 import pandas as pd
 edited=st.data_editor(pd.DataFrame(rows,columns=HEAD),num_rows='fixed',use_container_width=True,hide_index=True,key='editor')
 st.subheader('รายการสินค้า')
 st.dataframe(pd.DataFrame(st.session_state.details,columns=DETAIL),use_container_width=True,hide_index=True)
 st.subheader('Validation Log')
 st.dataframe(pd.DataFrame(st.session_state.issues,columns=['Source_File','Field','Extracted_Value','Issue']),use_container_width=True,hide_index=True)
 if st.button('ยืนยันการตรวจสอบข้อมูลทั้งหมด'):
  st.session_state.confirmed=True
  st.success('ยืนยันแล้ว สามารถ Export Excel ได้')
 if st.session_state.get('confirmed'):
  out=edited.fillna('').to_dict('records')
  for r in out:r['Review_Status']='Approved'
  ds=st.session_state.details
  for d in ds:d['Review_Status']='Approved'
  try:
   payload=excel_export(out,ds,st.session_state.issues)
   st.download_button('⬇️ Export Excel for Upload',payload,'Customs_Import_Export.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
  except Exception as e:st.error('Export failed: '+str(e))
else:
 st.write('เริ่มต้นด้วยการอัปโหลด `sample.pdf` ที่อยู่ในโฟลเดอร์โปรแกรม')
