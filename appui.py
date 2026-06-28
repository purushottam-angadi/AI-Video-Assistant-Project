import streamlit as st
import gc
import os
import tempfile
import re

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VideoMind",
    page_icon="🎬",
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


# ─────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Space+Grotesk:wght@500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0D0F14;
    color: #E2E4EA;
}

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 2rem 2.5rem 4rem; max-width: 1100px; margin: 0 auto; }

/* ── Hero ── */
.hero { text-align: center; padding: 2.5rem 0 1.8rem; }
.hero h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.8rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #7B7FFF 0%, #B06EFF 60%, #FF6EB4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.4rem;
}
.hero p { color: #555A70; font-size: 0.95rem; margin: 0; }

/* ── Input card ── */
.input-card {
    background: #13161F;
    border: 1px solid #1E2230;
    border-radius: 18px;
    padding: 1.6rem 1.8rem 1.2rem;
    margin-bottom: 1.8rem;
}

/* ── Section label ── */
.section-label {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #3D4255;
    margin-bottom: 0.75rem;
}

/* ── Video title badge ── */
.title-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1.4rem;
    flex-wrap: wrap;
}
.title-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: linear-gradient(135deg, #1A1730, #1A2235);
    border: 1px solid #322D5C;
    border-radius: 100px;
    padding: 0.5rem 1.2rem;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: #C084FC;
}

/* ── Result cards ── */
.result-card {
    background: #13161F;
    border: 1px solid #1E2230;
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
    height: 100%;
    transition: border-color 0.18s, box-shadow 0.18s;
}
.result-card:hover {
    border-color: #35395A;
    box-shadow: 0 4px 24px rgba(123,127,255,0.06);
}
.card-icon { font-size: 1.1rem; margin-bottom: 0.5rem; }
.card-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7B7FFF;
    margin-bottom: 0.75rem;
}
.card-body {
    font-size: 0.875rem;
    line-height: 1.7;
    color: #9DA3BC;
}
.card-body ul { padding-left: 1.1rem; margin: 0; }
.card-body li { margin-bottom: 0.35rem; }

