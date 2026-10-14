import os
import sys
from pathlib import Path

def main():
    base=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    os.environ['CUSTOMS_OCR_BASE']=str(base)
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE']='false'
    os.environ['STREAMLIT_SERVER_HEADLESS']='true'
    app=base/'app.py'
    if not app.exists():
        raise FileNotFoundError(f'Missing app.py: {app}')
    os.chdir(base)
    from streamlit.web import cli as cli
    sys.argv=['streamlit','run',str(app),'--global.developmentMode=false','--server.headless=true','--server.address=127.0.0.1','--server.port=8501','--server.fileWatcherType=none','--browser.gatherUsageStats=false']
    cli.main()

if __name__=='__main__':
    main()
