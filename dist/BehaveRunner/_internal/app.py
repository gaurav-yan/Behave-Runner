import streamlit as st
import os
import glob
import subprocess
import json
import pandas as pd
# tkinter imports moved to local scope for optimization
import shutil
import re
import sys
import importlib.metadata
import time
from execution_manager import ExecutionManager

# --- 1. App Configuration ---
st.set_page_config(page_title="Behave Runner", layout="wide")

# Inject PWA Code
try:
    from pwa_injector import inject_pwa
    inject_pwa()
except ImportError:
    pass

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
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.wm_attributes('-topmost', 1); 
        p = filedialog.askdirectory(master=root); root.destroy(); return p
    except Exception as e:
        print(f"Tkinter error: {e}")
        return None

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
    files = glob.glob(steps_path)
    if not files:
         files = glob.glob(os.path.join(project_path, "steps", "*.py"))

    steps_data = {}
    step_pattern = re.compile(r"^\s*@(given|when|then|step)\s*\(\s*['\"](.*)['\"]\s*\)")

    for f_path in files:
        filename = os.path.basename(f_path)
        found_steps = []
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                for line in f:
                    match = step_pattern.search(line)
                    if match:
                        keyword = match.group(1).title() 
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
    
# Required environment variables for this project
REQUIRED_ENV_VARS = [
    "LAMBDA_USER_NAME",
    "LAMBDA_APIKEY",
    "ENCRYPT_KEY",
    "ESAM_QA_APIKEY",
]

