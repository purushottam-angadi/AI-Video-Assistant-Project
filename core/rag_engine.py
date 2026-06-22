# 

# rag_engine.py
from core.vector_store import get_retriever, load_vector_store
from typing import List , TypedDict, Literal 
from pydantic import BaseModel
import re 
import os
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from core.vector_store import get_retriever, load_vector_store
from langchain_core.documents import Document


from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from langchain_tavily import TavilySearch

load_dotenv()

def get_llm():
    return ChatMistralAI(model = "mistral-small-2603", mistral_api_key = os.getenv("MISTRAL_API_KEY"),temperature=0.3)

UPPER_TH = 0.7
LOWER_TH = 0.3


def get_pipeline_retriever():
    vector_store = load_vector_store()
    return get_retriever(vector_store)

try:
    vector_store = load_vector_store()
    retriever = get_retriever(vector_store)
except FileNotFoundError:
    retriever = None   # or raise a clearer error


class State(TypedDict):
    question : str
    chat_history : str
    docs: List[Document]
    good_docs: List[Document]
    verdict: str
    reason: str
    strips: List[str]
    kept_strips: List[str]
    refined_context: str
    web_query: str
    web_docs: List[Document]
    answer: str

def retrieve_node(state: State)-> State:
    q=state['question']
    return {"docs": retriever.invoke(q)}


#Score-based evaluator
class DocScore(BaseModel):
    index: int
    score: float
    reason: str

class DocEvalBatch(BaseModel):
    scores: List[DocScore]

def doc_eval_score_node(state: State) -> State:
    q = state["question"]
    docs = state["docs"]

    doc_eval_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a strict retrieval evaluator for RAG.\n"
                "You will be given a question and a numbered list of chunks.\n"
                "For EACH chunk, return its index, a relevance score in [0.0, 1.0], and a short reason.\n"
                "- 1.0: chunk alone is sufficient to answer fully/mostly\n"
                "- 0.0: chunk is irrelevant\n"
                "Be conservative with high scores.\n"
                "Output JSON only.",
            ),
            ("human", "Question: {question}\n\nChunks:\n{chunks}"),
        ]
    )

    doc_eval_chain = doc_eval_prompt | get_llm().with_structured_output(DocEvalBatch)

    chunks_text = "\n\n".join(f"[{i}] {d.page_content}" for i, d in enumerate(docs))
    result = doc_eval_chain.invoke({"question": q, "chunks": chunks_text})
    

    print("DOC EVAL RESULT:", result)



    scores = [0.0] * len(docs)
    for s in result.scores:
        if 0 <= s.index < len(docs):
            scores[s.index] = s.score

    good = [d for d, s in zip(docs, scores) if s > LOWER_TH]

    if any(s > UPPER_TH for s in scores):
        return {
            "good_docs": good,
            "verdict": "CORRECT",
            "reason": f"At least one retrieved chunk scored > {UPPER_TH}.",
        }
    if len(scores) > 0 and all(s < LOWER_TH for s in scores):
        return {
            "good_docs": [],
            "verdict": "INCORRECT",
            "reason": f"All retrieved chunks scored < {LOWER_TH}.",
        }
    return {
        "good_docs": good,
        "verdict": "AMBIGUOUS",
        "reason": f"No chunk scored > {UPPER_TH}, but not all were < {LOWER_TH}.",
    }


class WebQuery(BaseModel):
    query:str




def rewrite_query_node(state:State)->State:
    rewrite_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Rewrite the user question into a web search query composed of keywords.\n"
            "Rules:\n"
            "- Keep it short (6–14 words).\n"
            "- If the question implies recency (e.g., recent/latest/last week/last month), add a constraint like (last 30 days).\n"
            "- Do NOT answer the question.\n"
            "- Return JSON with a single key: query",
        ),
        ("human", "Question: {question}"),
    ]
)

    rewrite_chain = rewrite_prompt | get_llm().with_structured_output(WebQuery)

    out=rewrite_chain.invoke({"question":state["question"]})
    return {"web_query": out.query}



tavily = TavilySearch(max_results=2, tavily_api_key=os.getenv("TAVILY_API_KEY"),include_raw_content=True)

