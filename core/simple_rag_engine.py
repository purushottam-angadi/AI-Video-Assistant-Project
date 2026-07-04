# simple_rag_engine.py
import os
from core.vector_store import get_retriever, load_vector_store
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    return ChatMistralAI(
        model="mistral-small-2603",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.3
    )

def get_pipeline_retriever():
    vector_store = load_vector_store()
    return get_retriever(vector_store)

answer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert video assistant. Answer the user's question 
        based ONLY on the context provided below (from the video transcript) 
        and answer in brief but with detail.

        Context:
        {context}
        Previous Conversation:
        {chat_history}""",
    ),
    ("human", "{question}"),
])

rag_chain = answer_prompt | get_llm()


def query(question: str, chat_history: str = "") -> dict:
    retriever = get_pipeline_retriever()
    docs = retriever.invoke(question)

    context = "\n\n".join(d.page_content for d in docs)

    answer = rag_chain.invoke({
        "context": context,
        "question": question,
        "chat_history": chat_history
    })

    return {
        "answer": "🎬 [Simple RAG answer]\n" + answer.content,
        "contexts": [{"id": d.metadata.get("id", i), "text": d.page_content} for i, d in enumerate(docs)]
    }