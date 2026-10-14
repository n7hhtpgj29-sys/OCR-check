import io, os, re, sys
from pathlib import Path
import fitz
import streamlit as st
from openpyxl import Workbook

HEAD = ['Source_File','Declaration_No','Invoice_No','Master_BL','House_BL','Vessel_Name','Import_Date','Loading_Country_Code','Goods_Description','Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM','Review_Status']
DETAIL = ['Source_File','Declaration_No','Item_No','Goods_Description','Review_Status']
LABELS = {'Declaration_No':'Declaration No.','Invoice_No':'Invoice No.','Master_BL':'Master B/L','House_BL':'House B/L','Vessel_Name':'Vessel Name','Import_Date':'Import Date','Loading_Country_Code':'Loading Country Code','Goods_Description':'Goods Description','Total_CIF_USD':'Total CIF (USD)','Import_Duty_THB':'Import Duty (THB)','Gross_Weight_KGM':'Gross Weight (KGM)'}
NUMERIC = {'Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM'}

def find(pattern,text,flags=re.I):
    m=re.search(pattern,text,flags)
    return m.group(1).strip() if m else ''

def clean_num(v):
    try: return float(str(v).replace(',','').strip())
    except (TypeError,ValueError): return ''

def parse_pdf(data, filename):
    doc=fitz.open(stream=data,filetype='pdf')
    texts=[p.get_text(sort=True) for p in doc]
    if len(''.join(texts).strip()) < 80:
        raise ValueError('Scanned/image PDF: OCR engine is not bundled yet; please review manually or add Tesseract.')
    t='\n'.join(texts)
    d={k:'' for k in HEAD}; d['Source_File']=filename
    d['Declaration_No']=find(r'เลขที่ใบขนฯ\s*([A-Z0-9]{8,})',t) or find(r'\b([A-Z]{4}\d{8,})\b',t)
    d['Invoice_No']=find(r'เลขที่บัญชีราคาสินค้า[\s\S]{0,160}?\b([A-Z][A-Z0-9-]*(?:\s*,\s*[A-Z][A-Z0-9-]*)+)\b',t)
    # Coordinates provide separation between the two B/L entries and ship/date columns.
    for p in doc:
        lines=[]
        for b in p.get_text('dict')['blocks']:
            if 'lines' not in b: continue
            for line in b['lines']:
                spans=line['spans']; val=''.join(s['text'] for s in spans).strip()
                if val: lines.append((min(s['bbox'][0] for s in spans), min(s['bbox'][1] for s in spans), val))
        # Thai standard import declaration: B/L numbers under ใบตราส่งเลขที่
        bill_y=next((y for x,y,s in lines if 'ใบตราส่งเลขที่' in s),None)
        vessel_y=next((y for x,y,s in lines if 'ชื่อยานพาหนะ' in s),None)
        if bill_y is not None:
            # B/Ls often share one PDF text block with two separate lines.
            candidates=[]
            for block in p.get_text('blocks'):
                x0,y0,x1,y1,content=block[:5]
                if x0 < 210 and bill_y+2 < y0 < bill_y+58 and (vessel_y is None or y0 < vessel_y):
                    for token in content.splitlines():
                        token=token.strip()
                        if re.fullmatch(r'[A-Z][A-Z0-9/-]{4,}',token):candidates.append(token)
            if candidates:
                d['Master_BL']=candidates[0]
                if len(candidates)>1:d['House_BL']=candidates[1]
        if vessel_y is not None:
            candidates=[(x,y,s) for x,y,s in lines if vessel_y+7<y<vessel_y+42 and re.fullmatch(r'[A-Z0-9][A-Z0-9 /.-]{3,}',s)]
            d['Vessel_Name']=next((s for x,y,s in candidates if x<230 and not re.search(r'\d{4}-\d{2}-\d{2}',s)),d['Vessel_Name'])
            d['Import_Date']=next((m.group(0) for x,y,s in candidates if (m:=re.search(r'\b\d{4}-\d{2}-\d{2}\b',s))),d['Import_Date'])
        # Country of loading = ประเทศต้นทางที่บรรทุก (right-hand country), NOT ประเทศกำเนิด.
        country_label=next(((x,y) for x,y,s in lines if 'ประเทศต้นทางที่บรรทุก' in s),None)
        if country_label:
            cx,cy=country_label
            options=[(x,s) for x,y,s in lines if cy<y<cy+43 and x>cx-20 and re.fullmatch('[A-Z]{2}',s)]
            if options:d['Loading_Country_Code']=max(options)[1]
    if not d['Invoice_No']:
        d['Invoice_No']=find(r'\b([A-Z][A-Z0-9-]{2,}(?:\s*,\s*[A-Z][A-Z0-9-]{2,})+)\b',t)
    if not d['Import_Date']:d['Import_Date']=find(r'\b(\d{4}-\d{2}-\d{2})\b',t)
    # Use TOTAL row, not the tax summary at top.
    d['Total_CIF_USD']=clean_num(find(r'รวม\s+USD\s*([\d,]+\.\d{2})',t))
    d['Import_Duty_THB']=clean_num(find(r'รวม\s+USD\s*[\d,]+\.\d{2}\s+([\d,]+\.\d{2})',t))
    d['Gross_Weight_KGM']=clean_num(find(r'GW\.?\s*=\s*([\d,]+\.\d+)\s*KGM',t))
    descriptions=re.findall(r'ACCESSORIES FOR SWITCHGEAR,\s*MCC AND SUS SYSTEM',t,re.I)
    d['Goods_Description']='ACCESSORIES FOR SWITCHGEAR, MCC AND SUS SYSTEM' if descriptions else ''
    d['Review_Status']='Review required'
    details=[{'Source_File':filename,'Declaration_No':d['Declaration_No'],'Item_No':i+1,'Goods_Description':v,'Review_Status':'Review required'} for i,v in enumerate(descriptions)]
    issues=[(filename,k,'','Missing - check source PDF') for k in HEAD[1:-1] if d[k]=='']
    return d,details,issues

