import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    if getattr(sys, "frozen", False):
        # Running from PyInstaller bundle
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))  # ensure correct CWD

    app_path = resolve_path("app.py")

    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]

    sys.exit(stcli.main())
