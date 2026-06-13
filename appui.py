import streamlit as st
import gc
import os
import tempfile

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VidMind · AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@400;500;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, .stApp {
    background-color: #080D18 !important;
    color: #DDE6F5 !important;
    font-family: 'Inter', sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2.5rem 5rem !important; max-width: 1080px; }

/* ── Hero ── */
.hero {
    text-align: center;
    padding: 2.8rem 1rem 2rem;
}
.hero-eyebrow {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #3B82F6;
    margin-bottom: 0.4rem;
}
.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.5rem;
    font-weight: 700;
    background: linear-gradient(135deg, #60A5FA 0%, #A5B4FC 55%, #38BDF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.4px;
    margin-bottom: 0.45rem;
}
.hero-sub {
    font-size: 1rem;
    color: #6B84A8;
    max-width: 500px;
    margin: 0 auto;
    line-height: 1.65;
}

/* ── Divider ── */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #1B3558, transparent);
    margin: 1.25rem 0;
}

/* ── Section anchor label ── */
.section-anchor {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3B82F6;
    margin-bottom: 0.6rem;
    display: block;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0C1525 !important;
    border: 2px dashed #1B3558 !important;
    border-radius: 14px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #3B82F6 !important; }
[data-testid="stFileUploader"] label { color: #6B84A8 !important; font-size: 0.93rem !important; }

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: #0C1525 !important;
    border: 1px solid #1B3558 !important;
    border-radius: 10px !important;
    color: #DDE6F5 !important;
}

/* ── Primary button ── */
.stButton > button {
    background: linear-gradient(135deg, #1D4ED8, #3B82F6) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.8rem !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.93rem !important;
    width: 100% !important;
    box-shadow: 0 4px 16px #3B82F638 !important;
    transition: all 0.18s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1E40AF, #2563EB) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 22px #3B82F658 !important;
}

/* ── Nav pill bar ── */
.nav-bar {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    background: #0C1525;
    border: 1px solid #1B3558;
    border-radius: 14px;
    padding: 0.4rem 0.5rem;
    margin-bottom: 1.75rem;
}
.nav-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: transparent;
    color: #6B84A8;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.84rem;
    font-weight: 500;
    padding: 0.42rem 0.95rem;
    border-radius: 9px;
    text-decoration: none !important;
    transition: all 0.15s;
    cursor: pointer;
    border: none;
    white-space: nowrap;
}
.nav-pill:hover {
    background: #152038;
    color: #93C5FD;
    text-decoration: none !important;
}

/* ── Result card ── */
.result-card {
    background: #0C1525;
    border: 1px solid #1B3558;
    border-radius: 14px;
    padding: 1.4rem 1.65rem;
    margin-bottom: 1.2rem;
    scroll-margin-top: 80px;
}
.result-card-header {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-bottom: 0.85rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid #152038;
}
.result-card-icon { font-size: 1.1rem; }
.result-card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #60A5FA;
}
.result-card-body {
    color: #B8CCEB;
    font-size: 0.95rem;
    line-height: 1.78;
    white-space: pre-wrap;
}

/* ── Video title badge ── */
.title-badge {
    background: linear-gradient(135deg, #0F2040, #0C1A30);
    border: 1px solid #2563EB;
    border-radius: 12px;
    padding: 1rem 1.65rem;
    margin-bottom: 1.4rem;
}
.title-badge-label {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #3B82F6;
    margin-bottom: 0.3rem;
}
.title-badge-text {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #93C5FD;
    line-height: 1.35;
}

/* ── Two-col grid ── */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 700px) { .two-col { grid-template-columns: 1fr; } }

/* ── Transcript box ── */
.transcript-box {
    background: #080D18;
    border: 1px solid #152038;
    border-radius: 10px;
    padding: 1.1rem 1.3rem;
    max-height: 320px;
    overflow-y: auto;
    font-size: 0.9rem;
    color: #8FA5C8;
    line-height: 1.75;
    white-space: pre-wrap;
    scrollbar-width: thin;
    scrollbar-color: #1B3558 transparent;
}

