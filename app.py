import os
import tempfile

import streamlit as st
from mega import Mega

st.set_page_config(page_title="Anywhere Storage", page_icon="☁️")

st.title("☁️ Anywhere Storage")
st.caption("Upload any file directly to your MEGA account.")

uploaded_file = st.file_uploader("Choose any file")

if st.button("Upload File", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("Please choose a file.")
    else:
        tmp_path = None
        try:
            with st.spinner("Logging in to MEGA..."):
                mega = Mega()
                m = mega.login(st.secrets["mega_email"], st.secrets["mega_password"])

            # mega.py uploads from a path on disk, so write the file to a temp path first
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = tmp.name

            with st.spinner(f"Uploading {uploaded_file.name}..."):
                file = m.upload(tmp_path, dest_filename=uploaded_file.name)
                link = m.get_upload_link(file)

            st.success(f"Uploaded: {uploaded_file.name}")
            st.link_button("Open in MEGA", link)
        except Exception as exc:
            st.error(f"Upload failed: {exc}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
