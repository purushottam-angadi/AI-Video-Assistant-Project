
import streamlit as st
import os
import tempfile
from dotenv import load_dotenv
import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)
load_dotenv()

st.set_page_config(
    page_title="VideoMind AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500&family=Fira+Code:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #080d1a; color: #e8edf5; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 0; padding-bottom: 2.5rem; max-width: 1100px; }

/* ── Kill ghost boxes ── */
[data-testid="stVerticalBlock"] > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
div[data-testid="stMarkdownContainer"] {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
.element-container {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stHorizontalBlock"] > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
div[class*="stColumn"] > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}

/* ── Top navbar ── */
.vm-navbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.1rem 0 1rem;
    border-bottom: 1px solid #14213d;
    margin-bottom: 2.2rem;
}
.vm-navbar-brand {
    font-family: 'Outfit', sans-serif;
    font-weight: 800;
    font-size: 1.1rem;
    color: #e8edf5;
    letter-spacing: -0.02em;
}
.vm-navbar-brand em { font-style: normal; color: #7c6af7; }
.vm-navbar-status {
    font-family: 'Fira Code', monospace;
    font-size: 0.65rem;
    color: #3a4560;
    letter-spacing: 0.12em;
}
.vm-navbar-status span {
    color: #7c6af7;
    margin-right: 0.4rem;
}

/* ── Page nav pills ── */
.vm-page-nav {
    display: flex;
    gap: 0.4rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}
.vm-nav-pill {
    font-family: 'Fira Code', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.1em;
    padding: 0.4rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid #1e2d4a;
    color: #3a4560;
    background: transparent;
    transition: all 0.15s;
    text-decoration: none;
}
.vm-nav-pill:hover { border-color: #7c6af7; color: #a89ef9; }
.vm-nav-pill.active {
    background: rgba(124,106,247,0.12);
    border-color: #7c6af7;
    color: #a89ef9;
}

/* ── Hero ── */
.vm-hero {
    position: relative;
    padding: 4rem 0 3rem;
    overflow: hidden;
}
.vm-hero::before {
    content: '';
    position: absolute;
    top: -80px; right: -120px;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(124,106,247,0.07) 0%, transparent 60%);
    pointer-events: none;
}
.vm-hero-eyebrow {
    font-family: 'Fira Code', monospace;
    font-size: 0.68rem;
    color: #7c6af7;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.vm-hero-title {
    font-family: 'Outfit', sans-serif;
    font-size: clamp(2.8rem, 6vw, 4.2rem);
    font-weight: 800;
    color: #e8edf5;
    line-height: 1.08;
    margin: 0 0 1rem;
    letter-spacing: -0.03em;
}
.vm-hero-title em { font-style: normal; color: #7c6af7; }
.vm-hero-sub {
    font-size: 0.92rem;
    color: #4a5568;
    max-width: 500px;
    line-height: 1.7;
    margin-bottom: 0;
}

/* ── Input panel ── */
.vm-input-panel {
    background: #0d1526;
    border: 1px solid #14213d;
    border-top: 2px solid #7c6af7;
    border-radius: 8px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.2rem;
}

/* ── Cards ── */
.vm-card {
    background: #0d1526;
    border: 1px solid #14213d;
    border-top: 2px solid #7c6af7;
    border-radius: 8px;
    padding: 2rem 2.2rem;
    margin-bottom: 1.2rem;
}
.vm-card-sm {
    background: #0a1020;
    border: 1px solid #14213d;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
}
.vm-label {
    font-family: 'Fira Code', monospace;
    font-size: 0.62rem;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #7c6af7;
    margin-bottom: 0.9rem;
}
.vm-body {
    font-size: 0.9rem;
    color: #8892a4;
    line-height: 1.85;
    white-space: pre-wrap;
}
.vm-page-title {
    font-family: 'Outfit', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #e8edf5;
    letter-spacing: -0.02em;
    margin-bottom: 0.3rem;
}
.vm-page-subtitle {
    font-size: 0.85rem;
    color: #3a4560;
    margin-bottom: 2rem;
    font-family: 'Fira Code', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
}

/* ── Video title banner ── */
.vm-video-banner {
    background: linear-gradient(135deg, #0d1526 0%, #0f1a30 100%);
    border: 1px solid #14213d;
    border-left: 3px solid #7c6af7;
    border-radius: 8px;
    padding: 1.2rem 1.6rem;
    margin-bottom: 1.8rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.vm-video-name {
    font-family: 'Outfit', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #e8edf5;
    letter-spacing: -0.01em;
}
.vm-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: rgba(124,106,247,0.1);
    border: 1px solid rgba(124,106,247,0.2);
    color: #a89ef9;
    border-radius: 4px;
    padding: 0.2rem 0.7rem;
    font-family: 'Fira Code', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.1em;
    white-space: nowrap;
}

/* ── Summary home cards ── */
.vm-nav-card {
    background: #0d1526;
    border: 1px solid #14213d;
    border-radius: 8px;
    padding: 1.5rem;
    cursor: pointer;
    transition: border-color 0.2s, transform 0.15s;
    height: 100%;
}
.vm-nav-card:hover {
    border-color: #7c6af7;
    transform: translateY(-2px);
}
.vm-nav-card-icon {
    font-size: 1.4rem;
    margin-bottom: 0.7rem;
}
.vm-nav-card-title {
    font-family: 'Outfit', sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    color: #e8edf5;
    margin-bottom: 0.4rem;
}
.vm-nav-card-desc {
    font-size: 0.75rem;
    color: #3a4560;
    line-height: 1.5;
}

/* ── Chat ── */
.vm-chat {
    background: #0a1020;
    border: 1px solid #14213d;
    border-radius: 8px;
    padding: 1.4rem;
    height: 460px;
    overflow-y: auto;
    margin-bottom: 0.8rem;
    scrollbar-width: thin;
    scrollbar-color: #1e2d4a transparent;
}
.vm-chat-empty {
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    color: #1e2d4a;
    font-family: 'Fira Code', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.1em;
}
.vm-bubble-user {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.85rem;
}
.vm-bubble-user > div {
    background: #7c6af7;
    color: #ffffff;
    border-radius: 10px 10px 2px 10px;
    padding: 0.7rem 1.1rem;
    max-width: 70%;
    font-size: 0.85rem;
    line-height: 1.55;
}
.vm-bubble-bot {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 0.85rem;
}
.vm-bubble-bot > div {
    background: #0d1526;
    color: #8892a4;
    border-radius: 10px 10px 10px 2px;
    padding: 0.7rem 1.1rem;
    max-width: 76%;
    font-size: 0.85rem;
    line-height: 1.65;
    border: 1px solid #14213d;
}

/* ── Inputs ── */
.stTextInput > div,
.stTextInput > div > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
    border-radius: 0 !important;
}
.stTextInput > div > div > input {
    background: #0a1020 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 6px !important;
    color: #e8edf5 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    caret-color: #7c6af7 !important;
    padding: 0.55rem 0.9rem !important;
    box-shadow: none !important;
}
.stTextInput > div > div > input:focus {
    border-color: #7c6af7 !important;
    box-shadow: 0 0 0 2px rgba(124,106,247,0.15) !important;
    background: #080d1a !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: #2a3550 !important; }

.stSelectbox > div {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.stSelectbox > div > div {
    background: #0a1020 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 6px !important;
    color: #e8edf5 !important;
    box-shadow: none !important;
}
.stSelectbox > div > div:focus-within {
    border-color: #7c6af7 !important;
    box-shadow: 0 0 0 2px rgba(124,106,247,0.15) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: #7c6af7 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.55rem 1.4rem !important;
    width: 100%;
    transition: background 0.18s, transform 0.15s !important;
}
.stButton > button:hover {
    background: #9585f9 !important;
    transform: translateY(-1px) !important;
}
.stButton > button:disabled {
    background: #1e2d4a !important;
    color: #3a4560 !important;
    transform: none !important;
}

/* ── Radio ── */
.stRadio > div { flex-direction: row !important; gap: 0.5rem; }
.stRadio > div > label {
    background: #0d1526 !important;
    border: 1px solid #1e2d4a !important;
    border-radius: 6px !important;
    padding: 0.35rem 1rem !important;
    font-size: 0.8rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    color: #8892a4 !important;
    transition: all 0.15s !important;
}
.stRadio > div > label:hover { border-color: #7c6af7 !important; color: #a89ef9 !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0a1020 !important;
    border: 1px dashed #1e2d4a !important;
    border-radius: 8px !important;
}

/* ── Error ── */
.vm-error {
    background: rgba(239,68,68,0.06);
    border: 1px solid rgba(239,68,68,0.18);
    border-left: 3px solid #ef4444;
    border-radius: 6px;
    padding: 0.9rem 1.2rem;
    margin-top: 1rem;
    font-size: 0.82rem;
    color: #fca5a5;
    font-family: 'Fira Code', monospace;
}

/* ── Spinner ── */
.stSpinner > div { border-top-color: #7c6af7 !important; }

/* ── Download ── */
.stDownloadButton > button {
    background: transparent !important;
    color: #7c6af7 !important;
    border: 1px solid #2a1f6a !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    width: auto !important;
}
.stDownloadButton > button:hover {
    background: rgba(124,106,247,0.08) !important;
    border-color: #7c6af7 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #060b16 !important;
    border-right: 1px solid #14213d !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "pipeline_result": None,
        "chat_history": [],
        "rag_chain": None,
        "error": None,
        "page": "home",       # home | summary | actions | decisions | questions | transcript | chat
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def go(page):
    st.session_state.page = page
    st.rerun()


# ── Navbar ────────────────────────────────────────────────────────────────────
result = st.session_state.pipeline_result
status = "● processed" if result else "○ no video loaded"

st.markdown(f"""
<div class="vm-navbar">
    <div class="vm-navbar-brand">Video<em>Mind</em></div>
    <div class="vm-navbar-status"><span>{'●' if result else '○'}</span>{status}</div>
</div>
""", unsafe_allow_html=True)


# ── Page nav (only shown after processing) ────────────────────────────────────
if result:
    pages = [
        ("home",       "~/home"),
        ("summary",    "summary"),
        ("actions",    "actions"),
        ("decisions",  "decisions"),
        ("questions",  "questions"),
        ("transcript", "transcript"),
        ("chat",       "chat"),
    ]
    cols = st.columns(len(pages))
    for col, (page_id, label) in zip(cols, pages):
        with col:
            is_active = st.session_state.page == page_id
            btn_style = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{page_id}"):
                go(page_id)

    st.markdown('<hr style="border:none;border-top:1px solid #14213d;margin:0 0 1.8rem;">', unsafe_allow_html=True)

    # Video banner on every result page
    st.markdown(f"""
    <div class="vm-video-banner">
        <div class="vm-video-name">🎙️ {result.get('title', 'Untitled Video')}</div>
        <span class="vm-badge">✓ processed</span>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME (input / landing)
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home" and not result:

    st.markdown("""
    <div class="vm-hero">
        <div class="vm-hero-eyebrow">// transcribe · summarise · ask anything</div>
        <h1 class="vm-hero-title">Video<em>Mind</em><br>AI Assistant</h1>
        <p class="vm-hero-sub">
            Drop a video or paste a YouTube link.
            Get a full transcript, summary, action items — then talk to your content.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([3, 2], gap="large")

    with col_l:
        st.markdown('<div class="vm-input-panel">', unsafe_allow_html=True)
        st.markdown('<div class="vm-label">Source</div>', unsafe_allow_html=True)
        input_mode = st.radio("", ["YouTube URL", "Upload File"],
                              label_visibility="collapsed", horizontal=True)
        source = None

        if input_mode == "YouTube URL":
            st.markdown('<div style="height:0.4rem"></div>', unsafe_allow_html=True)
            yt_url = st.text_input("", placeholder="https://www.youtube.com/watch?v=...",
                                   label_visibility="collapsed")
            source = yt_url.strip() if yt_url and yt_url.strip() else None
        else:
            uploaded = st.file_uploader(
                "", type=["mp4", "mov", "avi", "mkv", "mp3", "wav", "m4a"],
                label_visibility="collapsed"
            )
            if uploaded:
                suffix = os.path.splitext(uploaded.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.read())
                    source = tmp.name
        st.markdown('</div>', unsafe_allow_html=True)

    with col_r:
        st.markdown('<div class="vm-input-panel">', unsafe_allow_html=True)
        st.markdown('<div class="vm-label">Language</div>', unsafe_allow_html=True)
        language = st.selectbox("", ["english", "hinglish"], label_visibility="collapsed")
        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
        st.markdown('<div class="vm-label">Run</div>', unsafe_allow_html=True)
        run_btn = st.button("⚡  Process Video", disabled=not source)
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.error:
        st.markdown(f'<div class="vm-error">// error<br>{st.session_state.error}</div>',
                    unsafe_allow_html=True)

    if run_btn and source:
        st.session_state.error = None
        with st.spinner("Transcribing and analysing — hang tight..."):
            try:
                from main import run_pipeline
                result = run_pipeline(source, language=language)
                st.session_state.pipeline_result = result
                st.session_state.rag_chain = result.get("rag_chain")
                st.session_state.chat_history = []
                st.session_state.page = "home"
                if input_mode == "Upload File" and source and os.path.exists(source):
                    try: os.unlink(source)
                    except: pass
                st.rerun()
            except Exception as e:
                st.session_state.error = str(e)
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME (after processing — show nav cards)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "home" and result:

    st.markdown("""
    <div class="vm-page-title">Overview</div>
    <div class="vm-page-subtitle">// select a section to explore</div>
    """, unsafe_allow_html=True)

    nav_items = [
        ("summary",    "📋", "Summary",     "A concise overview of the entire video content."),
        ("actions",    "✅", "Action Items", "Tasks and follow-ups extracted from the video."),
        ("decisions",  "🔑", "Key Decisions","Important decisions and conclusions identified."),
        ("questions",  "❓", "Open Questions","Unresolved questions raised during the video."),
        ("transcript", "📝", "Transcript",   "Full verbatim transcript with download option."),
        ("chat",       "💬", "Chat",         "Ask anything about the video using RAG."),
    ]

    row1 = st.columns(3, gap="medium")
    row2 = st.columns(3, gap="medium")

    for i, (page_id, icon, title, desc) in enumerate(nav_items):
        col = row1[i] if i < 3 else row2[i - 3]
        with col:
            st.markdown(f"""
            <div class="vm-nav-card">
                <div class="vm-nav-card-icon">{icon}</div>
                <div class="vm-nav-card-title">{title}</div>
                <div class="vm-nav-card-desc">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Open {title}", key=f"card_{page_id}"):
                go(page_id)

    st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
    if st.button("↩  Process a new video"):
        for k in ["pipeline_result", "chat_history", "rag_chain", "error"]:
            st.session_state[k] = [] if k == "chat_history" else None
        st.session_state.page = "home"
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SUMMARY
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "summary":
    st.markdown("""
    <div class="vm-page-title">Summary</div>
    <div class="vm-page-subtitle">// ai-generated overview of the video content</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="vm-card">
        <div class="vm-label">Overview</div>
        <div class="vm-body">{result.get('summary', 'No summary available.')}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("→ View Action Items"):
        go("actions")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ACTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "actions":
    st.markdown("""
    <div class="vm-page-title">Action Items</div>
    <div class="vm-page-subtitle">// tasks and follow-ups extracted from the video</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="vm-card">
        <div class="vm-label">Tasks</div>
        <div class="vm-body">{result.get('action_items', 'No action items found.')}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("→ View Key Decisions"):
        go("decisions")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DECISIONS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "decisions":
    st.markdown("""
    <div class="vm-page-title">Key Decisions</div>
    <div class="vm-page-subtitle">// important conclusions identified in the video</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="vm-card">
        <div class="vm-label">Decisions</div>
        <div class="vm-body">{result.get('key_decisions', 'No key decisions found.')}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("→ View Open Questions"):
        go("questions")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: QUESTIONS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "questions":
    st.markdown("""
    <div class="vm-page-title">Open Questions</div>
    <div class="vm-page-subtitle">// unresolved questions raised in the video</div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="vm-card">
        <div class="vm-label">Questions</div>
        <div class="vm-body">{result.get('open_questions', 'No open questions found.')}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("→ View Full Transcript"):
        go("transcript")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TRANSCRIPT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "transcript":
    st.markdown("""
    <div class="vm-page-title">Transcript</div>
    <div class="vm-page-subtitle">// full verbatim transcription</div>
    """, unsafe_allow_html=True)

    transcript_text = result.get('transcript', '')

    col_dl, col_spacer = st.columns([1, 4])
    with col_dl:
        st.download_button(
            "↓ download transcript",
            data=transcript_text,
            file_name="transcript.txt",
            mime="text/plain"
        )

    st.markdown(f"""
    <div class="vm-card" style="max-height:560px;overflow-y:auto;">
        <div class="vm-label">Full Text</div>
        <div class="vm-body" style="font-family:'Fira Code',monospace;
             font-size:0.78rem;color:#5a6478;line-height:1.9;">
            {transcript_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("→ Chat with this video"):
        go("chat")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: CHAT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "chat":
    st.markdown("""
    <div class="vm-page-title">Chat</div>
    <div class="vm-page-subtitle">// ask anything about the video — powered by RAG</div>
    """, unsafe_allow_html=True)

    # Chat history display
    if not st.session_state.chat_history:
        chat_html = """
        <div class="vm-chat-empty">
            <div>// no messages yet</div>
            <div style="font-size:0.6rem;margin-top:0.3rem;color:#14213d;">ask anything about the video below</div>
        </div>"""
    else:
        chat_html = ""
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f'<div class="vm-bubble-user"><div>{msg["content"]}</div></div>'
            else:
                chat_html += f'<div class="vm-bubble-bot"><div>{msg["content"]}</div></div>'

    st.markdown(f'<div class="vm-chat">{chat_html}</div>', unsafe_allow_html=True)

    q_col, btn_col = st.columns([5, 1], gap="small")
    with q_col:
        user_q = st.text_input("", placeholder="What were the main decisions made?",
                               key="chat_input", label_visibility="collapsed")
    with btn_col:
        ask_btn = st.button("Ask →", key="ask_btn")

    if ask_btn and user_q.strip():
        question = user_q.strip()
        st.session_state.chat_history.append({"role": "user", "content": question})

        history_str = ""
        for msg in st.session_state.chat_history[:-1]:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{prefix}: {msg['content']}\n"

        with st.spinner("thinking..."):
            try:
                from core.rag_engine import ask_question
                answer = ask_question(st.session_state.rag_chain, question, history_str)
            except Exception as e:
                answer = f"// error: {str(e)}"

        st.session_state.chat_history.append({"role": "assistant", "content": answer})
        st.rerun()

    if st.session_state.chat_history:
        col_clr, col_sp = st.columns([1, 5])
        with col_clr:
            if st.button("✕ clear"):
                st.session_state.chat_history = []
                st.rerun()