/* ── Chat bubbles ── */
.chat-scroll {
    max-height: 420px;
    overflow-y: auto;
    padding-right: 0.4rem;
    scrollbar-width: thin;
    scrollbar-color: #1B3558 transparent;
    margin-bottom: 1rem;
}
.bubble-user {
    background: linear-gradient(135deg, #1D4ED815, #3B82F60D);
    border: 1px solid #2563EB44;
    border-radius: 14px 14px 4px 14px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.65rem;
    color: #BFDBFE;
    font-size: 0.93rem;
    line-height: 1.55;
    text-align: right;
}
.bubble-ai {
    background: #0F1E33;
    border: 1px solid #1B3558;
    border-radius: 14px 14px 14px 4px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.65rem;
    color: #CBD8EF;
    font-size: 0.93rem;
    line-height: 1.6;
}
.bubble-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    margin-bottom: 0.28rem;
}
.bubble-user .bubble-label { color: #3B82F6; }
.bubble-ai .bubble-label { color: #60A5FA; }

/* ── Chat input ── */
[data-testid="stChatInput"] textarea {
    background: #0C1525 !important;
    color: #DDE6F5 !important;
    border: 1px solid #1B3558 !important;
    border-radius: 10px !important;
    font-size: 0.93rem !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #0C1525 !important;
    color: #60A5FA !important;
    border: 1px solid #1B3558 !important;
    border-radius: 9px !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 1rem !important;
    width: auto !important;
    box-shadow: none !important;
}
[data-testid="stDownloadButton"] button:hover {
    border-color: #3B82F6 !important;
    color: #93C5FD !important;
    transform: none !important;
}

/* ── Step tracker ── */
.step-row {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.87rem;
    color: #6B84A8;
    padding: 0.28rem 0;
}
.step-dot-active {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #3B82F6;
    box-shadow: 0 0 7px #3B82F6;
    flex-shrink: 0;
}
.step-dot-inactive {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #1B3558;
    flex-shrink: 0;
}
.step-active { color: #93C5FD; }

/* ── File info pill ── */
.file-pill {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.6rem 1rem;
    background: #0C1525;
    border: 1px solid #1B3558;
    border-radius: 9px;
    margin-bottom: 0.9rem;
    font-size: 0.87rem;
    color: #6B84A8;
}
.file-pill-name { color: #93C5FD; font-weight: 500; }
.file-pill-size { margin-left: auto; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1B3558; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #2563EB; }

/* ── Alert ── */
[data-testid="stAlert"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def result_card(anchor_id: str, icon: str, title: str, body: str):
    st.markdown(f"""
    <div class="result-card" id="{anchor_id}">
        <div class="result-card-header">
            <span class="result-card-icon">{icon}</span>
            <span class="result-card-title">{title}</span>
        </div>
        <div class="result-card-body">{body}</div>
    </div>
    """, unsafe_allow_html=True)


def chat_bubble(role: str, text: str):
    if role == "user":
        st.markdown(f'<div class="bubble-user"><div class="bubble-label">You</div>{text}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="bubble-ai"><div class="bubble-label">VidMind</div>{text}</div>',
                    unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {"pipeline_result": None, "chat_history_text": "",
              "chat_messages": [], "processing": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-eyebrow">AI Video Assistant</div>
    <div class="hero-title">VidMind</div>
    <div class="hero-sub">Drop in any video or audio. Walk away with deep insights.</div>
</div>
<div class="divider"></div>
""", unsafe_allow_html=True)


# ── Upload row ────────────────────────────────────────────────────────────────
col_up, col_lang = st.columns([3, 1], gap="large")

with col_up:
    st.markdown('<span class="section-anchor">Audio / Video File</span>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "file",
        type=["mp3", "mp4", "wav", "m4a", "flac", "webm", "mkv", "avi", "mov"],
        label_visibility="collapsed",
    )

with col_lang:
    st.markdown('<span class="section-anchor">Language</span>', unsafe_allow_html=True)
    language = st.selectbox(
        "lang",
        options=["english", "hinglish"],
        format_func=lambda x: "English" if x == "english" else "Hinglish",
        label_visibility="collapsed",
    )

st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

if uploaded_file:
    st.markdown(f"""
    <div class="file-pill">
        <span>📎</span>
        <span class="file-pill-name">{uploaded_file.name}</span>
        <span class="file-pill-size">{uploaded_file.size / 1_000_000:.1f} MB</span>
    </div>
    """, unsafe_allow_html=True)

    run_btn = st.button("⚡  Analyse", use_container_width=True)

    if run_btn and not st.session_state.processing:
        st.session_state.processing = True
        st.session_state.pipeline_result = None
        st.session_state.chat_messages = []
        st.session_state.chat_history_text = ""

        suffix = os.path.splitext(uploaded_file.name)[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        try:
            from utils.audio_processor import process_audio
            from core.transcriber import transcribe_full
            from core.summarizer import summarize, generate_title
            from core.extractor import extract_action_items, extract_key_decisions, extract_questions
            from core.rag_engine import build_rag_chain

            status = st.empty()
            steps = [
                ("🎵", "Converting & chunking audio"),
                ("🗣️", "Transcribing speech"),
                ("📝", "Generating summary"),
                ("✅", "Extracting action items"),
                ("⚖️", "Identifying key decisions"),
                ("❓", "Finding open questions"),
                ("🔍", "Building Q&A index"),
            ]

            def show_step(active: int):
                rows = ""
                for i, (ic, lb) in enumerate(steps):
                    dot = "step-dot-active" if i == active else "step-dot-inactive"
                    cls = "step-active" if i == active else ""
                    rows += f'<div class="step-row {cls}"><div class="{dot}"></div>{ic} {lb}{"…" if i == active else ""}</div>'
                status.markdown(
                    f'<div class="result-card" style="margin-bottom:0">'
                    f'<div class="result-card-header"><span class="result-card-title">Processing</span></div>'
                    f'{rows}</div>',
                    unsafe_allow_html=True
                )

            show_step(0); chunks = process_audio(tmp_path)
            show_step(1); transcript = transcribe_full(chunks, language=language); gc.collect()
            show_step(2); title = generate_title(transcript); summary = summarize(transcript)
            show_step(3); action_items = extract_action_items(transcript)
            show_step(4); decisions = extract_key_decisions(transcript)
            show_step(5); questions = extract_questions(transcript)
            show_step(6); rag_chain = build_rag_chain(transcript); gc.collect()

            status.empty()

            st.session_state.pipeline_result = {
                "title": title, "transcript": transcript, "summary": summary,
                "action_items": action_items, "key_decisions": decisions,
                "open_questions": questions, "rag_chain": rag_chain,
            }

        except Exception as e:
            st.error(f"**Processing failed:** {e}")
        finally:
            st.session_state.processing = False
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
result = st.session_state.pipeline_result

if result:
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Title badge
    st.markdown(f"""
    <div class="title-badge">
        <div class="title-badge-label">Detected Title</div>
        <div class="title-badge-text">📌 {result['title']}</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Nav pill bar (anchor links) ───────────────────────────────────────────
    st.markdown("""
    <div class="nav-bar">
        <a class="nav-pill" href="#sec-summary">🧠 Summary</a>
        <a class="nav-pill" href="#sec-actions">✅ Action Items</a>
        <a class="nav-pill" href="#sec-decisions">⚖️ Key Decisions</a>
        <a class="nav-pill" href="#sec-questions">❓ Open Questions</a>
        <a class="nav-pill" href="#sec-transcript">📄 Transcript</a>
        <a class="nav-pill" href="#sec-chat">💬 Chat</a>
    </div>
    """, unsafe_allow_html=True)

    # ── Summary ───────────────────────────────────────────────────────────────
    result_card("sec-summary", "🧠", "Summary", result["summary"])

    # ── Action Items + Key Decisions (side by side) ───────────────────────────
    col_a, col_b = st.columns(2, gap="medium")
    with col_a:
        result_card("sec-actions", "✅", "Action Items", result["action_items"])
    with col_b:
        result_card("sec-decisions", "⚖️", "Key Decisions", result["key_decisions"])

    # ── Open Questions ────────────────────────────────────────────────────────
    result_card("sec-questions", "❓", "Open Questions", result["open_questions"])

    # ── Transcript ────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="result-card" id="sec-transcript">
        <div class="result-card-header">
            <span class="result-card-icon">📄</span>
            <span class="result-card-title">Full Transcript</span>
        </div>
    """, unsafe_allow_html=True)
    st.markdown(f'<div class="transcript-box">{result["transcript"]}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button(
        label="⬇  Download transcript (.txt)",
        data=result["transcript"],
        file_name="transcript.txt",
        mime="text/plain",
    )

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    # ── Chat ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="result-card" id="sec-chat">
        <div class="result-card-header">
            <span class="result-card-icon">💬</span>
            <span class="result-card-title">Ask Anything</span>
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.chat_messages:
        st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
        for msg in st.session_state.chat_messages:
            chat_bubble(msg["role"], msg["content"])
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center;padding:1.5rem 1rem;color:#364D6B;font-size:0.88rem;">
            Ask anything about the content — themes, quotes, takeaways, timelines…
        </div>""", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    user_q = st.chat_input("Ask about this video or audio…")
    if user_q:
        from core.rag_engine import ask_question
        st.session_state.chat_messages.append({"role": "user", "content": user_q})
        with st.spinner("Thinking…"):
            ans = ask_question(result["rag_chain"], user_q, st.session_state.chat_history_text)
        st.session_state.chat_messages.append({"role": "assistant", "content": ans})
        st.session_state.chat_history_text += f"User: {user_q}\nAssistant: {ans}\n"
        st.rerun()

    if st.session_state.chat_messages:
        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            if st.button("🗑  Clear chat"):
                st.session_state.chat_messages = []
                st.session_state.chat_history_text = ""
                st.rerun()

elif not uploaded_file:
    st.markdown("""
    <div style="text-align:center;padding:3.5rem 1rem 2rem;color:#2A3D5A;">
        <div style="font-size:2.5rem;margin-bottom:0.7rem;opacity:0.45;">🎬</div>
        <div style="font-size:0.92rem;color:#3D5578;line-height:1.75;">
            Upload a file above to get started.<br>
            <span style="font-size:0.82rem;color:#283C55;">MP3 · MP4 · WAV · M4A · FLAC · WEBM · MKV · AVI · MOV</span>
        </div>
    </div>
    """, unsafe_allow_html=True)