/* ── Divider ── */
.soft-divider { border: none; border-top: 1px solid #181B26; margin: 1.8rem 0; }

/* ── Chat container ── */
.chat-wrap {
    background: #0F111A;
    border: 1px solid #1A1D2B;
    border-radius: 16px;
    padding: 1.2rem 1.4rem;
    min-height: 80px;
    max-height: 520px;
    overflow-y: auto;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
}

.bubble-row-user { display: flex; justify-content: flex-end; }
.bubble-user {
    background: linear-gradient(135deg, #2A2060, #1E2A50);
    border: 1px solid #3B3275;
    border-radius: 18px 18px 4px 18px;
    padding: 0.65rem 1rem;
    max-width: 68%;
    font-size: 0.875rem;
    color: #D8D0FF;
    line-height: 1.55;
    word-wrap: break-word;
}

.bubble-row-bot { display: flex; justify-content: flex-start; flex-direction: column; gap: 0.3rem; }
.source-badge {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    padding: 0.18rem 0.6rem;
    border-radius: 100px;
    display: inline-block;
    margin-left: 0.3rem;
}
.src-transcript { background: #1A1A3A; color: #7B7FFF; border: 1px solid #2E2A60; }
.bubble-bot {
    background: #13161F;
    border: 1px solid #1E2230;
    border-radius: 4px 18px 18px 18px;
    padding: 0.75rem 1.1rem;
    max-width: 78%;
    font-size: 0.875rem;
    color: #B0B6CC;
    line-height: 1.7;
    word-wrap: break-word;
    white-space: pre-wrap;
}

/* ── Streamlit overrides ── */
.stTextInput > div > div > input,
.stTextArea textarea {
    background: #0D0F14 !important;
    border: 1px solid #1E2230 !important;
    border-radius: 10px !important;
    color: #E2E4EA !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
}
.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
    border-color: #7B7FFF !important;
    box-shadow: 0 0 0 3px rgba(123,127,255,0.12) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #6366F1, #A855F7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.3rem !important;
    letter-spacing: 0.03em !important;
    transition: opacity 0.15s, transform 0.1s !important;
}
.stButton > button:hover { opacity: 0.88 !important; transform: translateY(-1px) !important; }
.stButton > button:active { transform: translateY(0) !important; }

.stSelectbox > div > div {
    background: #0D0F14 !important;
    border: 1px solid #1E2230 !important;
    border-radius: 10px !important;
    color: #E2E4EA !important;
}

[data-testid="stFileUploader"] {
    background: #0D0F14 !important;
    border: 1.5px dashed #252838 !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"]:hover { border-color: #6366F1 !important; }

.file-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #13161F;
    border: 1px solid #252838;
    border-radius: 8px;
    padding: 0.35rem 0.8rem;
    font-size: 0.8rem;
    color: #9DA3BC;
    margin-top: 0.5rem;
}
.file-chip .fname { color: #818CF8; font-weight: 600; }

.stSpinner > div { color: #7B7FFF !important; }

.streamlit-expanderHeader {
    background: #13161F !important;
    border: 1px solid #1E2230 !important;
    border-radius: 10px !important;
    color: #9DA3BC !important;
    font-size: 0.85rem !important;
}

.chat-empty {
    text-align: center;
    color: #2D3147;
    font-size: 0.85rem;
    padding: 1.5rem 0;
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
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>VideoMind</h1>
    <p>Transcribe · Summarise · Chat with any video or audio</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Input card — File upload only
# ─────────────────────────────────────────────
ALLOWED_EXT = ["mp4","mkv","mov","avi","webm","flv","mp3","wav","m4a","ogg","flac","aac"]

source        = ""
uploaded_path = None
language      = "english"

st.markdown('<div class="input-card">', unsafe_allow_html=True)
st.markdown('<div class="section-label">Upload File</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns([4, 1, 1], gap="medium")
with c1:
    uploaded = st.file_uploader(
        "upload", label_visibility="collapsed",
        type=ALLOWED_EXT,
        help="Video: MP4 MKV MOV AVI WebM FLV  ·  Audio: MP3 WAV M4A OGG FLAC AAC",
        key="file_upload",
    )
    if uploaded:
        st.markdown(
            f'<div class="file-chip">📄 <span class="fname">{uploaded.name}</span>'
            f'&nbsp;·&nbsp;{uploaded.size/1_048_576:.1f} MB</div>',
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
        tmp.write(uploaded.read())
        tmp.flush(); tmp.close()
        uploaded_path = tmp.name
        source        = uploaded_path

st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────
def run_pipeline_cached(source: str, language: str) -> dict:
    from dotenv import load_dotenv
    load_dotenv()
    from utils.audio_processor import process_audio
    from core.transcriber import transcribe_full
    from core.summarizer import summarize, generate_title
    from core.extractor import extract_action_items, extract_key_decisions, extract_questions
    from core.rag_engine import get_pipeline_retriever
    from core.vector_store import build_vector_store

    chunks     = process_audio(source)
    transcript = transcribe_full(chunks, language=language)

    gc.collect()
    title     = generate_title(transcript)
    summary   = summarize(transcript)
    actions   = extract_action_items(transcript)
    decisions = extract_key_decisions(transcript)
    questions = extract_questions(transcript)
    gc.collect()
    build_vector_store(transcript)
    get_pipeline_retriever()

    return {
        "title": title, "transcript": transcript,
        "summary": summary, "action_items": actions,
        "key_decisions": decisions, "open_questions": questions,
    }


if source:
    st.session_state.chat_history_str = ""
    st.session_state.chat_display     = []
    st.session_state.pipeline_ran     = False

    with st.spinner("Analysing… this may take a minute for long videos"):
        try:
            result = run_pipeline_cached(source, language)
            st.session_state.pipeline_result = result
            st.session_state.pipeline_ran    = True
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

    st.markdown(f"""
    <div class="title-row">
        <div class="title-badge">🎬 {res["title"]}</div>
    </div>
    """, unsafe_allow_html=True)

    summary_clean = clean_llm_text(res["summary"])
    st.markdown(f"""
    <div class="result-card">
        <div class="card-icon">📋</div>
        <div class="card-title">Summary</div>
        <div class="card-body">{summary_clean}</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")

    def _bullet_card(icon, title, content):
        lines = [l.lstrip("•-– *").strip() for l in clean_llm_text(content).split("\n") if l.strip()]
        items = "".join(f"<li>{l}</li>" for l in lines) if lines else "<li>None found</li>"
        return f"""
        <div class="result-card">
            <div class="card-icon">{icon}</div>
            <div class="card-title">{title}</div>
            <div class="card-body"><ul>{items}</ul></div>
        </div>"""

    with col1:
        st.markdown(_bullet_card("✅", "Action Items", res["action_items"]), unsafe_allow_html=True)
    with col2:
        st.markdown(_bullet_card("🔑", "Key Decisions", res["key_decisions"]), unsafe_allow_html=True)
    with col3:
        st.markdown(_bullet_card("❓", "Open Questions", res["open_questions"]), unsafe_allow_html=True)

    with st.expander("📄 Raw transcript"):
        st.text_area("t", label_visibility="collapsed",
                     value=res["transcript"], height=200)

    st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

    # ─────────────────────────────────────────────
    # Chat
    # ─────────────────────────────────────────────
    st.markdown('<div class="section-label">Chat with your video</div>', unsafe_allow_html=True)

    chat_html = ""
    for turn in st.session_state.chat_display:
        bot_text = turn["bot"].replace("<", "&lt;").replace(">", "&gt;")
        chat_html += f"""
        <div class="bubble-row-user">
            <div class="bubble-user">{turn["user"]}</div>
        </div>
        <div class="bubble-row-bot">
            <span class="source-badge src-transcript">🎬 Transcript</span>
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
        from core.rag_engine import main_graph

        with st.spinner("Thinking…"):
            state  = {"question": user_q.strip(),
                      "chat_history": st.session_state.chat_history_str}
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