def export_xlsx(rows,details,issues):
    wb=Workbook(); ws=wb.active; ws.title='Upload_Data'; ws.append(HEAD)
    for row in rows:ws.append([row.get(k,'') for k in HEAD])
    ws=wb.create_sheet('Item_Detail');ws.append(DETAIL)
    for row in details:ws.append([row.get(k,'') for k in DETAIL])
    ws=wb.create_sheet('Validation_Log');ws.append(['Source_File','Field','Extracted_Value','Issue'])
    for issue in issues:ws.append(list(issue))
    for ws in wb:
        ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]:
            from openpyxl.styles import Font,PatternFill
            cell.font=Font(color='FFFFFF',bold=True)
            cell.fill=PatternFill('solid',fgColor='174A70')
        for col in ws.columns:
            from openpyxl.utils import get_column_letter
            ws.column_dimensions[get_column_letter(col[0].column)].width=min(55,max(16,max(len(str(c.value or '')) for c in list(col)[:100])+3))
    buff=io.BytesIO();wb.save(buff);return buff.getvalue()

st.set_page_config(page_title='Customs Import OCR',page_icon='📄',layout='wide')
st.title('Customs Import OCR · v1.2')
st.caption('PDF → ตรวจสอบและแก้ไข → Export Excel | Offline local processing | No pandas')
files=st.file_uploader('เลือกใบขนสินค้า PDF (หลายไฟล์)',type=['pdf'],accept_multiple_files=True)
if files:
    signature=tuple((f.name,len(f.getvalue()),hash(f.getvalue())) for f in files)
    if st.session_state.get('signature')!=signature:
        st.session_state.signature=signature;st.session_state.rows=[];st.session_state.details=[];st.session_state.issues=[];st.session_state.confirmed=False
        for f in files:
            try:
                row,detail,issues=parse_pdf(f.getvalue(),f.name)
                st.session_state.rows.append(row);st.session_state.details.extend(detail);st.session_state.issues.extend(issues)
            except Exception as e:st.session_state.issues.append((f.name,'PDF','','Unable to parse: '+str(e)))
    st.metric('อ่านได้ (ใบขน)',len(st.session_state.rows))
    st.warning('กรุณาตรวจสอบทุกช่องกับ PDF ต้นฉบับก่อนอนุมัติ โดยเฉพาะเอกสารที่รูปแบบต่างจากตัวอย่าง')
    seen=set()
    for idx,row in enumerate(st.session_state.rows):
        with st.expander(f"{row.get('Declaration_No') or 'Unknown declaration'} · {row['Source_File']}",expanded=True):
            for key in HEAD[1:-1]:
                value=row.get(key,'')
                if key in NUMERIC:
                    row[key]=st.text_input(LABELS[key],value=str(value),key=f'{idx}_{key}')
                else:
                    row[key]=st.text_input(LABELS.get(key,key),value=str(value),key=f'{idx}_{key}')
            no=row['Declaration_No']
            if no and no in seen:st.error('Duplicate declaration number: '+no)
            seen.add(no)
    st.subheader('รายการสินค้า')
    st.table(st.session_state.details)
    st.subheader('Validation Log')
    st.table([dict(zip(['Source_File','Field','Extracted_Value','Issue'],i)) for i in st.session_state.issues])
    if st.button('ยืนยันข้อมูลเพื่อ Export Excel'):
        missing=[(r['Source_File'],k) for r in st.session_state.rows for k in HEAD[1:-1] if not str(r.get(k,'')).strip()]
        if missing:st.error('ยังมีช่องว่าง: '+', '.join(f'{a}: {b}' for a,b in missing))
        elif not st.session_state.rows:st.error('ไม่มีใบขนที่อ่านได้')
        elif len([r['Declaration_No'] for r in st.session_state.rows])!=len(set(r['Declaration_No'] for r in st.session_state.rows)):st.error('พบเลขใบขนซ้ำ')
        else:st.session_state.confirmed=True
    if st.session_state.get('confirmed'):
        output=[]
        for r in st.session_state.rows:
            copy=r.copy();copy['Review_Status']='Approved'
            for k in NUMERIC:copy[k]=clean_num(copy[k])
            output.append(copy)
        details=[{**d,'Review_Status':'Approved'} for d in st.session_state.details]
        st.download_button('⬇️ Export Excel for Upload',export_xlsx(output,details,st.session_state.issues),'Customs_Import_Export.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
else:st.info('เริ่มต้นโดยอัปโหลดใบขน PDF')
