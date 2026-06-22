

import os
from langchain_chroma import Chroma
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "vector_db"
COLLECTION_NAME = "meeting_transcript"
EMBEDDING_MODEL = "mistral-embed"  # 1024-dim, API-based — no local model in memory


def get_embeddings() -> MistralAIEmbeddings:
    """
    Returns Mistral API-based embeddings.
    No model weights are loaded locally — all inference happens on Mistral's servers.
    Requires MISTRAL_API_KEY in your .env file.
    """
    return MistralAIEmbeddings(
        model=EMBEDDING_MODEL,
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
    )


def split_transcript(transcript: str) -> list[Document]:
    """
    Splits a transcript string into overlapping chunks and wraps them as Documents.
    Chunk size and overlap are tuned for meeting transcripts (~spoken sentences).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = splitter.split_text(transcript)
    return [
        Document(page_content=chunk, metadata={"source": "meeting"})
        for chunk in chunks
    ]

def build_vector_store(transcript: str) -> Chroma:
    """
    Embeds transcript chunks and persists them into a local Chroma vector store.
    Safe to call multiple times — Chroma will overwrite the existing collection.
    """
    print("Building vector store...")
    docs = split_transcript(transcript)
    embeddings = get_embeddings()

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME,
    )

    print(f"✅ Vector store built at '{CHROMA_DIR}', collection: '{COLLECTION_NAME}'")
    print(f"   Chunks indexed: {len(docs)}")
    return vectorstore

def get_retriever(vector_store: Chroma, k: int = 4):
    """
    Returns a similarity-based retriever from the given vector store.
    k: number of top chunks to retrieve per query.
    """
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )