import os
import sys
import streamlit as st                      # important
import streamlit.web.cli as stcli

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))

    app_path = resolve_path("app.py")
    sys.argv = ["streamlit", "run", app_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())
