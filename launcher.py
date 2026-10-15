import os, sys
from pathlib import Path

def main():
    root=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    os.environ['CUSTOMS_OCR_BASE']=str(root)
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE']='false'
    os.environ['STREAMLIT_SERVER_HEADLESS']='true'
    os.environ['STREAMLIT_SERVER_ADDRESS']='127.0.0.1'
    os.environ['STREAMLIT_SERVER_PORT']='8501'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    app=root/'app.py'
    if not app.is_file():raise FileNotFoundError(f'Missing {app}')
    from streamlit.web import cli as stcli
    sys.argv=['streamlit','run',str(app),'--global.developmentMode=false','--server.headless=true','--server.address=127.0.0.1','--server.port=8501']
    stcli.main()
if __name__=='__main__':main()
