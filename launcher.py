import os,sys,threading,time,webbrowser
from pathlib import Path

def main():
    base=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
    app=base/'app.py'
    os.environ['CUSTOMS_OCR_BASE']=str(base)
    tess=Path(sys.executable).parent/'tesseract'/'tesseract.exe'
    if tess.exists():
        os.environ['TESSERACT_CMD']=str(tess)
        os.environ['TESSDATA_PREFIX']=str(tess.parent/'tessdata')
    sys.argv=['streamlit','run',str(app),'--server.address=127.0.0.1','--server.port=8501','--server.headless=true','--browser.gatherUsageStats=false']
    def open_browser():
        time.sleep(3)
        webbrowser.open('http://127.0.0.1:8501')
    threading.Thread(target=open_browser,daemon=True).start()
    from streamlit.web.cli import main as cli_main
    cli_main()
if __name__=='__main__':main()
