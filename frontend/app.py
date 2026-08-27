import streamlit as st
import os
import re
import json
import requests

API_BASE = os.getenv("API_BASE", "http://127.0.0.1:8000")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".auth_token.json")
CSS_FILE = os.path.join(os.path.dirname(__file__), "style.css")

# ── Update these with your real handles ──
INSTAGRAM_URL = "https://instagram.com/puruu_angadi"
LINKEDIN_URL = "https://www.linkedin.com/in/puru-angadi/"
GITHUB_URL = "https://github.com/purushottam-angadi/AI-Video-Assistant-Project"

st.set_page_config(
    page_title="VidMind",
    page_icon="◈",
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


def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
defaults = {
    "access_token": None,
    "auth_checked": False,
    "page": "landing",        # "landing" | "auth" | "app"
    "auth_default_tab": "Sign up",
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
        st.session_state.page = "app"
    else:
        clear_saved_token()
    st.session_state.auth_checked = True


# ─────────────────────────────────────────────
# Landing page
# ─────────────────────────────────────────────
def show_landing_page():
    nav_l, nav_r = st.columns([3, 1])
    with nav_l:
        st.markdown("""
        <div class="nav-brand">
            <div class="app-logo">VM</div>
            <div class="nav-brand-name">VidMind</div>
        </div>
        """, unsafe_allow_html=True)
    with nav_r:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Log in", key="nav_login"):
                st.session_state.auth_default_tab = "Log in"
                st.session_state.page = "auth"
                st.rerun()
        with c2:
            if st.button("Sign up", key="nav_signup"):
                st.session_state.auth_default_tab = "Sign up"
                st.session_state.page = "auth"
                st.rerun()

    st.markdown("""
    <div class="landing-hero">
        <div class="landing-eyebrow">AI-Powered Meeting Intelligence Platform</div>
        <div class="landing-title">Every recording, <span>understood.</span></div>
        <div class="landing-subtitle">
            VidMind turns your meetings, lectures, interviews, and podcasts into transcripts,
            summaries, action items, and a live conversation — so you never have to
            re-watch a recording to find what mattered.
        </div>
    </div>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1, 1])
    with mid:
        if st.button("Start here →", key="hero_cta", use_container_width=True):
            st.session_state.auth_default_tab = "Sign up"
            st.session_state.page = "auth"
            st.rerun()

    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon">01</div>
            <div class="feature-title">Transcription, multilingual</div>
            <div class="feature-desc">Accurate transcripts from any video or audio file, in English or Hinglish, with automatic language detection.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">02</div>
            <div class="feature-title">Instant structure</div>
            <div class="feature-desc">Summaries, action items, key decisions, and open questions — extracted automatically, ready to scan in seconds.</div>
        </div>
        <div class="feature-card">
            <div class="feature-icon">03</div>
            <div class="feature-title">Ask it anything</div>
            <div class="feature-desc">A context-aware chat grounded in your recording's actual content, with web search fallback when it isn't covered.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="about-section">
        <div class="about-heading">About VidMind</div>
        <div class="about-body">
            VidMind is built on a Corrective RAG pipeline — retrieval that grades its own results,
            falls back to live web search when a recording doesn't have the answer, and stays
            grounded through guardrails at every step. Every recording is processed in isolation
            per account, with nothing shared between users. It's a small, focused tool built to
            make one thing genuinely useful: never losing track of what was actually said.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="landing-footer">
        <div class="footer-brand">VidMind — built by Purushottam Angadi</div>
        <div class="social-links">
            <a href="{INSTAGRAM_URL}" target="_blank">Instagram</a>
            <a href="{LINKEDIN_URL}" target="_blank">LinkedIn</a>
            <a href="{GITHUB_URL}" target="_blank">GitHub</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Auth screen
# ─────────────────────────────────────────────
def show_auth_screen():
    if st.button("← Back", key="back_to_landing"):
        st.session_state.page = "landing"
        st.rerun()

    left, center, right = st.columns([1, 1.1, 1])
    with center:
        st.markdown('<div class="auth-title">Welcome to VidMind</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-subtitle">Sign up to get started, or log in if you already have an account.</div>',
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            tab_labels = ["Sign up", "Log in"]
            default_index = tab_labels.index(st.session_state.auth_default_tab)
            tabs = st.tabs(tab_labels)
            tab_signup, tab_login = tabs[0], tabs[1]

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
                            st.success("Account created — log in below to continue.")
                        else:
                            detail = resp.json().get("detail", "Signup failed.")
                            st.error(detail)
                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not reach the server: {e}")

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
                            st.session_state.page = "app"
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                    except requests.exceptions.RequestException as e:
                        st.error(f"Could not reach the server: {e}")


# ─────────────────────────────────────────────
# Main app (the actual tool)
# ─────────────────────────────────────────────
def show_main_app():
    st.sidebar.markdown("### VidMind")
    st.sidebar.success("● Logged in")
    if st.sidebar.button("Log out"):
        clear_saved_token()
        st.session_state.access_token = None
        st.session_state.auth_checked = False
        st.session_state.pipeline_ran = False
        st.session_state.retriever_ready = False
        st.session_state.page = "landing"
        st.rerun()

    st.markdown("""
    <div class="app-header">
        <div class="app-logo">VM</div>
        <div>
            <p class="app-title">VidMind</p>
            <p class="app-subtitle">Turn any recording into a transcript, a summary, and a conversation.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-copy">
    Drop in a meeting recording, lecture, interview, or podcast — VidMind transcribes it,
    pulls out a summary, action items, key decisions, and open questions, and lets you ask
    follow-up questions directly against what was said, in either English or Hinglish.
    </div>
    """, unsafe_allow_html=True)

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
                        st.session_state.page = "landing"
                        st.rerun()
                    resp.raise_for_status()
                    result = resp.json()

                    st.session_state.pipeline_result = result
                    st.session_state.pipeline_ran = True
                    st.session_state.retriever_ready = True
                except requests.exceptions.RequestException as e:
                    st.error(f"Pipeline error: {e}")

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

        st.write("")

        tab_summary, tab_actions, tab_decisions, tab_questions, tab_transcript, tab_chat = st.tabs(
            ["Summary", f"Action Items ({n_actions})", f"Decisions ({n_decisions})",
             f"Open Questions ({n_questions})", "Transcript", "Chat"]
        )

        with tab_summary:
            with st.container(border=True):
                st.write(clean_llm_text(res["summary"]))

        with tab_actions:
            with st.container(border=True):
                for item in bullets(res["action_items"]) or ["None found"]:
                    st.markdown(f"- {item}")

        with tab_decisions:
            with st.container(border=True):
                for item in bullets(res["key_decisions"]) or ["None found"]:
                    st.markdown(f"- {item}")

        with tab_questions:
            with st.container(border=True):
                for item in bullets(res["open_questions"]) or ["None found"]:
                    st.markdown(f"- {item}")

        with tab_transcript:
            st.text_area("t", label_visibility="collapsed", value=res["transcript"], height=350)

        with tab_chat:
            chat_html = '<div class="chat-log">'
            for turn in st.session_state.chat_display:
                chat_html += f"""
                <div class="chat-row user">
                    <div class="chat-label">You</div>
                    <div class="chat-bubble user">{escape_html(turn['user'])}</div>
                </div>
                <div class="chat-row assistant">
                    <div class="chat-label">VidMind</div>
                    <div class="chat-bubble assistant">{escape_html(turn['bot'])}</div>
                </div>
                """
            chat_html += '</div>'

            if not st.session_state.chat_display:
                st.markdown('<div class="chat-empty">Ask anything about this recording to get started.</div>', unsafe_allow_html=True)
            else:
                st.markdown(chat_html, unsafe_allow_html=True)

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
                                st.session_state.page = "landing"
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


# ─────────────────────────────────────────────
# Page router
# ─────────────────────────────────────────────
if st.session_state.access_token:
    show_main_app()
elif st.session_state.page == "auth":
    show_auth_screen()
else:
    show_landing_page()