# VideoMind — AI Video Assistant

A RAG-based AI assistant that transcribes video and audio recordings, extracts structured insights, and enables context-aware Q&A over the content using Corrective RAG.

**[Live App](https://ai-video-assistant-project-production.up.railway.app/)** 

---

## What it does

Drop in a video, audio file,and VideoMind:

- Transcribes the content in English or Hinglish
- Generates a structured summary, action items, key decisions, and open questions
- Lets you chat with the recording via a Corrective RAG pipeline that retrieves relevant transcript chunks, grades their relevance, and falls back to live web search when the transcript doesn't contain the answer

---

## Architecture

```
Upload A local file
        ↓
Audio Processing (pydub / ffmpeg → 60s WAV chunks)
        ↓
Transcription (Groq Whisper API / Sarvam AI for Hinglish)
        ↓
Extraction (Mistral AI → summary, actions, decisions, questions)
        ↓
Vector Store (FAISS in-memory, Mistral embeddings)
        ↓
Corrective RAG (LangGraph)
    ├── Retrieve top-k chunks
    ├── Grade relevance (LLM scorer, 0.0–1.0)
    ├── CORRECT  → refine context → generate answer
    ├── AMBIGUOUS → transcript + web search → refine → generate
    └── INCORRECT → rewrite query → Tavily web search → refine → generate
```

---

## Corrective RAG vs Simple RAG

Evaluated both pipelines on a custom dataset via LangSmith. Corrective RAG improved retrieval accuracy by **15%** through:

- Per-chunk relevance scoring (not just similarity threshold)
- Query rewriting for web search fallback
- Sentence-level context refinement before generation

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Mistral AI (`mistral-small-2603`) |
| Transcription (English) | Groq Whisper (`whisper-large-v3-turbo`) |
| Transcription (Hinglish) | Sarvam AI (`saaras:v3`) |
| Embeddings | Mistral AI (`mistral-embed`) |
| Vector Store | FAISS (in-memory) |
| RAG Orchestration | LangGraph |
| Web Search Fallback | Tavily |
| Evaluation | LangSmith |
| UI | Streamlit |
| Containerisation | Docker |

---

## Project Structure

```
├── core/
│   ├── rag_engine.py        # LangGraph Corrective RAG pipeline
│   ├── vector_store.py      # FAISS in-memory vector store
│   ├── transcriber.py       # Groq + Sarvam transcription router
│   ├── summarizer.py        # Map-reduce summarisation
│   └── extractor.py         # Action items, decisions, questions
├── utils/
│   └── audio_processor.py   # Audio chunking (pydub / ffmpeg)
├── eval/
│   ├── run_eval.py          # LangSmith evaluation pipeline
│   └── test_dataset.json    # Evaluation dataset
├── appui.py                 # Streamlit UI
├── main.py                  # CLI entry point
├── Dockerfile
└── requirements.txt
```

---

## Running locally

**1. Clone and set up environment:**
```bash
git clone https://github.com/purushottam-angadi/AI-Video-Assistant-Project
cd AI-Video-Assistant-Project
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Add API keys — create a `.env` file:**
```
MISTRAL_API_KEY=your_key
GROQ_API_KEY=your_key
SARVAM_API_KEY=your_key
TAVILY_API_KEY=your_key
```

**3. Run the app:**
```bash
streamlit run appui.py
```

**Or run the CLI:**
```bash
python main.py
```

---

## Deployment

The app is containerised with Docker and deployed on Railway. Key optimisations made for the memory-constrained environment:

- All heavy imports are lazy (loaded only when a video is processed, not on startup)
- FAISS replaces ChromaDB — lighter in-memory index, no persistence overhead
- Audio is processed via ffmpeg subprocess so Python's heap never holds decoded audio
- Startup memory footprint: ~110MB (vs ~490MB before optimisation)

---

## Evaluation Results

| Metric | Simple RAG | Corrective RAG |
|---|---|---|
| Retrieval Accuracy | baseline | +15% |
| Faithfulness | baseline | improved |

Evaluated using a custom Q&A dataset with LangSmith, scoring correctness and faithfulness via an LLM grader.

---

## Timeline

May 2026 – June 2026