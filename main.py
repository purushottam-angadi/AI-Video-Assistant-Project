from utils.audio_processor import process_audio
from core.transcriber import transcribe_full
from dotenv import load_dotenv
load_dotenv()
import gc,os
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question, load_rag_chain

import psutil
import os

def log_memory(step: str):
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"[MEMORY] {step}: {mem_mb:.1f} MB")

def run_pipeline(source: str, language: str = "english") -> dict:
    log_memory("start")
    
    chunks = process_audio(source)
    log_memory("after audio processing")
    
    transcript = transcribe_full(chunks, language=language)
    log_memory("after transcription")
    
    gc.collect()
    
    title = generate_title(transcript)
    log_memory("after generate_title")
    
    summary = summarize(transcript)
    log_memory("after summarize")
    
    action_item = extract_action_items(transcript)
    log_memory("after action_items")
    
    decisions = extract_key_decisions(transcript)
    log_memory("after decisions")
    
    questions = extract_questions(transcript)
    log_memory("after questions")
    
    gc.collect()
    
    rag_chain = build_rag_chain(transcript)
    log_memory("after rag_chain built")
    
    return {
        "title": title,
        "transcript": transcript,
        "summary": summary,
        "action_items": action_item,
        "key_decisions": decisions,
        "open_questions": questions,
        "rag_chain": rag_chain,
    }


if __name__ == "__main__":
    source=input("Enter YouTube URL or local file path: ").strip().strip('"').strip("'")
    language = input("Language (english/hinglish): ").strip() or "english"
    result = run_pipeline(source, language)

    print("\n" + "=" * 60)
    print(f"📌 Title: {result['title']}")
    print(f"\n Summary:\n{result['summary']}")
    print(f"\n Action Items:\n{result['action_items']}")
    print(f"\n Key Decisions:\n{result['key_decisions']}")
    print(f"\n Open Questions:\n{result['open_questions']}")
    print("=" * 60)

    # Phase 2 — Chat with your meeting via RAG
    print("\n💬 Chat with your meeting (type 'exit' to quit)\n")
    rag_chain = result["rag_chain"]

    # Keep a list of (user, assistant) messages
    chat_history = ""

    while True:
        question = input("You: ").strip()
        if question.lower() in ["exit", "quit", "q"]:
            print("👋 Goodbye!")
            break
        if not question:
            continue

        # Format history into a string
        

        # Ask question with history
        answer = ask_question(rag_chain, question, chat_history)

        # Save this turn into history
        chat_history += f"User: {question}\nAssistant: {answer}\n"

        print(f"\n🤖 Assistant: {answer}\n")