def load_env_file(env_path):
    """Return (env_dict, invalid_lines). Values are raw; caller decides masking."""
    env_vars = {}
    invalid_lines = []
    if not os.path.exists(env_path):
        return env_vars, invalid_lines

    with open(env_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip()
            else:
                invalid_lines.append(f"Line {line_num}: {line}")
    return env_vars, invalid_lines

def save_env_file(env_path, env_dict):
    """Write env_dict to .env in KEY=VALUE format."""
    lines = [f"{k}={v}" for k, v in env_dict.items()]
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")



# --- 3. Persistent Footer Logic ---
def render_footer():
    """Renders the persistent terminal footer with auto-scroll and fixed height."""
    new_logs = exec_manager.get_new_logs()
    
    with st.container():
        st.markdown("""
            <style>
            .terminal-footer {
                position: fixed; bottom: 0; left: 0; width: 100%;
                background-color: #0e1117; border-top: 1px solid #303030;
                z-index: 9999; padding: 10px;
            }
            .terminal-footer div[data-testid="stExpander"] div[data-testid="stCodeBlock"] pre {
                max-height: 250px !important; overflow-y: auto !important;
                white-space: pre-wrap !important; display: flex; flex-direction: column-reverse;
            }
            </style>
            """, unsafe_allow_html=True)

        if exec_manager.full_logs:
            state_icon = "🟢 Running..." if exec_manager.is_running else "🔴 Stopped"
            st.markdown('<div class="terminal-footer">', unsafe_allow_html=True)
            with st.expander(f"📟 Terminal Output ({state_icon})", expanded=True):
                st.code(exec_manager.full_logs, language="bash", height=300)
                st.markdown("""
                    <script>
                        const codeBlocks = window.parent.document.querySelectorAll('.terminal-footer div[data-testid="stCodeBlock"] pre');
                        if (codeBlocks.length > 0) {
                             const terminal = codeBlocks[codeBlocks.length - 1];
                             terminal.scrollBottom = terminal.scrollHeight;
                        }
                    </script>
                    """, unsafe_allow_html=True)
                if exec_manager.is_running:
                    time.sleep(1); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

def reset_execution_filters():
    """Callback to reset all filters in the Execution Run page."""
    # 1. Reset the search box
    st.session_state.feature_search = ""
    
    # 2. Reset the tag multiselect
    st.session_state.selected_tags = []
    
    # 3. Uncheck all feature checkboxes
    # We look for all keys starting with 'chk_' and set them to False
    for key in st.session_state.keys():
        if key.startswith("chk_"):
            st.session_state[key] = False

# --- 4. Page Definitions ---
def page_execution_run():
    st.header("🚀 Execution Run")
    st.subheader("1. Project Location")
    col1, col2, col3, col4 = st.columns([1, 4, 1, 1])
    with col1:
        if st.button("Select", icon="📂"):
            s = select_folder()
            if s: st.session_state.proj_path = s; st.rerun()
    with col2:
        project_path_input = st.text_input("Path", value=st.session_state.proj_path, label_visibility="collapsed")
    with col3:
        if st.button("Scan", icon="🔍"):
            d, c, t = scan_project(project_path_input)
            if d:
                st.session_state.features_data = d
                st.session_state.caps_files = c
                st.session_state.unique_tags = t
                st.session_state.scan_done = True
                st.toast("Scan Complete", icon="✅")
                with st.spinner("Scanning..."):
                    time.sleep(1)
                st.success("Scan Complete!")
                st.rerun()
        with col4:
                st.text(f"Features Found \n {len(st.session_state.features_data)}", text_alignment="center")

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
        col_scope_title, col_reset = st.columns([4, 1])
        with col_reset:
            st.button("🔄 Reset Scope", on_click=reset_execution_filters, use_container_width=True)

        # 1. Tags Multiselect (with Key)
        selected_tags = st.multiselect(
            "Filter by Tags:", 
            options=st.session_state.unique_tags,
            key="selected_tags" # <--- Added key for reset
        )
        
        st.write("--- OR Select Features ---")

        # 2. Search Input (with Key)
        search_query = st.text_input(
            "🔍 Search Features", 
            key="feature_search", # <--- Added key for reset
            placeholder="Search by name, filename, or tag..."
        ).lower()
        
        # Filter logic (same as before)
        filtered_features = []
        if search_query:
            for feat in st.session_state.features_data:
                in_name = search_query in feat['feature_name'].lower()
                in_file = search_query in feat['filename'].lower()
                in_tags = any(search_query in t.lower() for t in feat['tags'])
                if in_name or in_file or in_tags:
                    filtered_features.append(feat)
        else:
            filtered_features = st.session_state.features_data

        # 3. Feature Selection List
        selected_feature_paths = []
        with st.container(height=400):
            if not filtered_features:
                st.info("No features match your search.")
            
            for feat in filtered_features:
                # IMPORTANT: Use 'chk_' prefix as expected by the reset callback
                chk_key = f"chk_{feat['filename']}"
                path_rel = os.path.relpath(feat['path'], project_path_input)
                label = f"**{feat['feature_name']}**"
                
                col_chk, col_exp = st.columns([0.8, 0.2], gap=None, vertical_alignment='center')
                with col_chk:
                    # Checkbox now uses the persistent chk_key
                    if st.checkbox(label, key=chk_key, help=path_rel): 
                        selected_feature_paths.append(path_rel)
                with col_exp:
                    with st.popover("Scenarios"):
                         if feat['scenarios']: 
                            for s in feat['scenarios']: st.markdown(f"- {s}")
                st.divider()

        st.divider()
        st.subheader("4. Execution")
        
        # --- Run / Stop Logic ---
        if exec_manager.is_running:
            if st.button("⏹️ Stop Execution", type="primary"):
                if exec_manager.stop_execution():
                    st.warning("Stopped by user.")
                    time.sleep(1); st.rerun()
                else: st.error("Stop failed.")
        else:
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
    steps_data = scan_steps(project_path)
    if not steps_data:
        st.warning("No step files found.")
        return
    st.success(f"Found {len(steps_data)} Step Files.")
    st.divider()
    for filename, steps in steps_data.items():
        with st.expander(f"📄 {filename} ({len(steps)} steps)"):
            for step in steps: st.markdown(f"- {step}")

def page_requirements():
    st.header("📦 Requirements Verification")
    project_path = st.session_state.get("proj_path", os.getcwd())
    req_file = os.path.join(project_path, "requirements.txt")
    env_file = os.path.join(project_path, ".env")

    # --- 1. System Tools ---
    st.subheader("1. System Tools")
    allure_path = get_allure_path()
    if allure_path:
        st.success(f"Allure: `{allure_path}`")
    else:
        st.error("Allure Not Found")

    st.divider()

    # --- 2. .env Verification ---
    st.subheader("2. Environment Variables (.env)")
    env_vars, invalid_lines = load_env_file(env_file)
    missing_required = [k for k in REQUIRED_ENV_VARS if not env_vars.get(k)]

    if os.path.exists(env_file):
        if not missing_required and not invalid_lines:
            st.success(f"`.env` found at `{env_file}` and all required variables are set.")
        else:
            st.warning(f"`.env` found at `{env_file}` but some required variables are missing or invalid lines exist.")
    else:
        st.error("`.env` file not found in project root.")

    # Show current variables (masked)
    if env_vars:
        with st.expander("Current .env variables (values masked)"):
            for key, val in env_vars.items():
                masked = ("*" * len(val)) if len(val) <= 4 else (val[:2] + "*" * (len(val) - 2))
                st.code(f"{key}={masked}", language="bash")
    else:
        st.info("No variables loaded. Use the editor below to create `.env`.")

    if invalid_lines:
        with st.expander("⚠ Invalid lines in .env"):
            for l in invalid_lines:
                st.warning(l)

    # --- 2.1 .env Editor "Popup" ---
    if "show_env_editor" not in st.session_state:
        st.session_state.show_env_editor = False

    if st.button("➕ Create / Update .env"):
        st.session_state.show_env_editor = True

    if st.session_state.show_env_editor:
        st.markdown("### Edit .env variables")
        st.info("Required: LAMBDA_USER_NAME, LAMBDA_APIKEY, ENCRYPT_KEY, ESAM_QA_APIKEY")

        updated_env = dict(env_vars)

        # Required variables
        for key in REQUIRED_ENV_VARS:
            current_val = updated_env.get(key, "")
            updated_env[key] = st.text_input(
                key,
                value=current_val,
                type="password" if "KEY" in key or "API" in key else "default"
            )

        st.markdown("---")
        st.write("Optional custom variables (key=value, one per line):")

        # Build current custom vars text
        custom_pairs = [f"{k}={v}" for k, v in updated_env.items() if k not in REQUIRED_ENV_VARS]
        custom_text_default = "\n".join(custom_pairs)
        custom_text = st.text_area(
            "Custom variables",
            value=custom_text_default,
            placeholder="MY_VAR=my_value\nANOTHER_VAR=another_value",
            height=120,
        )

        # Parse custom vars
        custom_dict = {}
        for line in custom_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                ck, cv = line.split("=", 1)
                custom_dict[ck.strip()] = cv.strip()

        # Merge final env
        final_env = {}
        for k in REQUIRED_ENV_VARS:
            if updated_env.get(k):
                final_env[k] = updated_env[k]
        final_env.update(custom_dict)

        c_ok, c_cancel = st.columns(2)
        with c_ok:
            if st.button("💾 Save .env", type="primary"):
                missing_now = [k for k in REQUIRED_ENV_VARS if not final_env.get(k)]
                if missing_now:
                    st.error(f"Missing required variables: {', '.join(missing_now)}")
                else:
                    try:
                        save_env_file(env_file, final_env)
                        st.success(f".env saved to {env_file}")
                        st.session_state.show_env_editor = False
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save .env: {e}")
        with c_cancel:
            if st.button("Cancel"):
                st.session_state.show_env_editor = False

    st.divider()

    # --- 3. Python Dependencies ---
    st.subheader("3. Python Dependencies")
    if os.path.exists(req_file):
        with open(req_file, 'r', encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = re.split(r'[=<>!]', line)[0].strip()
            ver = get_installed_version(pkg)
            c1, c2, c3 = st.columns([3, 2, 2])
            with c1:
                st.code(line, language="text")
            with c2:
                st.write(f"Installed: {ver}" if ver else "Missing")
            with c3:
                if not ver:
                    if st.button("Install", key=f"install_{pkg}"):
                        with st.status(f"Installing {pkg}...", expanded=True) as status:
                            log_box = st.empty()
                            ok, msg = install_package(line, output_container=log_box)
                            if ok:
                                status.update(label=f"✅ {pkg} Installed!", state="complete", expanded=False)
                                time.sleep(1)
                                st.rerun()
                            else:
                                status.update(label=f"❌ Failed {pkg}", state="error", expanded=True)
                                st.error(msg)
    else:
        st.warning("No requirements.txt found.")



def page_allure_results():
    st.header("📊 Results")
    project_path = st.session_state.get("proj_path", os.getcwd())
    allure_dir = os.path.join(project_path, "allure-results")
    allure_cmd = get_allure_path()
    
    if os.path.exists(allure_dir):
        stats = parse_allure_results(allure_dir)
        if stats and stats['Total']>0:
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total", stats['Total'])
            m2.metric("Passed", stats['Passed'])
            m3.metric("Failed", stats['Failed'])
            m4.metric("Other", stats['Broken']+stats['Skipped'])
            if st.button("🌐 Open Report"):
                if allure_cmd: 
                    if os.getenv("STREAMLIT_SHARING_MODE"):
                        st.warning("Allure Serve is not supported in Cloud mode. Please download the 'allure-results' folder and run 'allure serve' locally.")
                    else:
                        with st.spinner("Opening Allure Report..."):
                            time.sleep(1)
                        subprocess.Popen([allure_cmd, "serve", allure_dir], cwd=project_path, env=os.environ.copy())
                        st.success("Allure Report Opened!")
                        st.rerun()
                else: st.error("Allure missing.")
            results_list = []
            for jf in glob.glob(os.path.join(allure_dir, "*-result.json")):
                try:
                    with open(jf,'r') as f:
                        d=json.load(f)
                        results_list.append({"Test": d.get("name"), "Status": d.get("status")})
                except: pass
            if results_list: st.dataframe(pd.DataFrame(results_list), use_container_width=True)
        else: st.warning("No results.")
    else: st.error("No allure-results folder.")

# --- 5. Navigation & Footer ---
pg = st.navigation({
    "Test Automation": [
        st.Page(page_execution_run, title="Current Execution Run", icon="🚀"),
        st.Page(page_steps_viewer, title="Step Definitions", icon="👣"),
        st.Page(page_requirements, title="Verify Requirements", icon="📦"),
        st.Page(page_allure_results, title="View Allure Results", icon="📊"),
    ]
})

st.sidebar.title("🦄 Behave Runner")
st.sidebar.markdown("---")
st.sidebar.caption("Developed by **Gaurav Wardhekar**")
st.sidebar.markdown("---")
st.sidebar.caption("Developed for **🚀YAN IT Solutions**")
pg.run()
render_footer()
