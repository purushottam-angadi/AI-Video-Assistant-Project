import os
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.vector_store import build_vector_store, load_vector_store, get_retriever

def get_llm():
    return ChatMistralAI(
        model="mistral-small-latest",
        mistral_api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.3,
    )

def format_docs(docs):
    return "\n\n".join ([doc.page_content for doc in docs])


def build_rag_chain(transcript:str):
    vector_store=build_vector_store(transcript)
    retriever=get_retriever(vector_store, k=5)
    llm = get_llm()
    prompt= prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert meeting assistant. Answer the user's question 
        based ONLY on the meeting transcript context provided below and answer in brief like in detail.

        If the answer is not found in the context, say: 
        "I could not find this information in the meeting transcript."
        



        Context from meeting transcript:
         {context}
         Previous Conversation:
         {chat_history}""",
         
        ),
        ("human", "{question}"),
        ])

    rag_chain=(
         {"context": RunnableLambda(lambda x: x["question"]) | retriever | RunnableLambda(format_docs),
          "question": RunnableLambda(lambda x: x["question"]),
          "chat_history": RunnableLambda(lambda x: x.get("chat_history", ""))}
          |prompt|llm|StrOutputParser())
    
    
    return rag_chain

def load_rag_chain():
    vector_store=load_vector_store()
    retriever=get_retriever(vector_store, k=4)
    llm = get_llm()
    prompt= prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an expert meeting assistant. Answer the user's question 
        based ONLY on the meeting transcript context provided below.and answer in brief.

        If the answer is not found in the context, say: 
        "I could not find this information in the meeting transcript."

        Always be concise and precise. If quoting someone, mention it clearly.

        Context from meeting transcript:
         {context}
         
         Previous Conversation:
         {chat_history}""",
        ),
        ("human", "{question}"),
        ])

    rag_chain=(
        {"context": RunnableLambda(lambda x: x["question"]) | retriever | RunnableLambda(format_docs),
         "question": RunnableLambda(lambda x: x["question"]),
         "chat_history": RunnableLambda(lambda x: x.get("chat_history", ""))}
          |prompt|llm|StrOutputParser())
    
    return rag_chain

def ask_question(rag_chain, question: str, chat_history: str = "") -> str:
    """
    Ask a question to the RAG chain, including optional chat history.

    Args:
        rag_chain: The RAG chain object
        question: The current user question
        chat_history: A string containing previous conversation turns

    Returns:
        str: The assistant's answer
    """
    

    # Pass both question and history into the chain
    answer = rag_chain.invoke({
        "question": question,
        "chat_history": chat_history
    })

    
    return answer
