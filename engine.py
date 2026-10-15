"""Configurable local PDF extractor. No pandas/numpy dependency."""
import json, re, io
from pathlib import Path
import fitz

FIELDS=['Declaration_No','Invoice_No','Master_BL','House_BL','Vessel_Name','Import_Date','Loading_Country_Code','Goods_Description','Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM']
SUMMARY={'Total_CIF_USD','Import_Duty_THB','Gross_Weight_KGM'}
NUMERIC=SUMMARY
DEFAULT_RULES={
 'Declaration_No':{'labels':['เลขที่ใบขนฯ','เลขที่ใบขนสินค้า','Declaration No','Declaration Number'],'pattern':r'([A-Z0-9]{9,25})','scope':'first'},
 'Invoice_No':{'labels':['เลขที่บัญชีราคาสินค้า','Invoice No','Invoice Number'],'pattern':r'([A-Z0-9][A-Z0-9/_-]*(?:\s*,\s*[A-Z0-9][A-Z0-9/_-]*)*)','scope':'first'},
 'Master_BL':{'labels':['Master B/L','Master BL','MAWB','เลขที่ใบตราส่งหลัก'],'pattern':r'([A-Z0-9][A-Z0-9/-]{3,})','scope':'first'},
 'House_BL':{'labels':['House B/L','House BL','HAWB','เลขที่ใบตราส่งย่อย'],'pattern':r'([A-Z0-9][A-Z0-9/-]{3,})','scope':'first'},
 'Vessel_Name':{'labels':['ชื่อยานพาหนะ','Vessel Name','Vessel'],'pattern':r'([A-Z][A-Z0-9 ./_-]{2,})','scope':'first'},
 'Import_Date':{'labels':['วันนำเข้า','วันที่นำเข้า','Import Date'],'pattern':r'(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[-/]\d{2}[-/]\d{4})','scope':'first'},
 'Loading_Country_Code':{'labels':['ประเทศต้นทางที่บรรทุก','Country of Loading','Loading Country'],'pattern':r'\b([A-Z]{2})\b','scope':'first'},
 'Goods_Description':{'labels':['รายการสินค้า','คำอธิบายสินค้า','Goods Description','Description of Goods'],'pattern':r'(.{5,180})','scope':'all'},
 'Total_CIF_USD':{'labels':['Total CIF','รวม CIF','CIF USD','รวม'],'pattern':r'([\d,]+\.\d{2})','scope':'last_summary'},
 'Import_Duty_THB':{'labels':['Import Duty','อากรขาเข้า','รวมอากร'],'pattern':r'([\d,]+\.\d{2})','scope':'last_summary'},
 'Gross_Weight_KGM':{'labels':['Gross Weight','GW.','น้ำหนักรวม'],'pattern':r'([\d,]+(?:\.\d+)?)','scope':'last_summary'},
}

def load_profiles(folder):
    profiles=[]
    for p in Path(folder).glob('*.json'):
        try:
            data=json.loads(p.read_text(encoding='utf-8'))
            if data.get('active',True):profiles.append(data)
        except (ValueError,OSError):pass
    return profiles

def page_lines(page):
    out=[]
    for b in page.get_text('dict')['blocks']:
        for line in b.get('lines',[]):
            spans=line.get('spans',[])
            if not spans:continue
            txt=''.join(s['text'] for s in spans).strip()
            if txt:out.append({'text':txt,'rect':fitz.Rect(line['bbox'])})
    return sorted(out,key=lambda a:(round(a['rect'].y0/5),a['rect'].x0))

def detect(pages,profiles):
    joined='\n'.join(p['text'] for p in pages[:2]).lower()
    scored=[]
    for profile in profiles:
        aliases=[x.lower() for x in profile.get('forwarder_aliases',[]) if x.strip()]
        anchors=[x.lower() for x in profile.get('layout_anchors',[]) if x.strip()]
        a=sum(1 for x in aliases if x in joined); b=sum(1 for x in anchors if x in joined)
        if a and (b or not anchors):scored.append((a*3+b,profile))
    scored.sort(key=lambda x:x[0],reverse=True)
    if not scored:return None,'Unknown forwarder/template'
    if len(scored)>1 and scored[0][0]==scored[1][0]:return None,'Ambiguous template match'
    return scored[0][1],''

def candidates_for_field(pages,key,rule):
    scope=rule.get('scope','first')
    indices=range(len(pages)-1,-1,-1) if scope=='last_summary' else range(len(pages))
    results=[]
    for idx in indices:
        page=pages[idx]; lines=page['lines']; txt=page['text']
        if scope=='last_summary' and not any(re.search(x,txt,re.I) for x in rule.get('summary_anchors',['รวม','Total','Summary','GW','CIF'])):continue
        for i,line in enumerate(lines):
            for label in rule.get('labels',[]):
                m=re.search(re.escape(label),line['text'],re.I)
                if not m:continue
                possible=[]
                after=line['text'][m.end():].strip(' :：-\t')
                if after:possible.append((after,line['rect']))
                # Nearby same-row/right and directly below, but never across distant sections.
                for other in lines:
                    if other is line:continue
                    dx=other['rect'].x0-line['rect'].x0; dy=other['rect'].y0-line['rect'].y0
                    if (-3<=dy<=26 and dx>=-10 and (dy>5 or dx>15)):
                        possible.append((other['text'],other['rect']))
                for raw,rect in possible:
                    mm=re.search(rule.get('pattern',r'(.+)'),raw,re.I)
                    if mm:
                        value=mm.group(1).strip().rstrip(' :')
                        if value.lower() in [x.lower() for x in rule.get('labels',[])]:continue
                        results.append({'value':value,'page':idx+1,'rect':list(rect),'label':label,'confidence':'candidate'})
        if scope in ('first','last_summary') and results:break
    return results

def extract(data,filename,profiles):
    doc=fitz.open(stream=data,filetype='pdf')
    pages=[]
    for page in doc:
        lines=page_lines(page)
        pages.append({'text':page.get_text(sort=True),'lines':lines})
    if sum(len(p['text'].strip()) for p in pages)<80:
        raise ValueError('Image-only PDF: text layer missing. OCR engine required; no silent extraction.')
    profile,warning=detect(pages,profiles)
    rules={**DEFAULT_RULES,**(profile.get('rules',{}) if profile else {})}
    result={'Source_File':filename,'Forwarder':profile.get('forwarder','Unknown') if profile else 'Unknown','Template_ID':profile.get('template_id','Generic-Review') if profile else 'Generic-Review','Pages':len(pages),'Review_Status':'Review required'}
    provenance={}; issues=[]
    if warning:issues.append({'Field':'Template','Issue':warning,'Page':''})
    for key in FIELDS:
        options=candidates_for_field(pages,key,rules[key]); provenance[key]=options
        # Do not auto-approve ambiguous extraction. Distinct candidate values require review.
        values=list(dict.fromkeys(x['value'] for x in options))
        if len(values)==1:result[key]=values[0]
        else:
            result[key]=''
            issues.append({'Field':key,'Issue':'No candidate' if not values else 'Conflicting candidates: '+', '.join(values[:5]),'Page':options[0]['page'] if options else ''})
        if key in SUMMARY and options and options[0]['page']!=len(pages):
            issues.append({'Field':key,'Issue':'Summary not found on physical last page; manual confirmation required','Page':options[0]['page']})
            result[key]=''
    return result,provenance,issues
