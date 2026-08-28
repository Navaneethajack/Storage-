import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Anywhere Storage", page_icon="☁️")

SCOPES = ["https://www.googleapis.com/auth/drive"]

st.title("☁️ Anywhere Storage")
st.caption("Upload any file directly to your Google Drive destination.")

folder_id = st.text_input("Google Drive destination folder ID")
uploaded_file = st.file_uploader("Choose any file")

if st.button("Upload File", type="primary", use_container_width=True):
    if not folder_id.strip():
        st.warning("Please enter the Google Drive folder ID.")
    elif uploaded_file is None:
        st.warning("Please choose a file.")
    else:
        try:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                credentials = service_account.Credentials.from_service_account_info(
                    st.secrets["gcp_service_account"], scopes=SCOPES
                )
                service = build("drive", "v3", credentials=credentials)

                media = MediaIoBaseUpload(
                    io.BytesIO(uploaded_file.getvalue()),
                    mimetype=uploaded_file.type or "application/octet-stream",
                    resumable=True,
                )
                result = service.files().create(
                    body={"name": uploaded_file.name, "parents": [folder_id.strip()]},
                    media_body=media,
                    fields="id,name,webViewLink",
                ).execute()

            st.success(f"Uploaded: {result['name']}")
            st.link_button("Open in Google Drive", result["webViewLink"])
        except Exception as exc:
            st.error(f"Upload failed: {exc}")
