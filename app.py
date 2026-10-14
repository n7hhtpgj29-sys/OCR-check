import io
import os
import re
import hashlib
from pathlib import Path

import fitz
import streamlit as st
from openpyxl import load_workbook

HEAD = ['Source_File','Declaration_No','Invoice_No','Master_BL','House_BL','Vessel_Name','Import_Date','Loading_Country_Code','Goods_Description','Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM','Review_Status']
DETAIL = ['Source_File','Declaration_No','Item_No','Goods_Description','Review_Status']
NUMS = {'Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM'}
LABELS = {'Source_File':'Source PDF','Declaration_No':'Declaration No.','Invoice_No':'Invoice No.','Master_BL':'Master B/L','House_BL':'House B/L','Vessel_Name':'Vessel Name','Import_Date':'Import Date','Loading_Country_Code':'Loading Country Code','Goods_Description':'Goods Description','Total_CIF_USD':'Total CIF (USD)','Import_Duty_THB':'Import Duty (THB)','Gross_Weight_KGM':'Gross Weight (KGM)'}

def match(pattern, text, flags=re.I):
    m = re.search(pattern, text, flags)
    return m.group(1).strip() if m else ''

def extract_lines(page):
    return [line.strip() for line in page.get_text(sort=True).splitlines() if line.strip()]

