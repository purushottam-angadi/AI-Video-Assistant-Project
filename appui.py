
import streamlit as st
import gc
import os
import shutil
import tempfile
import re

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VideoMind",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def clean_llm_text(text: str) -> str:
    """Strip markdown symbols so output renders as clean plain text."""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"\*(.*?)\*", r"\1", text)
    text = re.sub(r"`{1,3}(.*?)`{1,3}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"^[-•*]\s+", "• ", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_speaking_time(word_count: int) -> str:
    """Rough spoken-word estimate at ~150 wpm."""
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
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

:root {
    --bg:        #0A0B0E;
    --panel:     #121317;
    --panel-alt: #16171C;
    --border:    #22242B;
    --border-hi: #2E313B;
    --text:      #E7E8EA;
    --text-dim:  #A0A3AC;
    --text-mute: #63666F;
    --accent:    #4C6EF5;
    --accent-dim:#2B3A75;
    --ok:        #3FA66C;
    --warn:      #C9922B;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg);
    color: var(--text);
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2.2rem 2.5rem 4rem; max-width: 1120px; margin: 0 auto; }

/* ── Hero ── */
.hero {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.4rem 0 1.6rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.8rem;
}
.hero-left { display: flex; align-items: center; gap: 0.85rem; }
.hero-mark {
    width: 40px; height: 40px;
    border-radius: 9px;
    background: var(--panel);
    border: 1px solid var(--border-hi);
    display: flex; align-items: center; justify-content: center;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    color: var(--accent);
    font-size: 1.05rem;
}
.hero h1 {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.35rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--text);
    margin: 0;
    line-height: 1.2;
}
.hero p { color: var(--text-mute); font-size: 0.82rem; margin: 0.1rem 0 0; }
.hero-tag {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-mute);
    border: 1px solid var(--border-hi);
    border-radius: 100px;
    padding: 0.32rem 0.8rem;
}

/* ── Intro copy ── */
.intro {
    max-width: 640px;
    color: var(--text-dim);
    font-size: 0.95rem;
    line-height: 1.7;
    margin: 0 0 2rem;
}

/* ── How it works (timeline, not boxes) ── */
.how-it-works {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 2.2rem;
    margin-bottom: 2.2rem;
}
.step { border-top: 2px solid var(--border-hi); padding-top: 0.9rem; }
.step-num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    color: var(--accent);
    margin-bottom: 0.45rem;
}
.step-title {
    font-family: 'IBM Plex Sans', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text);
    margin-bottom: 0.3rem;
}
.step-desc {
    font-size: 0.82rem;
    color: var(--text-mute);
    line-height: 1.6;
}
@media (max-width: 900px) {
    .how-it-works { grid-template-columns: 1fr; gap: 1.4rem; }
}

/* ── Input card ── */
.input-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem 1.7rem 1.3rem;
    margin-bottom: 1.6rem;
}

/* ── Section label ── */
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-mute);
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-label::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--border);
}

/* ── Video title row ── */
.title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    margin-bottom: 1.2rem;
    flex-wrap: wrap;
}
.title-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.6rem;
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.15rem;
    font-weight: 600;
    color: var(--text);
}
.title-badge .dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--ok);
    box-shadow: 0 0 0 3px rgba(63,166,108,0.15);
}
.status-chip {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ok);
    background: rgba(63,166,108,0.08);
    border: 1px solid rgba(63,166,108,0.28);
    border-radius: 100px;
    padding: 0.28rem 0.75rem;
}

/* ── Metrics bar ── */
.metrics-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.9rem;
    margin-bottom: 1.4rem;
}
.metric-tile {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.85rem 1rem;
}
.metric-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-mute);
    margin-bottom: 0.35rem;
}
.metric-value {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
}

/* ── Result cards ── */
.result-card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-left: 3px solid var(--border-hi);
    border-radius: 10px;
    padding: 1.15rem 1.3rem;
    margin-bottom: 1rem;
    height: 100%;
    transition: border-color 0.15s;
}
.result-card:hover { border-color: var(--border-hi); }
.result-card.accent-blue  { border-left-color: var(--accent); }
.result-card.accent-green { border-left-color: var(--ok); }
.result-card.accent-amber { border-left-color: var(--warn); }

.card-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.card-count {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.68rem;
    color: var(--text-mute);
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0.05rem 0.45rem;
}
.card-body {
    font-size: 0.875rem;
    line-height: 1.7;
    color: var(--text-dim);
}
.card-body ul { padding-left: 1.1rem; margin: 0; }
.card-body li { margin-bottom: 0.4rem; }

/* ── Divider ── */
.soft-divider { border: none; border-top: 1px solid var(--border); margin: 1.8rem 0; }

/* ── Chat container ── */
.chat-wrap {
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    min-height: 80px;
    max-height: 480px;
    overflow-y: auto;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
}

.bubble-row-user { display: flex; justify-content: flex-end; }
.bubble-user {
    background: var(--accent-dim);
    border: 1px solid #38428A;
    border-radius: 12px 12px 2px 12px;
    padding: 0.65rem 1rem;
    max-width: 68%;
    font-size: 0.875rem;
    color: #DCE2FF;
    line-height: 1.55;
    word-wrap: break-word;
}

