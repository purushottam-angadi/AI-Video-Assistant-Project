import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv
load_dotenv()

CHROMA_DIR="vector_db"
COLLECTION_NAME="meeting_transcript"
EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2"

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name= EMBEDDING_MODEL,
        model_kwargs={"device":'cpu'}
    )

def split_transcript(transcript: str):
    
    splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200)

    chunks=  splitter.split_text(transcript)
    docs=[
        Document(page_content=chunk, metadata={"source":"meeting"}) for chunk in chunks]
    return docs

def build_vector_store(transcript:str)->Chroma:
    print("Building Vector Store")

    docs=split_transcript(transcript)

    embeddings=get_embeddings()

    vectorstore=Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
        collection_name=COLLECTION_NAME
    )
    
  
    print(f"✅ Vector store built at: {CHROMA_DIR}, collection: {COLLECTION_NAME}")

    return vectorstore
    

def load_vector_store() ->Chroma:
    embeddings = get_embeddings()
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function= embeddings,
        persist_directory=CHROMA_DIR
    )

    return vector_store

def get_retriever(vector_store: Chroma, k: int=4):
    return vector_store.as_retriever(
        search_type= 'similarity',
        search_kwargs= {"k":k}
    )
    