def parse_pdf(data, name):
    with fitz.open(stream=data, filetype='pdf') as doc:
        lines = [line for page in doc for line in extract_lines(page)]
        text = '\n'.join(lines)
        if len(re.sub(r'\s','',text)) < 80:
            try:
                import pytesseract
                from PIL import Image
                if os.environ.get('TESSERACT_CMD'):
                    pytesseract.pytesseract.tesseract_cmd = os.environ['TESSERACT_CMD']
                lines=[]
                for page in doc:
                    pix=page.get_pixmap(matrix=fitz.Matrix(2,2))
                    img=Image.open(io.BytesIO(pix.tobytes('png')))
                    lines.extend([x.strip() for x in pytesseract.image_to_string(img,lang='eng+tha').splitlines() if x.strip()])
                text='\n'.join(lines)
            except Exception as exc:
                raise ValueError('PDF เป็นภาพสแกน และ OCR Engine ยังไม่พร้อม: '+str(exc)) from exc
    row = {key:'' for key in HEAD}
    row['Source_File'] = name
    row['Declaration_No'] = match(r'เลขที่ใบขนฯ\s*([A-Z0-9]+)',text)
    row['Invoice_No'] = match(r'\b([A-Z0-9-]+\s*,\s*[A-Z0-9-]+)\b',text)
    row['Import_Date'] = match(r'\b(\d{4}-\d{2}-\d{2})\b',text)
    row['Loading_Country_Code'] = match(r'ประเทศต้นทางที่บรรทุก[\s\S]{0,100}?\b([A-Z]{2})\b',text)
    if not row['Loading_Country_Code']:
        row['Loading_Country_Code'] = match(r'\bJAPAN\s+(JP)\b',text)
    row['Total_CIF_USD'] = match(r'รวม\s+USD\s*([\d,]+\.\d{2})',text)
    row['Import_Duty_THB'] = match(r'รวม\s+USD\s*[\d,]+\.\d{2}\s+([\d,]+\.\d{2})',text)
    row['Gross_Weight_KGM'] = match(r'GW\.?\s*=\s*([\d,]+(?:\.\d+)?)\s*KGM',text)
    # Labels in sample are often positioned separately from values. Avoid inventing values.
    bl_index = next((i for i,s in enumerate(lines) if 'ใบตราส่งเลขที่' in s),-1)
    if bl_index >= 0:
        candidates = [x for x in lines[bl_index+1:bl_index+8] if re.fullmatch(r'[A-Z0-9][A-Z0-9/\-]{3,}',x)]
        if candidates: row['Master_BL'] = candidates[0]
        if len(candidates)>1: row['House_BL'] = candidates[1]
    vessel_index = next((i for i,s in enumerate(lines) if 'ชื่อยานพาหนะ' in s),-1)
    if vessel_index >= 0:
        candidates = [x for x in lines[vessel_index+1:vessel_index+7] if re.fullmatch(r'[A-Z][A-Z0-9 /\-]{3,}',x) and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',x)]
        if candidates: row['Vessel_Name'] = candidates[0]
    descriptions = re.findall(r'ACCESSORIES FOR SWITCHGEAR,\s*MCC AND SUS SYSTEM',text,re.I)
    # Example-layout fallback only; unknown descriptions must be reviewed manually.
    row['Goods_Description'] = descriptions[0].strip() if descriptions else ''
    for key in NUMS:
        if row[key]:
            try: row[key] = float(row[key].replace(',',''))
            except ValueError: row[key] = ''
    row['Review_Status']='Review required'
    items = [dict(Source_File=name,Declaration_No=row['Declaration_No'],Item_No=i+1,Goods_Description=s.strip(),Review_Status='Review required') for i,s in enumerate(descriptions)]
    issues = [(name,k,'','Missing / review required') for k in HEAD[1:-1] if row[k] == '']
    if not items: issues.append((name,'Item_Detail','','No items automatically identified'))
    return row,items,issues

def export_excel(rows,details,issues):
    base=Path(os.environ.get('CUSTOMS_OCR_BASE',Path(__file__).resolve().parent))
    template=base/'Customs_Import_OCR_Template.xlsx'
    if not template.exists():
        raise FileNotFoundError('Excel Template not found: '+str(template))
    wb=load_workbook(template)
    sets=[('Upload_Data',HEAD,rows),('Item_Detail',DETAIL,details)]
    for sheet,headers,records in sets:
        ws=wb[sheet]
        if ws.max_row>1: ws.delete_rows(2,ws.max_row-1)
        for record in records: ws.append([record.get(h,'') for h in headers])
    ws=wb['Validation_Log']
    if ws.max_row>1: ws.delete_rows(2,ws.max_row-1)
    for issue in issues: ws.append([*issue,'','Pending'])
    output=io.BytesIO(); wb.save(output)
    return output.getvalue()

st.set_page_config(page_title='Customs Import OCR',page_icon='📄',layout='wide')
st.title('Customs Import OCR · v1.1')
st.caption('PDF → ตรวจสอบข้อมูล → Excel | Offline · No pandas')
files=st.file_uploader('เลือกใบขนสินค้า PDF (หลายไฟล์)',type=['pdf'],accept_multiple_files=True)
if files:
    signature=tuple((f.name,len(f.getvalue()),hashlib.sha256(f.getvalue()).hexdigest()) for f in files)
    if st.session_state.get('signature') != signature:
        st.session_state['signature']=signature
        st.session_state['rows']=[]
        st.session_state['details']=[]
        st.session_state['issues']=[]
        st.session_state['confirmed']=False
        for f in files:
            try:
                row,details,issues=parse_pdf(f.getvalue(),f.name)
                st.session_state['rows'].append(row)
                st.session_state['details'].extend(details)
                st.session_state['issues'].extend(issues)
            except Exception as exc:
                st.session_state['issues'].append((f.name,'PDF','','Cannot process: '+str(exc)))
    rows=st.session_state['rows']
    st.metric('อ่านได้ (ใบขน)',len(rows))
    st.warning('ต้องตรวจสอบข้อมูลก่อน Export: ตัวอ่านอัตโนมัติรองรับโครงสร้างใบขนตัวอย่างเป็นหลัก')
    with st.form('review_form'):
        updated=[]
        for i,row in enumerate(rows):
            with st.expander(f"ใบขน {i+1}: {row.get('Declaration_No') or row['Source_File']}",expanded=True):
                values={}
                for key in HEAD[:-1]:
                    value=row.get(key,'')
                    values[key]=st.text_input(LABELS.get(key,key),value=str(value),key=f'{i}_{key}')
                values['Review_Status']='Approved'
                updated.append(values)
        submitted=st.form_submit_button('ยืนยันข้อมูลที่ตรวจสอบแล้ว')
    if submitted:
        st.session_state['edited_rows']=updated
        st.session_state['confirmed']=True
    st.subheader('รายการสินค้า (ตรวจสอบและแก้ไข)')
    revised=[]
    for j,item in enumerate(st.session_state['details']):
        with st.expander(f"Item {item['Item_No']} · {item['Source_File']}"):
            desc=st.text_input('Goods Description',value=item['Goods_Description'],key=f'detail_{j}')
            revised.append({**item,'Goods_Description':desc,'Review_Status':'Approved'})
    st.subheader('Validation Log')
    for filename,field,_,reason in st.session_state['issues']:
        st.caption(f'{filename} · {field}: {reason}')
    if st.session_state.get('confirmed'):
        approved=st.session_state['edited_rows']
        seen=set(); errors=[]
        for row in approved:
            declaration=row.get('Declaration_No','').strip()
            if not declaration: errors.append(f"{row['Source_File']}: Declaration No. is missing")
            elif declaration in seen: errors.append(f'Duplicate Declaration No.: {declaration}')
            seen.add(declaration)
            for field in NUMS:
                raw=row.get(field,'').replace(',','').strip()
                try: row[field]=float(raw) if raw else ''
                except ValueError: errors.append(f"{row['Source_File']}: Invalid number in {field}")
        if errors:
            for error in errors: st.error(error)
        else:
            st.success('ยืนยันแล้ว ตรวจสอบความถูกต้องอีกครั้งก่อน Upload เข้า System')
            try:
                output=export_excel(approved,revised,st.session_state['issues'])
                st.download_button('⬇️ Export Excel',output,'Customs_Import_Export.xlsx',mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            except Exception as exc:
                st.error('Export failed: '+str(exc))
else:
    st.info('เริ่มต้นด้วยการอัปโหลด PDF ตัวอย่าง')
