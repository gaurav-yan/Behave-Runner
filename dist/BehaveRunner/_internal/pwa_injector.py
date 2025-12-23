import streamlit as st
import base64

def inject_pwa():
    """
    Injects the necessary HTML/JS to make the Streamlit app PWA-installable.
    """
    # This uses a CDN or local static file for the manifest.
    # Since checking for local static files server-side in Streamlit is tricky without setup,
    # we will direct the browser to fetch 'static/manifest.json'. 
    # NOTE: Streamlit >= 1.10 serves the 'static' folder at relative path 'static/'.
    
    pwa_meta = """
<head>
    <link rel="manifest" href="app/static/manifest.json" crossorigin="use-credentials">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="application-name" content="Behave Runner">
    <meta name="theme-color" content="#0e1117">
</head>
"""
    
    st.markdown(
        f"""
{pwa_meta}
<script>
    // Check if service worker is supported
    if ('serviceWorker' in navigator) {{
        window.addEventListener('load', function() {{
            // We don't necessarily need a complex service worker for a local runner,
            // but having one registered helps Chrome prompt for installation.
            // This is a dummy registration if you don't have a sw.js.
            // navigator.serviceWorker.register('sw.js');
        }});
    }}
</script>
""",
        unsafe_allow_html=True,
    )
