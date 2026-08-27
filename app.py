import io
import json
import os

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Anywhere Storage", page_icon="☁️", layout="centered")

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")


def load_service_account_info():
    """
    Resolve service-account credentials from, in order:
      1) Streamlit secrets (st.secrets["gcp_service_account"]) - best for Streamlit Cloud
      2) A local JSON key file (service-account.json, or GOOGLE_SERVICE_ACCOUNT_FILE)
      3) JSON pasted into the app UI (session state), for quick local testing
    Returns a dict, or None if nothing is configured yet.
    """
    if "gcp_service_account" in st.secrets:
        return dict(st.secrets["gcp_service_account"])

    if os.path.isfile(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    pasted = st.session_state.get("pasted_service_account_json")
    if pasted:
        try:
            return json.loads(pasted)
        except json.JSONDecodeError:
            return None

    return None


def get_drive_service(info):
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def upload_file(service, uploaded_file, folder_id):
    metadata = {
        "name": uploaded_file.name,
        "parents": [folder_id],
    }
    data = uploaded_file.getvalue()
    media = MediaIoBaseUpload(
        io.BytesIO(data),
        mimetype=uploaded_file.type or "application/octet-stream",
        resumable=True,
        chunksize=8 * 1024 * 1024,
    )
    return service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,size,webViewLink",
        supportsAllDrives=True,
    ).execute()


st.title("☁️ Anywhere Storage")
st.caption("Upload any file directly to your Google Drive destination.")

service_account_info = load_service_account_info()
service_account_email = (
    service_account_info.get("client_email") if service_account_info else None
)

with st.expander(
    "🔑 Service account credentials"
    + (" — configured" if service_account_info else " — not configured"),
    expanded=service_account_info is None,
):
    st.markdown(
        "Provide credentials using **one** of these methods:\n\n"
        "1. **Streamlit Cloud (recommended for hosting):** add your key under "
        "`Settings → Secrets` as:\n"
        "```toml\n"
        "[gcp_service_account]\n"
        'type = "service_account"\n'
        'project_id = "..."\n'
        'private_key_id = "..."\n'
        'private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"\n'
        'client_email = "...@....iam.gserviceaccount.com"\n'
        'client_id = "..."\n'
        'token_uri = "https://oauth2.googleapis.com/token"\n'
        "```\n"
        "2. **Local file:** place your downloaded key as `service-account.json` "
        "next to this app (or set `GOOGLE_SERVICE_ACCOUNT_FILE`).\n"
        "3. **Paste it here** (not saved anywhere, just kept for this session):"
    )
    pasted_json = st.text_area(
        "Paste service-account JSON key",
        value=st.session_state.get("pasted_service_account_json", ""),
        height=120,
        placeholder='{ "type": "service_account", "client_email": "...", ... }',
    )
    if st.button("Use pasted credentials"):
        st.session_state["pasted_service_account_json"] = pasted_json
        st.rerun()

    if service_account_email:
        st.success(f"Using service account: {service_account_email}")
    else:
        st.warning("No credentials configured yet.")

folder_id = st.text_input(
    "Google Drive destination folder ID",
    value=os.getenv("GOOGLE_DRIVE_FOLDER_ID", ""),
    placeholder="Example: 1AbCdEfGhIjKlMnOp",
    help="Copy the ID from the Google Drive folder URL.",
)

uploaded_file = st.file_uploader("Choose any file", type=None)

if st.button("Upload File", type="primary", use_container_width=True):
    if service_account_info is None:
        st.error("Please configure service-account credentials above first.")
    elif not folder_id.strip():
        st.warning("Please enter the Google Drive folder ID.")
    elif uploaded_file is None:
        st.warning("Please choose a file.")
    else:
        try:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                service = get_drive_service(service_account_info)
                result = upload_file(service, uploaded_file, folder_id.strip())
            st.success(f"Uploaded successfully: {result['name']}")
            st.write(f"File ID: `{result['id']}`")
            if result.get("size"):
                st.write(f"Size: {int(result['size']):,} bytes")
            if result.get("webViewLink"):
                st.link_button("Open in Google Drive", result["webViewLink"])
        except Exception as exc:
            st.error(f"Upload failed: {exc}")
            st.info(
                "Make sure the destination folder is shared with:\n\n"
                f"{service_account_email or '(your service account email)'}"
            )

st.divider()
if service_account_email:
    st.caption(f"Service account: {service_account_email}")
