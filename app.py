import streamlit as st
import os
import glob
import subprocess
import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog
import shutil
import re
import sys
import importlib.metadata
import time
from execution_manager import ExecutionManager

# --- 1. App Configuration ---
st.set_page_config(page_title="Behave Runner", layout="wide")

# Initialize Session State
if "features_data" not in st.session_state: st.session_state.features_data = []
if "caps_files" not in st.session_state: st.session_state.caps_files = []
if "unique_tags" not in st.session_state: st.session_state.unique_tags = []
if "scan_done" not in st.session_state: st.session_state.scan_done = False
if "proj_path" not in st.session_state: st.session_state.proj_path = os.getcwd()

# Get the Singleton Manager
exec_manager = ExecutionManager()

# --- 2. Helper Functions ---
def get_allure_path():
    allure_path = shutil.which("allure")
    if allure_path: return allure_path
    user_home = os.path.expanduser("~")
    scoop_path = os.path.join(user_home, "scoop", "apps", "allure", "current", "bin", "allure.cmd")
    if os.path.exists(scoop_path): return scoop_path
    return None

def select_folder():
    try:
        root = tk.Tk(); root.withdraw(); root.wm_attributes('-topmost', 1); 
        p = filedialog.askdirectory(master=root); root.destroy(); return p
    except: return None

def parse_feature_file(file_path):
    feature_name = os.path.basename(file_path)
    scenarios = []; tags = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s.startswith("@"):
                    for t in s.split(): 
                        if t.startswith("@"): tags.add(t)
                if s.startswith("Feature:"): feature_name = s.replace("Feature:", "").strip()
                elif s.startswith("Scenario:") or s.startswith("Scenario Outline:"): scenarios.append(s.split(":", 1)[1].strip())
    except: pass
    return {"feature_name": feature_name, "scenarios": scenarios, "tags": sorted(list(tags)), "path": file_path, "filename": os.path.basename(file_path)}

def scan_project(project_path):
    if not os.path.isdir(project_path): return None, None, None
    f_path = os.path.join(project_path, "features", "**", "*.feature")
    files = glob.glob(f_path, recursive=True)
    parsed = []; all_tags = set()
    for f in files:
        d = parse_feature_file(f); parsed.append(d); all_tags.update(d['tags'])
    c_path = os.path.join(project_path, "**", "*caps*.json")
    caps = [os.path.basename(c) for c in glob.glob(c_path, recursive=True)]
    return parsed, caps, sorted(list(all_tags))

def scan_steps(project_path):
    """
    Scans the 'steps' directory for Python files and extracts Gherkin step definitions.
    Returns a dict: { 'filename': [list of step strings] }
    """
    steps_path = os.path.join(project_path, "features", "steps", "*.py")
    # Behave often puts steps in features/steps, but let's check recursively just in case
    # or just root 'steps' depending on structure. Let's assume features/steps as per standard Behave
    # If not found there, try project_root/steps
    files = glob.glob(steps_path)
    if not files:
         # Try project root steps
         files = glob.glob(os.path.join(project_path, "steps", "*.py"))

    steps_data = {}
    
    # Regex to capture @given('text'), @when("text"), etc.
    # Matches: @given, @when, @then, @step
    # Capture group 2 is the step text inside quotes
    # Handles both ' and "
    step_pattern = re.compile(r"^\s*@(given|when|then|step)\s*\(\s*['\"](.*)['\"]\s*\)")

    for f_path in files:
        filename = os.path.basename(f_path)
        found_steps = []
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = step_pattern.search(line)
                    if match:
                        keyword = match.group(1).title() # Given, When...
                        text = match.group(2)
                        found_steps.append(f"**{keyword}** {text}")
        except Exception as e:
            print(f"Error parsing {f_path}: {e}")
            
        if found_steps:
            steps_data[filename] = found_steps
            
    return steps_data

def parse_allure_results(results_dir):
    if not os.path.exists(results_dir): return None
    total=passed=failed=broken=skipped=0
    for jf in glob.glob(os.path.join(results_dir, "*-result.json")):
        try:
            with open(jf,'r') as f:
                d=json.load(f); s=d.get('status')
                total+=1
                if s=='passed': passed+=1
                elif s=='failed': failed+=1
                elif s=='broken': broken+=1
                elif s=='skipped': skipped+=1
        except: continue
    return {"Total": total, "Passed": passed, "Failed": failed, "Broken": broken, "Skipped": skipped}

