import os,sys,threading,time,webbrowser
from pathlib import Path

def main():
    os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE']='false'
    os.environ['STREAMLIT_SERVER_HEADLESS']='true'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    base=Path(sys.executable).resolve().parent if getattr(sys,'frozen',False) else Path(__file__).resolve().parent
    app=base/'app.py'
    if not app.exists():raise FileNotFoundError(f'Missing app.py beside EXE: {app}')
    os.chdir(base)
    def browser():
        time.sleep(4);webbrowser.open('http://127.0.0.1:8501')
    threading.Thread(target=browser,daemon=True).start()
    from streamlit.web import cli
    sys.argv=['streamlit','run',str(app),'--global.developmentMode=false','--server.port=8501','--server.address=127.0.0.1','--server.headless=true','--server.fileWatcherType=none']
    cli.main()
if __name__=='__main__':main()
