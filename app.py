import io
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Anywhere Storage", page_icon="☁️")

SCOPES = ["https://www.googleapis.com/auth/drive"]

st.title("☁️ Anywhere Storage")
st.caption("Upload any file directly to your Google Drive.")


@st.cache_resource
def get_drive_service():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


@st.cache_data(ttl=60)
def list_folders():
    service = get_drive_service()
    results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=200,
    ).execute()
    return results.get("files", [])


folders = list_folders()

if not folders:
    st.warning(
        "No folders found. Share at least one Drive folder with your "
        "service account's email (found in your JSON key's client_email field)."
    )
    st.stop()

folder_names = [f["name"] for f in folders]
selected_name = st.selectbox("Choose destination folder", folder_names)
selected_id = next(f["id"] for f in folders if f["name"] == selected_name)

uploaded_file = st.file_uploader("Choose any file")

if st.button("Upload File", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("Please choose a file.")
    else:
        try:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                service = get_drive_service()
                media = MediaIoBaseUpload(
                    io.BytesIO(uploaded_file.getvalue()),
                    mimetype=uploaded_file.type or "application/octet-stream",
                    resumable=True,
                )
                result = service.files().create(
                    body={"name": uploaded_file.name, "parents": [selected_id]},
                    media_body=media,
                    fields="id,name,webViewLink",
                ).execute()

            st.success(f"Uploaded: {result['name']}")
            st.link_button("Open in Google Drive", result["webViewLink"])
        except Exception as exc:
            st.error(f"Upload failed: {exc}")