.bubble-row-bot { display: flex; justify-content: flex-start; flex-direction: column; gap: 0.3rem; }
.source-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.64rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--text-mute);
    padding: 0.18rem 0.6rem;
    border-radius: 6px;
    background: var(--panel);
    border: 1px solid var(--border);
    display: inline-block;
}
.bubble-bot {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 2px 12px 12px 12px;
    padding: 0.75rem 1.1rem;
    max-width: 78%;
    font-size: 0.875rem;
    color: var(--text-dim);
    line-height: 1.7;
    word-wrap: break-word;
    white-space: pre-wrap;
}

/* ── Suggested prompts ── */
.suggest-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.9rem; }
.suggest-chip {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--text-dim);
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 0.4rem 0.9rem;
}

/* ── Streamlit overrides ── */
.stTextInput > div > div > input,
.stTextArea textarea {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(76,110,245,0.14) !important;
}
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.3rem !important;
    letter-spacing: 0.01em !important;
    transition: background 0.15s, transform 0.1s !important;
}
.stButton > button:hover { background: #3F5EDB !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0) !important; }

.stSelectbox > div > div {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}

[data-testid="stFileUploader"] {
    background: var(--bg) !important;
    border: 1.5px dashed var(--border-hi) !important;
    border-radius: 10px !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--accent) !important; }

.file-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    font-size: 0.8rem;
    color: var(--text-dim);
    margin-top: 0.5rem;
}
.file-chip .fname { color: var(--accent); font-weight: 600; }
.file-chip .ftype {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.66rem;
    color: var(--text-mute);
    background: var(--panel-alt);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.05rem 0.4rem;
    text-transform: uppercase;
}

.stSpinner > div { color: var(--accent) !important; }

.streamlit-expanderHeader {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text-dim) !important;
    font-size: 0.85rem !important;
}

.chat-empty {
    text-align: center;
    color: var(--text-mute);
    font-size: 0.85rem;
    padding: 1.5rem 0;
}

