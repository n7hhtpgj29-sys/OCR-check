
import os
import sys
from pathlib import Path

def main():
    # Prevent Streamlit from detecting PyInstaller as development mode
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"

    from streamlit.web import cli as stcli

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent

    app_path = base_dir / "app.py"

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
    ]

    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
