import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@300;400;500&display=swap');

/* ── Root & Global ── */
html, body, [class*="css"] {
    font-family: 'DM Mono', monospace;
}

.stApp {
    background: #0a0a0f;
    color: #e8e4d9;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1200px; }

/* ── Hero header ── */
.hero {
    text-align: center;
    padding: 3rem 0 2rem;
    position: relative;
}
.hero-tag {
    font-family: 'DM Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.3em;
    color: #ff6b2b;
    text-transform: uppercase;
    margin-bottom: 1rem;
}
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2.5rem, 6vw, 4.5rem);
    font-weight: 800;
    line-height: 1;
    color: #e8e4d9;
    margin: 0;
    letter-spacing: -0.02em;
}
.hero-title span {
    color: #ff6b2b;
}
.hero-sub {
    font-family: 'DM Mono', monospace;
    font-size: 0.8rem;
    color: #6b6760;
    margin-top: 1rem;
    letter-spacing: 0.05em;
}

/* ── Divider ── */
.rule {
    border: none;
    border-top: 1px solid #1e1e2a;
    margin: 2rem 0;
}

/* ── Input panel ── */
.input-panel {
    background: #0f0f1a;
    border: 1px solid #1e1e2a;
    border-radius: 12px;
    padding: 2rem;
    margin-bottom: 1.5rem;
}
.panel-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.65rem;
    letter-spacing: 0.25em;
    color: #ff6b2b;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}

/* ── Streamlit widget overrides ── */
.stTextInput > div > div > input,
.stSelectbox > div > div {
    background: #0a0a0f !important;
    border: 1px solid #2a2a3a !important;
    border-radius: 8px !important;
    color: #e8e4d9 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.85rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #ff6b2b !important;
    box-shadow: 0 0 0 2px rgba(255,107,43,0.15) !important;
}

.stButton > button {
    background: #ff6b2b !important;
    color: #0a0a0f !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s ease !important;
    width: 100%;
}
.stButton > button:hover {
    background: #ff8c5a !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(255,107,43,0.3) !important;
}

/* ── Radio buttons ── */
.stRadio > div {
    flex-direction: row !important;
    gap: 1rem;
}
.stRadio > div > label {
    background: #0f0f1a !important;
    border: 1px solid #1e1e2a !important;
    border-radius: 8px !important;
    padding: 0.4rem 1rem !important;
    font-size: 0.8rem !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
}
.stRadio > div > label:hover {
    border-color: #ff6b2b !important;
}

/* ── Result cards ── */
.result-card {
    background: #0f0f1a;
    border: 1px solid #1e1e2a;
    border-left: 3px solid #ff6b2b;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.result-card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: #ff6b2b;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
}
.result-card-body {
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
    color: #c8c4b9;
    line-height: 1.7;
    white-space: pre-wrap;
}
.video-title-display {
    font-family: 'Syne', sans-serif;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e8e4d9;
    line-height: 1.3;
    margin-bottom: 0.5rem;
}

/* ── Chat UI ── */
.chat-container {
    background: #0f0f1a;
    border: 1px solid #1e1e2a;
    border-radius: 12px;
    padding: 1.5rem;
    max-height: 420px;
    overflow-y: auto;
    margin-bottom: 1rem;
}
.chat-bubble-user {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.8rem;
}
.chat-bubble-user > div {
    background: #ff6b2b;
    color: #0a0a0f;
    border-radius: 16px 16px 4px 16px;
    padding: 0.6rem 1rem;
    max-width: 70%;
    font-size: 0.82rem;
    font-family: 'DM Mono', monospace;
}
.chat-bubble-bot {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 0.8rem;
}
.chat-bubble-bot > div {
    background: #1a1a28;
    color: #c8c4b9;
    border-radius: 16px 16px 16px 4px;
    padding: 0.6rem 1rem;
    max-width: 75%;
    font-size: 0.82rem;
    font-family: 'DM Mono', monospace;
    line-height: 1.6;
    border: 1px solid #2a2a3a;
}
.chat-empty {
    text-align: center;
    color: #3a3a4a;
    font-size: 0.75rem;
    letter-spacing: 0.1em;
    padding: 2rem 0;
}

