import psutil
import os

import warnings
warnings.filterwarnings("ignore", message="Pydantic serializer warnings")
_process = psutil.Process(os.getpid())

from utils.audio_processor import process_audio, is_youtube_url, get_youtube_transcript
from core.transcriber import transcribe_full
from dotenv import load_dotenv
load_dotenv()
import gc
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.vector_store import build_vector_store, get_retriever

def log_mem(label: str):
    """Print current resident memory (RSS) usage, in MB, with a label."""
    rss_mb = _process.memory_info().rss / (1024 * 1024)
    print(f"[MEM] {label:<35} {rss_mb:8.1f} MB")


def run_pipeline(source: str, language: str = "english",user_id: str = "default_user") -> dict:

    
    
   
    print("starting AI Video Assistant")
    log_mem("start")

    if is_youtube_url(source):
        print("Fetching transcript via YouTube transcript API...")
        transcript = get_youtube_transcript(source, language=language)
        log_mem("after youtube transcript fetch")
    else:
        chunks = process_audio(source)
        log_mem("after process_audio (chunking)")

        transcript = transcribe_full(chunks, language=language)
        log_mem("after transcribe_full")

    gc.collect()
    log_mem("after gc.collect (post-transcription)")
    print(f"raw transcription (first 300 characters) {transcript[:300]}")

    title = generate_title(transcript)
    log_mem("after generate_title")

    summary = summarize(transcript)
    log_mem("after summarize")

    action_item = extract_action_items(transcript)
    log_mem("after extract_action_items")

    decisions = extract_key_decisions(transcript)
    log_mem("after extract_key_decisions")

    questions = extract_questions(transcript)
    log_mem("after extract_questions")

    gc.collect()
    log_mem("after gc.collect (post-extraction)")

    vs = build_vector_store(transcript, user_id=user_id)
    log_mem("after build_vector_store (embeddings)")

    retriever = get_retriever(vs, user_id=user_id)
    log_mem("after get_retriever")

    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "retriever": retriever,
    }


if __name__ == "__main__":
    source = input("Enter YouTube URL or local file path: ").strip().strip('"').strip("'")
    language = input("Language (english/hinglish): ").strip() or "english"

    log_mem("before run_pipeline")
    result = run_pipeline(source, language)
    log_mem("after run_pipeline returns")

    print("\n" + "=" * 60)
    print(f" Title: {result['title']}")
    print(f"\n Summary:\n{result['summary']}")
    print(f"\n Action Items:\n{result['action_items']}")
    print(f"\n Key Decisions:\n{result['key_decisions']}")
    print(f"\n Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    
    print("\n💬 Chat with your meeting (type 'exit' to quit)\n")

    chat_history = ""
    retriever = result["retriever"] 

    while True:
        question = input("You: ").strip()
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        if not question:
            continue

        log_mem(f"before chat turn ({question[:20]!r})")

        state = {
            "question": question,
            "chat_history": chat_history,
            "retriever": retriever,   
        }
        from core.rag_engine import main_graph
        answer = main_graph.invoke(state)["answer"]

        log_mem(f"after chat turn ({question[:20]!r})")

        chat_history += f"User: {question}\nAssistant: {answer}\n"

        print(f"\n🤖 Assistant: {answer}\n")