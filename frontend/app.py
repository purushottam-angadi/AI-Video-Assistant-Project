import streamlit as st
import os
import re
import json
import requests

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
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
        resp = requests.get(f"{API_BASE}/me", headers={"Authorization": f"Bearer {token}"}, timeout=5)
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


def bullets(content: str):
    return [l.lstrip("•-– *").strip() for l in clean_llm_text(content).split("\n") if l.strip()]


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

if not st.session_state.auth_checked:
    saved_token = load_saved_token()
    if saved_token and token_is_valid(saved_token):
        st.session_state.access_token = saved_token
    else:
        clear_saved_token()
    st.session_state.auth_checked = True


# ─────────────────────────────────────────────
# Login / Signup screen
# ─────────────────────────────────────────────
def show_auth_screen():
    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.markdown('<div class="auth-title">Welcome to VideoMind</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-subtitle">Log in to your account, or sign up to start turning your recordings into searchable, chat-ready knowledge.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
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
                            token = resp.json()["access_token"]
                            save_token(token)
                            st.session_state.access_token = token
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not reach the server: {e}")

            with tab_signup:
                with st.form("signup_form"):
                    new_username = st.text_input("Choose a username", key="signup_username")
                    new_password = st.text_input("Choose a password", type="password", key="signup_password")
                    submitted_signup = st.form_submit_button("Create account")

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
        <p class="app-subtitle">Turn any recording into a transcript, a summary, and a conversation.</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-copy">
Drop in a meeting recording, lecture, interview, or podcast — VideoMind transcribes it,
pulls out a summary, action items, key decisions, and open questions, and lets you ask
follow-up questions directly against what was said, in either English or Hinglish.
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Upload — full width, native container
# ─────────────────────────────────────────────
ALLOWED_EXT = ["mp4", "mkv", "mov", "avi", "webm", "flv", "mp3", "wav", "m4a", "ogg", "flac", "aac"]
AUDIO_EXT = {"mp3", "wav", "m4a", "ogg", "flac", "aac"}

with st.container(border=True):
    st.markdown('<div class="section-title">Upload a recording</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([4, 1, 1], gap="medium")
    with c1:
        uploaded = st.file_uploader(
            "upload", label_visibility="collapsed",
            type=ALLOWED_EXT,
            help="Video: MP4 MKV MOV AVI WebM FLV · Audio: MP3 WAV M4A OGG FLAC AAC",
            key="file_upload",
        )
        if uploaded:
            ext = uploaded.name.rsplit(".", 1)[-1].lower()
            kind = "Audio" if ext in AUDIO_EXT else "Video"
            st.caption(f"{uploaded.name} · {fmt_size(uploaded.size)} · {kind} · {ext}")
    with c2:
        language = st.selectbox("Language", ["english", "hinglish"], key="lang_file", label_visibility="collapsed")
    with c3:
        run_file = st.button("Analyse →", key="run_file", use_container_width=True)

if run_file:
    if uploaded is None:
        st.warning("Upload a file first.")
    else:
        st.session_state.chat_history_str = ""
        st.session_state.chat_display = []
        st.session_state.pipeline_ran = False
        st.session_state.retriever_ready = False

        ext = uploaded.name.rsplit(".", 1)[-1].lower()
        st.session_state.upload_meta = {
            "name": uploaded.name,
            "ext": ext.upper(),
            "size": fmt_size(uploaded.size),
            "kind": "Audio" if ext in AUDIO_EXT else "Video",
        }

        with st.spinner("Analysing… this may take a minute for long recordings"):
            try:
                files = {"file": (uploaded.name, uploaded.getvalue())}
                resp = requests.post(
                    f"{API_BASE}/process",
                    data={"language": language, "youtube_url": ""},
                    files=files,
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
                st.session_state.pipeline_ran = True
                st.session_state.retriever_ready = True
            except requests.exceptions.RequestException as e:
                st.error(f"Pipeline error: {e}")


# ─────────────────────────────────────────────
# Results — tabbed: Summary / Actions / Decisions / Questions / Chat
# ─────────────────────────────────────────────
if st.session_state.pipeline_ran and st.session_state.pipeline_result:
    res = st.session_state.pipeline_result
    meta = st.session_state.upload_meta or {}

    word_count = len(res["transcript"].split())
    n_actions = len(bullets(res["action_items"]))
    n_decisions = len(bullets(res["key_decisions"]))
    n_questions = len(bullets(res["open_questions"]))

    st.divider()
    st.markdown(f'<div class="section-heading">{res["title"]}</div>', unsafe_allow_html=True)

    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    col_a.metric("Source", meta.get("kind", "—"))
    col_b.metric("Format", meta.get("ext", "—"))
    col_c.metric("File size", meta.get("size", "—"))
    col_d.metric("Words", f"{word_count:,}")
    col_e.metric("Length", estimate_speaking_time(word_count))

    tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
        ["Summary", f"Action Items ({n_actions})", f"Decisions ({n_decisions})",
         f"Open Questions ({n_questions})", "Transcript", "Chat"]
    )

    with tab_summary:
        st.write(clean_llm_text(res["summary"]))

    with tab_actions:
        items = bullets(res["action_items"])
        for item in items or ["None found"]:
            st.markdown(f"- {item}")

    with tab_decisions:
        items = bullets(res["key_decisions"])
        for item in items or ["None found"]:
            st.markdown(f"- {item}")

    with tab_questions:
        items = bullets(res["open_questions"])
        for item in items or ["None found"]:
            st.markdown(f"- {item}")

    with tab_transcript:
        st.text_area("t", label_visibility="collapsed", value=res["transcript"], height=350)

    with tab_chat:
        for turn in st.session_state.chat_display:
            with st.chat_message("user"):
                st.write(turn["user"])
            with st.chat_message("assistant"):
                st.write(turn["bot"])

        user_q = st.chat_input("Ask something about this recording…")

        if user_q:
            if not st.session_state.retriever_ready:
                st.warning("Upload and analyse a recording first.")
            else:
                with st.spinner("Thinking…"):
                    try:
                        resp = requests.post(
                            f"{API_BASE}/chat",
                            json={"question": user_q.strip(), "chat_history": st.session_state.chat_history_str},
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