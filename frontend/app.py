import streamlit as st
import gc
import os
import shutil
import tempfile
import re
import json
import requests

import os
API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
st.sidebar.caption(f"API_BASE: {API_BASE}")   # ← add this line temporarily
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".auth_token.json")
CSS_FILE = os.path.join(os.path.dirname(__file__), "style.css")

st.set_page_config(
    page_title="VideoMind",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def load_css(path: str):
    with open(path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css(CSS_FILE)


# ─────────────────────────────────────────────
# Token persistence helpers
# ─────────────────────────────────────────────
def save_token(token: str):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"access_token": token}, f)


def load_saved_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f).get("access_token")
    except (json.JSONDecodeError, KeyError):
        return None


def clear_saved_token():
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


def token_is_valid(token: str) -> bool:
    try:
        resp = requests.get(
            f"{API_BASE}/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.access_token}"}


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def clean_llm_text(text: str) -> str:
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^[-•*]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_speaking_time(word_count: int) -> str:
    minutes = max(1, round(word_count / 150))
    if minutes < 60:
        return f"~{minutes} min"
    h, m = divmod(minutes, 60)
    return f"~{h}h {m}m" if m else f"~{h}h"


def fmt_size(num_bytes: int) -> str:
    mb = num_bytes / 1_048_576
    if mb < 1024:
        return f"{mb:.1f} MB"
    return f"{mb/1024:.2f} GB"


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
defaults = {
    "access_token": None,
    "auth_checked": False,
    "pipeline_result": None,
    "chat_history_str": "",
    "chat_display": [],
    "pipeline_ran": False,
    "upload_meta": None,
    "retriever_ready": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# On first load: try the saved token before showing any login form
# ─────────────────────────────────────────────
if not st.session_state.auth_checked:
    saved_token = load_saved_token()
    if saved_token and token_is_valid(saved_token):
        st.session_state.access_token = saved_token
    else:
        clear_saved_token()
    st.session_state.auth_checked = True


# ─────────────────────────────────────────────
# Login / Signup screen — real centered card via columns
# ─────────────────────────────────────────────
def show_auth_screen():
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<div class="auth-title">VideoMind</div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-subtitle">Sign in to continue, or create an account if you\'re new.</div>', unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Log in")

                if submitted:
                 try:
                    resp = requests.post(
                        f"{API_BASE}/login",
                        data={"username": username, "password": password},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        try:
                            token = resp.json()["access_token"]
                            save_token(token)
                            st.session_state.access_token = token
                            st.rerun()
                        except (ValueError, KeyError):
                            st.error(f"Server returned 200 but invalid JSON: {resp.text[:300]}")
                    else:
                        st.error(f"Invalid username or password. (status {resp.status_code}: {resp.text[:200]})")
                 except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach the server: {e}")
                    
        with tab_signup:
            with st.form("signup_form"):
                new_username = st.text_input("Choose a username", key="signup_username")
                new_password = st.text_input("Choose a password", type="password", key="signup_password")
                submitted_signup = st.form_submit_button("Sign up")

            if submitted_signup:
                try:
                    resp = requests.post(
                        f"{API_BASE}/signup",
                        json={"username": new_username, "password": new_password},
                        timeout=10,
                    )
                    if resp.status_code == 201:
                        st.success("Account created — switch to the Log in tab.")
                    else:
                        detail = resp.json().get("detail", "Signup failed.")
                        st.error(detail)
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach the server: {e}")

        st.markdown('</div>', unsafe_allow_html=True)


if not st.session_state.access_token:
    show_auth_screen()
    st.stop()


# ─────────────────────────────────────────────
# Logged in from here on
# ─────────────────────────────────────────────
st.sidebar.markdown("### VideoMind")
st.sidebar.success("● Logged in")
if st.sidebar.button("Log out"):
    clear_saved_token()
    st.session_state.access_token = None
    st.session_state.auth_checked = False
    st.session_state.pipeline_ran = False
    st.session_state.retriever_ready = False
    st.rerun()

st.markdown("""
<div class="app-header">
    <div class="app-logo">VM</div>
    <div>
        <p class="app-title">VideoMind</p>
        <p class="app-subtitle">Transcription, summarisation and Q&A for video and audio</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Input card — File upload
# ─────────────────────────────────────────────
ALLOWED_EXT = ["mp4","mkv","mov","avi","webm","flv","mp3","wav","m4a","ogg","flac","aac"]
AUDIO_EXT = {"mp3","wav","m4a","ogg","flac","aac"}

source        = ""
uploaded_path = None
language      = "english"

st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">Upload file</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([4, 1, 1], gap="medium")
with c1:
    uploaded = st.file_uploader(
        "upload", label_visibility="collapsed",
        type=ALLOWED_EXT,
        help="Video: MP4 MKV MOV AVI WebM FLV  ·  Audio: MP3 WAV M4A OGG FLAC AAC",
        key="file_upload",
    )
    if uploaded:
        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        kind = "Audio" if ext in AUDIO_EXT else "Video"
        st.caption(f"{uploaded.name} · {fmt_size(uploaded.size)} · {kind} · {ext}")
with c2:
    language = st.selectbox("Language", ["english", "hinglish"],
                            key="lang_file", label_visibility="collapsed")
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    run_file = st.button("Analyse →", key="run_file", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

if run_file:
    if uploaded is None:
        st.warning("Upload a file first.")
    else:
        suffix = "." + uploaded.name.rsplit(".", 1)[-1].lower()
        os.makedirs("downloads", exist_ok=True)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir="downloads")
        shutil.copyfileobj(uploaded, tmp)
        size_bytes = tmp.tell()
        tmp.close()
        uploaded_path = tmp.name
        source        = uploaded_path
        st.session_state.upload_meta = {
            "name": uploaded.name,
            "ext": suffix.lstrip(".").upper(),
            "size": fmt_size(size_bytes),
            "kind": "Audio" if suffix.lstrip(".").lower() in AUDIO_EXT else "Video",
        }


# ─────────────────────────────────────────────
# Pipeline call — POST /process
# ─────────────────────────────────────────────
if source:
    if st.session_state.retriever_ready:
        st.session_state.retriever_ready = False
        gc.collect()

    st.session_state.chat_history_str = ""
    st.session_state.chat_display     = []
    st.session_state.pipeline_ran     = False

    with st.spinner("Analysing… this may take a minute for long videos"):
        try:
            resp = requests.post(
                f"{API_BASE}/process",
                json={"source": source, "language": language},
                headers=auth_headers(),
                timeout=600,
            )
            if resp.status_code == 401:
                st.error("Session expired — please log in again.")
                clear_saved_token()
                st.session_state.access_token = None
                st.session_state.auth_checked = False
                st.rerun()
            resp.raise_for_status()
            result = resp.json()

            st.session_state.pipeline_result = result
            st.session_state.pipeline_ran    = True
            st.session_state.retriever_ready = True
        except requests.exceptions.RequestException as e:
            st.error(f"Pipeline error: {e}")
        finally:
            if uploaded_path and os.path.exists(uploaded_path):
                os.remove(uploaded_path)


# ─────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────
if st.session_state.pipeline_ran and st.session_state.pipeline_result:
    res = st.session_state.pipeline_result
    meta = st.session_state.upload_meta or {}

    word_count = len(res["transcript"].split())
    n_actions   = len([l for l in res["action_items"].split("\n") if l.strip()])
    n_decisions = len([l for l in res["key_decisions"].split("\n") if l.strip()])
    n_questions = len([l for l in res["open_questions"].split("\n") if l.strip()])

    st.markdown(f'<div class="section-heading">{res["title"]}</div>', unsafe_allow_html=True)
    st.caption("Analysis complete")

    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    col_a.metric("Source", meta.get("kind", "—"))
    col_b.metric("Format", meta.get("ext", "—"))
    col_c.metric("File size", meta.get("size", "—"))
    col_d.metric("Transcript words", f"{word_count:,}")
    col_e.metric("Est. spoken length", estimate_speaking_time(word_count))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Summary</div>', unsafe_allow_html=True)
    st.write(clean_llm_text(res["summary"]))
    st.markdown('</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")

    def _bullets(content):
        return [l.lstrip("•-– *").strip() for l in clean_llm_text(content).split("\n") if l.strip()]

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">Action items · {n_actions}</div>', unsafe_allow_html=True)
        for item in _bullets(res["action_items"]) or ["None found"]:
            st.markdown(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">Key decisions · {n_decisions}</div>', unsafe_allow_html=True)
        for item in _bullets(res["key_decisions"]) or ["None found"]:
            st.markdown(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<div class="section-title">Open questions · {n_questions}</div>', unsafe_allow_html=True)
        for item in _bullets(res["open_questions"]) or ["None found"]:
            st.markdown(f"- {item}")
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("Raw transcript"):
        st.text_area("t", label_visibility="collapsed", value=res["transcript"], height=200)

    st.divider()

    # ─────────────────────────────────────────────
    # Chat — POST /chat
    # ─────────────────────────────────────────────
    st.markdown('<div class="section-heading">Chat with your video</div>', unsafe_allow_html=True)

    for turn in st.session_state.chat_display:
        with st.chat_message("user"):
            st.write(turn["user"])
        with st.chat_message("assistant"):
            st.write(turn["bot"])

    user_q = st.chat_input("What were the main points discussed?")

    if user_q:
        if not st.session_state.retriever_ready:
            st.warning("Upload and analyse a video first.")
        else:
            with st.spinner("Thinking…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/chat",
                        json={
                            "question": user_q.strip(),
                            "chat_history": st.session_state.chat_history_str,
                        },
                        headers=auth_headers(),
                        timeout=120,
                    )
                    if resp.status_code == 401:
                        st.error("Session expired — please log in again.")
                        clear_saved_token()
                        st.session_state.access_token = None
                        st.session_state.auth_checked = False
                        st.rerun()
                    resp.raise_for_status()
                    raw_answer = resp.json().get("answer", "")
                except requests.exceptions.RequestException as e:
                    st.error(f"Chat error: {e}")
                    raw_answer = ""

            clean_answer = re.sub(r"^[🌐📎🎬]\s*\[.*?\]\s*\n?", "", raw_answer).strip()
            clean_answer = clean_llm_text(clean_answer)

            st.session_state.chat_history_str += f"User: {user_q}\nAssistant: {clean_answer}\n"
            st.session_state.chat_display.append({"user": user_q, "bot": clean_answer})
            st.rerun()