def get_installed_version(pkg):
    try: return importlib.metadata.version(pkg)
    except: return None

def install_package(pkg, output_container=None):
    """
    Installs a package and streams output to a Streamlit container if provided.
    """
    try:
        # We use a Popen process to capture stdout line by line
        process = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", pkg],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        full_output = ""
        for line in process.stdout:
            full_output += line
            if output_container:
                output_container.code(full_output, language="bash")
        
        process.wait()
        
        if process.returncode == 0:
            return True, "Installed successfully"
        else:
            return False, f"Return Code {process.returncode}"
            
    except Exception as e:
        return False, str(e)

# --- 3. Persistent Footer Logic ---
def render_footer():
    new_logs = exec_manager.get_new_logs()
    with st.container():
        st.markdown("""<style>.terminal-footer {position: fixed;bottom: 0;left: 0;width: 100%;background-color: #0e1117;border-top: 1px solid #303030;z-index: 999;padding: 10px;max-height: 300px;overflow-y: auto;}</style>""", unsafe_allow_html=True)
        if exec_manager.full_logs:
            state_icon = "🟢 Running..." if exec_manager.is_running else "🔴 Stopped"
            with st.expander(f"📟 Terminal Output ({state_icon})", expanded=False):
                st.code(exec_manager.full_logs, language="bash")
                if exec_manager.is_running:
                    time.sleep(1); st.rerun()

# --- 4. Page Definitions ---
def page_execution_run():
    st.header("🚀 Execution Run")
    st.subheader("1. Project Location")
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        if st.button("📂 Select"):
            s = select_folder()
            if s: st.session_state.proj_path = s; st.rerun()
    with col2:
        project_path_input = st.text_input("Path", value=st.session_state.proj_path, label_visibility="collapsed")
    with col3:
        if st.button("Scan"):
            d, c, t = scan_project(project_path_input)
            if d:
                st.session_state.features_data = d
                st.session_state.caps_files = c
                st.session_state.unique_tags = t
                st.session_state.scan_done = True
                st.success(f"Found {len(d)} Features")

    if st.session_state.scan_done:
        st.divider()
        st.subheader("2. Configuration")
        selected_caps = None
        if st.session_state.caps_files:
            st.write("**Select Capabilities (Mandatory):**")
            selected_caps = st.radio("Caps File", st.session_state.caps_files, horizontal=True)
        else:
            st.error("No caps files found.")

        st.divider()
        st.subheader("3. Select Scope")
        selected_tags = st.multiselect("Filter Tags", st.session_state.unique_tags)
        st.write("--- OR Select Features ---")
        selected_feature_paths = []
        with st.container(border=True):
            for feat in st.session_state.features_data:
                chk_key = f"chk_{feat['filename']}"
                path_rel = os.path.relpath(feat['path'], project_path_input)
                label = f"**{feat['feature_name']}**"
                col_chk, col_exp = st.columns([0.8, 0.2])
                with col_chk:
                    if st.checkbox(label, key=chk_key, help=path_rel): selected_feature_paths.append(path_rel)
                with col_exp: # Read-only Scenario List
                    with st.popover("Scenarios"):
                         if feat['scenarios']: 
                            for s in feat['scenarios']: st.markdown(f"- {s}")
                         else: st.write("No scenarios.")

        st.divider()
        st.subheader("4. Execution")
        if st.button("▶ Run Tests", type="primary"):
            if not selected_caps: st.error("Select Caps file.")
            elif not selected_feature_paths and not selected_tags: st.warning("Select features or tags.")
            else:
                tags_arg = f"--tags={','.join(selected_tags)} " if selected_tags else ""
                features_arg = " ".join(f"\"{p}\"" for p in selected_feature_paths) if selected_feature_paths else ""
                cmd = f"behave --no-logcapture -D property_file=configs/config.properties -D endpoint_file=endpoints.json -D caps_file={selected_caps} {tags_arg}--no-capture --no-capture-stderr --no-color -f allure_behave.formatter:AllureFormatter -o allure-results {features_arg}"
                if exec_manager.start_execution(cmd, project_path_input, os.environ.copy()):
                    st.toast("Started!", icon="🚀"); st.rerun()
                else: st.warning("Busy.")