/* ── Status / info ── */
.status-pill {
    display: inline-block;
    background: rgba(255,107,43,0.1);
    border: 1px solid rgba(255,107,43,0.3);
    color: #ff6b2b;
    border-radius: 20px;
    padding: 0.2rem 0.8rem;
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    font-family: 'DM Mono', monospace;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0a0a0f !important;
    border-right: 1px solid #1e1e2a !important;
}
[data-testid="stSidebar"] .stMarkdown {
    color: #6b6760 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0f0f1a !important;
    border: 1px dashed #2a2a3a !important;
    border-radius: 8px !important;
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: #ff6b2b !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    gap: 0.5rem;
    border-bottom: 1px solid #1e1e2a;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #6b6760 !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.1em !important;
    border: none !important;
    padding: 0.5rem 1.2rem !important;
}
.stTabs [aria-selected="true"] {
    color: #ff6b2b !important;
    border-bottom: 2px solid #ff6b2b !important;
}
</style>
""", unsafe_allow_html=True)


# ── Session state init ─────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "pipeline_result": None,
        "chat_history": [],       # list of {"role": "user"|"assistant", "content": str}
        "rag_chain": None,
        "processing": False,
        "error": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0;">
        <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.1rem;color:#e8e4d9;">
            🎬 AI Video Assistant
        </div>
        <div style="font-size:0.65rem;color:#3a3a4a;letter-spacing:0.1em;margin-top:0.3rem;">
            RAG-POWERED ANALYSIS
        </div>
    </div>
    <hr style="border-color:#1e1e2a;margin:0.5rem 0 1.5rem;">
    """, unsafe_allow_html=True)

    st.markdown('<div class="panel-label">How it works</div>', unsafe_allow_html=True)
    steps = [
        ("01", "Paste a YouTube URL or upload a video/audio file"),
        ("02", "Choose your language"),
        ("03", "Click Process — AI transcribes & analyses"),
        ("04", "Read the summary, decisions & action items"),
        ("05", "Chat with your video using RAG"),
    ]
    for num, text in steps:
        st.markdown(f"""
        <div style="display:flex;gap:0.8rem;margin-bottom:0.8rem;align-items:flex-start;">
            <span style="font-family:'Syne',sans-serif;font-weight:800;color:#ff6b2b;font-size:0.7rem;min-width:20px;">{num}</span>
            <span style="font-size:0.72rem;color:#6b6760;line-height:1.5;">{text}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="border-color:#1e1e2a;margin:1.5rem 0;">', unsafe_allow_html=True)

    if st.session_state.pipeline_result:
        st.markdown('<div class="panel-label">Session</div>', unsafe_allow_html=True)
        st.markdown('<span class="status-pill">✓ Video Processed</span>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="margin-top:0.8rem;font-size:0.7rem;color:#6b6760;">
            Chat messages: {len(st.session_state.chat_history) // 2 if st.session_state.chat_history else 0}
        </div>
        """, unsafe_allow_html=True)

        if st.button("🔄 Reset & New Video"):
            for key in ["pipeline_result", "chat_history", "rag_chain", "error"]:
                st.session_state[key] = None if key != "chat_history" else []
            st.rerun()

    st.markdown('<hr style="border-color:#1e1e2a;margin:1.5rem 0;">', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.65rem;color:#2a2a3a;letter-spacing:0.08em;line-height:1.8;">
        Supports YouTube URLs<br>
        MP4 · MOV · AVI · MP3 · WAV · M4A<br>
        English & Hinglish
    </div>
    """, unsafe_allow_html=True)


# ── Main content ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">RAG · Transcription · Intelligence</div>
    <h1 class="hero-title">AI Video<br><span>Assistant</span></h1>
    <p class="hero-sub">drop a video. ask anything.</p>
</div>
<hr class="rule">
""", unsafe_allow_html=True)


# ── Input Section ──────────────────────────────────────────────────────────────
if not st.session_state.pipeline_result:

    col_l, col_r = st.columns([3, 2], gap="large")

    with col_l:
        st.markdown('<div class="panel-label">Input Source</div>', unsafe_allow_html=True)
        input_mode = st.radio(
            "", ["YouTube URL", "Upload File"],
            label_visibility="collapsed",
            horizontal=True
        )

        source = None

        if input_mode == "YouTube URL":
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
            yt_url = st.text_input(
                "",
                placeholder="https://www.youtube.com/watch?v=...",
                label_visibility="collapsed"
            )
            source = yt_url.strip() if yt_url else None

        else:
            uploaded = st.file_uploader(
                "",
                type=["mp4", "mov", "avi", "mp3", "wav", "m4a"],
                label_visibility="collapsed"
            )
            if uploaded:
                # Save to temp file so your pipeline can read it
                import tempfile
                suffix = os.path.splitext(uploaded.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uploaded.read())
                    source = tmp.name

    with col_r:
        st.markdown('<div class="panel-label">Language</div>', unsafe_allow_html=True)
        language = st.selectbox(
            "",
            ["english", "hinglish"],
            label_visibility="collapsed"
        )

        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)
        st.markdown('<div class="panel-label">Ready?</div>', unsafe_allow_html=True)

        run_btn = st.button("⚡ Process Video", disabled=not source)

    # Error display
    if st.session_state.error:
        st.markdown(f"""
        <div style="background:#1a0a0a;border:1px solid #5a1a1a;border-radius:8px;
                    padding:1rem 1.25rem;margin-top:1rem;font-size:0.8rem;color:#ff6b6b;">
            ⚠️ {st.session_state.error}
        </div>
        """, unsafe_allow_html=True)

    # ── Run pipeline ──
    if run_btn and source:
        st.session_state.error = None
        with st.spinner("Transcribing & analysing your video — this may take a minute..."):
            try:
                from main import run_pipeline
                result = run_pipeline(source, language=language)
                st.session_state.pipeline_result = result
                st.session_state.rag_chain = result.get("rag_chain")
                st.session_state.chat_history = []
                st.rerun()
            except Exception as e:
                st.session_state.error = str(e)
                st.rerun()


