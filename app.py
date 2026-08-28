import io
import streamlit as st
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Anywhere Storage", page_icon="☁️")

SCOPES = ["https://www.googleapis.com/auth/drive"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

st.title("☁️ Anywhere Storage")
st.caption("Upload any file directly to your Google Drive.")


def get_flow():
    client_config = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
        }
    }
    return Flow.from_client_config(client_config, scopes=SCOPES, redirect_uri=REDIRECT_URI)


if "credentials" not in st.session_state:
    if "code" in st.query_params:
        flow = get_flow()
        flow.fetch_token(code=st.query_params["code"])
        st.session_state["credentials"] = flow.credentials
        st.query_params.clear()
        st.rerun()
    else:
        flow = get_flow()
        auth_url, _ = flow.authorization_url(
            access_type="offline", include_granted_scopes="true", prompt="consent"
        )
        st.link_button("Sign in with Google", auth_url, type="primary")
        st.stop()

service = build("drive", "v3", credentials=st.session_state["credentials"])


@st.cache_data(ttl=60)
def list_folders(_service):
    results = _service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id, name)",
        pageSize=200,
    ).execute()
    return results.get("files", [])


folders = list_folders(service)
folder_names = ["My Drive (root)"] + [f["name"] for f in folders]
selected_name = st.selectbox("Choose destination folder", folder_names)
selected_id = None if selected_name == "My Drive (root)" else next(
    f["id"] for f in folders if f["name"] == selected_name
)

uploaded_file = st.file_uploader("Choose any file")

if st.button("Upload File", type="primary", use_container_width=True):
    if uploaded_file is None:
        st.warning("Please choose a file.")
    else:
        try:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                media = MediaIoBaseUpload(
                    io.BytesIO(uploaded_file.getvalue()),
                    mimetype=uploaded_file.type or "application/octet-stream",
                    resumable=True,
                )
                body = {"name": uploaded_file.name}
                if selected_id:
                    body["parents"] = [selected_id]
                result = service.files().create(
                    body=body, media_body=media, fields="id,name,webViewLink"
                ).execute()
            st.success(f"Uploaded: {result['name']}")
            st.link_button("Open in Google Drive", result["webViewLink"])
        except Exception as exc:
            st.error(f"Upload failed: {exc}")

if st.button("Sign out"):
    del st.session_state["credentials"]
    st.rerun()