def web_search_node(state: State) -> State:
    q = state.get("web_query") or state["question"]


    print("WEB SEARCH QUERY:", q)




    response = tavily.invoke({"query": q})
    print("TAVILY RAW RESPONSE:", response)
    # TavilySearch returns a dict; the actual results are under "results"
    results = response.get("results", []) if isinstance(response, dict) else (response or [])

    web_docs: List[Document] = []

    for r in results:
        if not isinstance(r, dict):
            continue
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("raw_content") or r.get("content", "") or r.get("snippet", "")
        text = f"TITLE: {title}\nURL: {url}\nCONTENT:\n{content}"
        web_docs.append(Document(page_content=text, metadata={"url": url, "title": title}))

    return {"web_docs": web_docs}

#decompose the docs for knowledge refinement

def decompose_to_sentences(text : str)->List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]
   

class RefinedContext(BaseModel):
    relevant_sentences: List[str]

def refine_node(state:State)->State:

    q = state["question"]

    if state.get("verdict") == "CORRECT":
        docs_to_use = state["good_docs"]

    elif state.get("verdict") == "INCORRECT":
        docs_to_use = state["web_docs"]

    else:  # AMBIGUOUS
        docs_to_use = state["good_docs"] + state["web_docs"]



    
    print("VERDICT:", state.get("verdict"))
    print("DOCS TO USE COUNT:", len(docs_to_use))
   

    context= "\n\n".join(d.page_content for d in docs_to_use).strip()
    print("CONTEXT LENGTH:", len(context))


    strips= decompose_to_sentences(context)
    
    filter_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict relevance filter for RAG context.\n"
            "You will be given a question and a list of candidate sentences.\n"
            "Return ONLY the sentences that directly help answer the question, "
            "verbatim, in original order. Output JSON only.",
        ),
        ("human", "Question: {question}\n\nSentences:\n{sentences}"),
    ]
)

    filter_chain = filter_prompt | get_llm().with_structured_output(RefinedContext)

    if strips:
        numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(strips))
        kept_strips = filter_chain.invoke({"question": q, "sentences": numbered}).relevant_sentences
    else:
        kept_strips = []
    refined_context= "\n".join(kept_strips)
    

    print("REFINED CONTEXT:", refined_context)




    return {
        "strips": strips,
        "kept_strips": kept_strips,
        "refined_context": refined_context,
    }

answer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert video assistant. Answer the user's question 
        based ONLY on the context provided below (which may come from the video transcript or web search) 
        and answer in brief but with detail.

        If the answer is not found in the context, say: 
        "I could not find this information."

        Context:
        {context}
        Previous Conversation:
        {chat_history}""",
    ),
    ("human", "{question}"),
])

rag_chain= answer_prompt | get_llm()



def generate_node(state:State)->State:
    answer= rag_chain.invoke({"context": state["refined_context"],
           "question": state["question"],
           "chat_history": state["chat_history"]
    })
    verdict = state.get("verdict", "CORRECT")
    if verdict == "INCORRECT":
        source_tag = "🌐 [Web search triggered — answer from live web results]\n"
    elif verdict == "AMBIGUOUS":
        source_tag = "📎 [Answer from transcript + web search combined]\n"
    else:
        source_tag = "🎬 [Answer from video transcript]\n"

    return {"answer": source_tag + answer.content}

#routing 

def route_after_eval(state: State) -> str:
    if state["verdict"] == "CORRECT":
        return "refine"
    else:
        return "rewrite_query"
    
    

g = StateGraph(State)

g.add_node("retrieve", retrieve_node)
g.add_node("eval_each_doc", doc_eval_score_node)
g.add_node("rewrite_query", rewrite_query_node)
g.add_node("web_search", web_search_node)
g.add_node("refine", refine_node)
g.add_node("generate", generate_node)

g.add_edge(START, "retrieve")
g.add_edge("retrieve", "eval_each_doc")

g.add_conditional_edges(
    "eval_each_doc",
    route_after_eval,
    {
        "refine": "refine",
        "rewrite_query": "rewrite_query",
    },
)

g.add_edge("rewrite_query", "web_search")
g.add_edge("web_search", "refine")
g.add_edge("refine", "generate")
g.add_edge("generate", END)

main_graph = g.compile()
