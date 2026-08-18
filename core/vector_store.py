

# import os
# from langchain_community.vectorstores.faiss import FAISS
# from langchain_mistralai import MistralAIEmbeddings
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_core.documents import Document
# from dotenv import load_dotenv
# from langchain_vectorstore import Chroma

# load_dotenv()


# EMBEDDING_MODEL = "mistral-embed"  # 1024-dim, API-based — no local model in memory


# def get_embeddings() -> MistralAIEmbeddings:
#     """
#     Returns Mistral API-based embeddings.
#     No model weights are loaded locally — all inference happens on Mistral's servers.
#     Requires MISTRAL_API_KEY in your .env file.
#     """
#     return MistralAIEmbeddings(
#         model=EMBEDDING_MODEL,
#         mistral_api_key=os.getenv("MISTRAL_API_KEY"),
#     )


# def split_transcript(transcript: str) -> list[Document]:
#     """
#     Splits a transcript string into overlapping chunks and wraps them as Documents.
#     Chunk size and overlap are tuned for meeting transcripts (~spoken sentences).
#     """
#     splitter = RecursiveCharacterTextSplitter(
#         chunk_size=1000,
#         chunk_overlap=200,
#     )
#     chunks = splitter.split_text(transcript)
#     return [
#         Document(page_content=chunk, metadata={"source": "meeting"})
#         for chunk in chunks
#     ]

# def build_vector_store(transcript: str, collection_name: str = "meeting_transcripts") -> Chroma:
#     """
#     Builds a Chroma vector store from a transcript, using HuggingFace API embeddings.
#     Persists to disk at PERSIST_DIR so it survives restarts.
#     """
#     docs = split_transcript(transcript)
#     embeddings = get_embeddings()

#     return Chroma.from_documents(
#         documents=docs,
#         embedding=embeddings,
#         collection_name=collection_name,
#         persist_directory=PERSIST_DIR,
#     )


# def get_retriever(vector_store: Chroma, k: int = 4):
#     """
#     Returns a similarity-based retriever from the given Chroma vector store.
#     k: number of top chunks to retrieve per query.
#     """
#     return vector_store.as_retriever(
#         search_type="similarity",
#         search_kwargs={"k": k},
#     )

import os
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_mistralai import MistralAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = "mistral-embed"
EMBEDDING_DIM = 1024
INDEX_NAME = "meeting-transcripts"  # Pinecone calls it an "index", not a "collection"


def get_embeddings() -> MistralAIEmbeddings:
    return MistralAIEmbeddings(
        model=EMBEDDING_MODEL,
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
    )


def get_pinecone_client() -> Pinecone:
    return Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def ensure_index(pc: Pinecone, index_name: str = INDEX_NAME) -> None:
    if index_name not in [i.name for i in pc.list_indexes()]:
        
        pc.create_index(
            name=index_name,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )


def split_transcript(transcript: str, user_id: str) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(transcript)
    return [
        Document(
            page_content=chunk,
            metadata={"source": "meeting", "user_id": user_id},
        )
        for chunk in chunks
    ]


def build_vector_store(transcript: str, user_id: str, index_name: str = INDEX_NAME) -> PineconeVectorStore:
    pc = get_pinecone_client()
    ensure_index(pc, index_name)

    docs = split_transcript(transcript, user_id=user_id)
    embeddings = get_embeddings()

    vector_store = PineconeVectorStore(index_name=index_name, embedding=embeddings)
    vector_store.add_documents(documents=docs)
    return vector_store


def get_retriever(vector_store: PineconeVectorStore, user_id: str, k: int = 4):
    filter_dict = {"user_id": user_id}
    

    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "filter": filter_dict},
    )