def page_steps_viewer():
    st.header("👣 Step Definitions Viewer")
    project_path = st.session_state.get("proj_path", os.getcwd())
    
    # 1. Scan for Steps
    steps_data = scan_steps(project_path)
    
    if not steps_data:
        st.warning(f"No step definition files found in `{os.path.join(project_path, 'features', 'steps')}` or `{os.path.join(project_path, 'steps')}`.")
        return

    st.success(f"Found {len(steps_data)} Step Definition Files.")
    st.divider()

    # 2. Display Collapsible Lists
    for filename, steps in steps_data.items():
        with st.expander(f"📄 {filename} ({len(steps)} steps)"):
            for step in steps:
                st.markdown(f"- {step}")

def page_requirements():
    st.header("📦 Requirements")
    project_path = st.session_state.get("proj_path", os.getcwd())
    req_file = os.path.join(project_path, "requirements.txt")
    
    st.subheader("System Tools")
    allure_path = get_allure_path()
    if allure_path: 
        st.success(f"Allure: `{allure_path}`")
    else: 
        st.error("Allure Not Found")

    st.subheader("Python Dependencies")
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # Extract package name for version check
            pkg = re.split(r'[=<>!]', line)[0].strip()
            ver = get_installed_version(pkg)
            
            # Layout: Requirement | Status | Install Button
            c1, c2, c3 = st.columns([3, 2, 2])
            
            with c1: 
                st.code(line, language="text")
            with c2: 
                if ver:
                    st.success(f"Installed: {ver}")
                else:
                    st.warning("Missing")
            with c3:
                if not ver:
                    if st.button("Install", key=f"install_{pkg}"):
                        # Use st.status to show a spinner and expandable logs
                        with st.status(f"Installing {pkg}...", expanded=True) as status:
                            st.write("Running pip install...")
                            # Create an empty placeholder for streaming logs
                            log_box = st.empty()
                            
                            ok, msg = install_package(line, output_container=log_box)
                            
                            if ok:
                                status.update(label=f"✅ {pkg} Installed!", state="complete", expanded=False)
                                time.sleep(1) # Brief pause to see success
                                st.rerun()
                            else:
                                status.update(label=f"❌ Failed to install {pkg}", state="error", expanded=True)
                                st.error(msg)
    else: 
        st.warning("No requirements.txt found.")

def page_allure_results():
    st.header("📊 Allure Results")
    project_path = st.session_state.get("proj_path", os.getcwd())
    allure_dir = os.path.join(project_path, "allure-results")
    allure_cmd = get_allure_path()

    if not allure_cmd:
        st.error("⚠️ 'allure' executable not found in PATH.")
    
    if os.path.exists(allure_dir):
        stats = parse_allure_results(allure_dir)
        if stats and stats['Total'] > 0:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", stats['Total'])
            m2.metric("Passed", stats['Passed'])
            m3.metric("Failed", stats['Failed'])
            m4.metric("Other", stats['Broken'] + stats['Skipped'])
            st.divider()
            if st.button("🌐 Open Report"):
                if allure_cmd:
                    subprocess.Popen([allure_cmd, "serve", allure_dir], cwd=project_path, env=os.environ.copy())
                    st.toast("Report opening...", icon="🚀")
                else:
                    st.error("Allure command not found.")
            
            results_list = []
            for jf in glob.glob(os.path.join(allure_dir, "*-result.json")):
                try:
                    with open(jf, 'r') as f:
                        d = json.load(f)
                        results_list.append({"Test": d.get("name"), "Status": d.get("status")})
                except: pass
            if results_list:
                st.dataframe(pd.DataFrame(results_list), use_container_width=True)
        else:
            st.warning("No results found.")
    else:
        st.error(f"Directory not found: {allure_dir}")

# --- 5. Navigation & Footer ---

# 1. Setup Navigation
pg = st.navigation({
    "Test Automation": [
        st.Page(page_execution_run, title="Test Execution", icon="🚀"),
        st.Page(page_steps_viewer, title="Step Definitions", icon="👣"),
        st.Page(page_requirements, title="Verify Requirements", icon="📦"),
        st.Page(page_allure_results, title="View Allure Results", icon="📊"),
    ]
})

# 2. Add Persistent Sidebar Title/Logo
st.sidebar.title("🦄 Behave Runner")
st.sidebar.markdown("---") # Visual separator

# 3. Run the selected page
pg.run()

# 4. Render Footer (Always last)
render_footer()