# ── Results Section ────────────────────────────────────────────────────────────
else:
    result = st.session_state.pipeline_result

    # Title banner
    st.markdown(f"""
    <div class="video-title-display">{result.get('title', 'Untitled Video')}</div>
    <span class="status-pill">✓ Processed</span>
    <hr class="rule">
    """, unsafe_allow_html=True)

    # Two-column layout: analysis left, chat right
    col_analysis, col_chat = st.columns([1, 1], gap="large")

    # ── LEFT: Analysis tabs ──
    with col_analysis:
        st.markdown('<div class="panel-label">Analysis</div>', unsafe_allow_html=True)

        tab_sum, tab_actions, tab_decisions, tab_questions, tab_transcript = st.tabs([
            "📋 Summary", "✅ Actions", "🔑 Decisions", "❓ Questions", "📝 Transcript"
        ])

        with tab_sum:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-card-title">Summary</div>
                <div class="result-card-body">{result.get('summary', 'N/A')}</div>
            </div>
            """, unsafe_allow_html=True)

        with tab_actions:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-card-title">Action Items</div>
                <div class="result-card-body">{result.get('action_items', 'No action items found.')}</div>
            </div>
            """, unsafe_allow_html=True)

        with tab_decisions:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-card-title">Key Decisions</div>
                <div class="result-card-body">{result.get('key_decisions', 'No key decisions found.')}</div>
            </div>
            """, unsafe_allow_html=True)

        with tab_questions:
            st.markdown(f"""
            <div class="result-card">
                <div class="result-card-title">Open Questions</div>
                <div class="result-card-body">{result.get('open_questions', 'No open questions found.')}</div>
            </div>
            """, unsafe_allow_html=True)

        with tab_transcript:
            transcript_text = result.get('transcript', '')
            st.markdown(f"""
            <div class="result-card" style="max-height:350px;overflow-y:auto;">
                <div class="result-card-title">Full Transcript</div>
                <div class="result-card-body" style="font-size:0.75rem;">{transcript_text}</div>
            </div>
            """, unsafe_allow_html=True)

            # Download button
            st.download_button(
                label="⬇ Download Transcript",
                data=transcript_text,
                file_name="transcript.txt",
                mime="text/plain"
            )

    # ── RIGHT: Chat ──
    with col_chat:
        st.markdown('<div class="panel-label">Chat with your video</div>', unsafe_allow_html=True)

        # Chat history display
        chat_html = ""
        if not st.session_state.chat_history:
            chat_html = '<div class="chat-empty">Ask anything about the video ↓</div>'
        else:
            for msg in st.session_state.chat_history:
                if msg["role"] == "user":
                    chat_html += f"""
                    <div class="chat-bubble-user">
                        <div>{msg['content']}</div>
                    </div>"""
                else:
                    chat_html += f"""
                    <div class="chat-bubble-bot">
                        <div>{msg['content']}</div>
                    </div>"""

        st.markdown(f'<div class="chat-container">{chat_html}</div>', unsafe_allow_html=True)

        # Input row
        q_col, btn_col = st.columns([4, 1], gap="small")
        with q_col:
            user_q = st.text_input(
                "",
                placeholder="What were the main decisions?",
                key="chat_input",
                label_visibility="collapsed"
            )
        with btn_col:
            ask_btn = st.button("Ask →", key="ask_btn")

        # Handle question
        if ask_btn and user_q.strip():
            question = user_q.strip()
            st.session_state.chat_history.append({"role": "user", "content": question})

            # Build chat history string for your rag engine
            history_str = ""
            for msg in st.session_state.chat_history[:-1]:  # exclude current question
                prefix = "User" if msg["role"] == "user" else "Assistant"
                history_str += f"{prefix}: {msg['content']}\n"

            with st.spinner("Thinking..."):
                try:
                    from core.rag_engine import ask_question
                    answer = ask_question(
                        st.session_state.rag_chain,
                        question,
                        history_str
                    )
                except Exception as e:
                    answer = f"⚠️ Error: {str(e)}"

            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()

        # Clear chat button
        if st.session_state.chat_history:
            if st.button("🗑 Clear chat"):
                st.session_state.chat_history = []
                st.rerun()