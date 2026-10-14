
import os
import sys
import time
import threading
import webbrowser
from pathlib import Path


def main():
    # Force Streamlit production mode before importing it
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent

    app_path = base_dir / "app.py"

    if not app_path.exists():
        print(f"ERROR: app.py not found: {app_path}")
        input("Press Enter to exit...")
        return

    os.chdir(base_dir)

    # Open browser after server starts
    def open_browser():
        time.sleep(4)
        webbrowser.open("http://127.0.0.1:8501")

    threading.Thread(
        target=open_browser,
        daemon=True
    ).start()

    # Import after environment variables are configured
    from streamlit.web import cli as stcli

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--server.port=8501",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]

    try:
        sys.exit(stcli.main())
    except Exception:
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