@media (max-width: 900px) {
    .metrics-row { grid-template-columns: repeat(2, 1fr); }
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────
defaults = {
    "pipeline_result": None,
    "chat_history_str": "",
    "chat_display": [],
    "pipeline_ran": False,
    "upload_meta": None,
    "retriever": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-left">
        <div class="hero-mark">VM</div>
        <div>
            <h1>VideoMind</h1>
            <p>Transcription, summarisation and Q&A for video and audio</p>
        </div>
    </div>
    <div class="hero-tag">Local processing</div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<p class="intro">
    Drop in a recorded meeting, lecture, interview or podcast and VideoMind turns it into a
    transcript, a summary, and a running list of action items, decisions and open questions —
    then lets you ask follow-up questions directly against the recording.
</p>
""", unsafe_allow_html=True)

st.markdown("""
<div class="how-it-works">
    <div class="step">
        <div class="step-num">01 · UPLOAD</div>
        <div class="step-title">Add a recording</div>
        <div class="step-desc">Drop in a video or audio file up to a couple of hours long, in English or Hinglish.</div>
    </div>
    <div class="step">
        <div class="step-num">02 · ANALYSE</div>
        <div class="step-title">Automatic breakdown</div>
        <div class="step-desc">VideoMind transcribes the recording and extracts a summary, action items and decisions.</div>
    </div>
    <div class="step">
        <div class="step-num">03 · ASK</div>
        <div class="step-title">Chat with the content</div>
        <div class="step-desc">Ask follow-up questions and get answers grounded in the transcript, with sources cited.</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Input card — File upload only
# ─────────────────────────────────────────────
ALLOWED_EXT = ["mp4","mkv","mov","avi","webm","flv","mp3","wav","m4a","ogg","flac","aac"]
AUDIO_EXT = {"mp3","wav","m4a","ogg","flac","aac"}

source        = ""
uploaded_path = None
language      = "english"

st.markdown('<div class="input-card">', unsafe_allow_html=True)
st.markdown('<div class="section-label">Upload file</div>', unsafe_allow_html=True)

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
        st.markdown(
            f'<div class="file-chip">'
            f'<span class="fname">{uploaded.name}</span>'
            f'&nbsp;·&nbsp;{fmt_size(uploaded.size)}'
            f'&nbsp;<span class="ftype">{kind} · {ext}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
with c2:
    language = st.selectbox("Language", ["english", "hinglish"],
                            key="lang_file", label_visibility="collapsed")
with c3:
    st.markdown("<br>", unsafe_allow_html=True)
    run_file = st.button("Analyse →", key="run_file", use_container_width=True)

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

st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Pipeline — lazy import via main.py
# All heavy imports live inside run_pipeline() in main.py, so nothing
# from core/ or utils/ loads at startup — only when Analyse is clicked.
# ─────────────────────────────────────────────
if source:
    if st.session_state.retriever is not None:
        st.session_state.retriever = None
        gc.collect()

    st.session_state.chat_history_str = ""
    st.session_state.chat_display     = []
    st.session_state.pipeline_ran     = False

    with st.spinner("Analysing… this may take a minute for long videos"):
        try:
            from main import run_pipeline          # lazy — nothing loads until here
            result = run_pipeline(source, language)
            st.session_state.pipeline_result = result
            st.session_state.pipeline_ran    = True
            st.session_state.retriever       = result["retriever"]
        except Exception as e:
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

    st.markdown(f"""
    <div class="title-row">
        <div class="title-badge"><span class="dot"></span>{res["title"]}</div>
        <div class="status-chip">Analysis complete</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="metrics-row">
        <div class="metric-tile">
            <div class="metric-label">Source</div>
            <div class="metric-value">{meta.get('kind','—')}</div>
        </div>
        <div class="metric-tile">
            <div class="metric-label">Format</div>
            <div class="metric-value">{meta.get('ext','—')}</div>
        </div>
        <div class="metric-tile">
            <div class="metric-label">File size</div>
            <div class="metric-value">{meta.get('size','—')}</div>
        </div>
        <div class="metric-tile">
            <div class="metric-label">Transcript words</div>
            <div class="metric-value">{word_count:,}</div>
        </div>
        <div class="metric-tile">
            <div class="metric-label">Est. spoken length</div>
            <div class="metric-value">{estimate_speaking_time(word_count)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    summary_clean = clean_llm_text(res["summary"])
    st.markdown(f"""
    <div class="result-card accent-blue">
        <div class="card-title">Summary</div>
        <div class="card-body">{summary_clean}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")

    def _bullet_card(title, content, count, accent_class):
        lines = [l.lstrip("•-– *").strip() for l in clean_llm_text(content).split("\n") if l.strip()]
        items = "".join(f"<li>{l}</li>" for l in lines) if lines else "<li>None found</li>"
        return f"""
        <div class="result-card {accent_class}">
            <div class="card-title">{title}<span class="card-count">{count}</span></div>
            <div class="card-body"><ul>{items}</ul></div>
        </div>"""

    with col1:
        st.markdown(_bullet_card("Action items", res["action_items"], n_actions, "accent-green"), unsafe_allow_html=True)
    with col2:
        st.markdown(_bullet_card("Key decisions", res["key_decisions"], n_decisions, "accent-blue"), unsafe_allow_html=True)
    with col3:
        st.markdown(_bullet_card("Open questions", res["open_questions"], n_questions, "accent-amber"), unsafe_allow_html=True)

    with st.expander("Raw transcript"):
        st.text_area("t", label_visibility="collapsed",
                     value=res["transcript"], height=200)

    st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # Chat
    # ─────────────────────────────────────────────
    st.markdown('<div class="section-label">Chat with your video</div>', unsafe_allow_html=True)

    if not st.session_state.chat_display:
        st.markdown("""
        <div class="suggest-row">
            <div class="suggest-chip">Summarise the key takeaways</div>
            <div class="suggest-chip">What decisions were made?</div>
            <div class="suggest-chip">List any deadlines mentioned</div>
        </div>
        """, unsafe_allow_html=True)

    chat_html = ""
    for turn in st.session_state.chat_display:
        bot_text = turn["bot"].replace("<", "&lt;").replace(">", "&gt;")
        chat_html += f"""
        <div class="bubble-row-user">
            <div class="bubble-user">{turn["user"]}</div>
        </div>
        <div class="bubble-row-bot">
            <span class="source-badge">Transcript</span>
            <div class="bubble-bot">{bot_text}</div>
        </div>"""

    if not chat_html:
        chat_html = '<div class="chat-empty">Ask anything about the video above ↑</div>'

    st.markdown(f'<div class="chat-wrap">{chat_html}</div>', unsafe_allow_html=True)

    q_col, btn_col = st.columns([6, 1], gap="small")
    with q_col:
        user_q = st.text_input("q", label_visibility="collapsed",
                               placeholder="What were the main points discussed?",
                               key="chat_input")
    with btn_col:
        st.markdown("<br>", unsafe_allow_html=True)
        send = st.button("Send →", key="send_btn", use_container_width=True)

    if send and user_q.strip():
        if st.session_state.retriever is None:
            st.warning("Upload and analyse a video first.")
        else:
            from core.rag_engine import main_graph

            with st.spinner("Thinking…"):
                state = {
                    "question": user_q.strip(),
                    "chat_history": st.session_state.chat_history_str,
                    "retriever": st.session_state.retriever,
                }
                output = main_graph.invoke(state)
                raw_answer = output.get("answer", "")

            clean_answer = re.sub(r"^[🌐📎🎬]\s*\[.*?\]\s*\n?", "", raw_answer).strip()
            clean_answer = clean_llm_text(clean_answer)

            st.session_state.chat_history_str += f"User: {user_q}\nAssistant: {clean_answer}\n"
            st.session_state.chat_display.append({
                "user": user_q,
                "bot": clean_answer,
            })
            st.rerun()