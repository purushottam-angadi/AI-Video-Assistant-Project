# rag_engine.py
from typing import List , TypedDict, Literal 
from pydantic import BaseModel
import re 
import os
from langchain_mistralai import ChatMistralAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document


from langgraph.graph import StateGraph, START, END
from dotenv import load_dotenv

from . import llm_gateway as gateway
from langchain_core.rate_limiters import InMemoryRateLimiter

# rate_limiter = InMemoryRateLimiter(
#     requests_per_second=0.5,   # 1 request every 2 seconds — tune to your tier's limit
#     check_every_n_seconds=0.1,
#     max_bucket_size=1,
# )

load_dotenv()

def get_llm():
    return ChatMistralAI(model = "mistral-small-2603", mistral_api_key = os.getenv("MISTRAL_API_KEY"),temperature=0.3)


UPPER_TH = 0.7
LOWER_TH = 0.3


class State(TypedDict):
    question : str
    chat_history : str
    docs: List[Document]
    retriever: object  
    good_docs: List[Document]
    verdict: str
    reason: str
    strips: List[str]
    kept_strips: List[str]
    refined_context: str
    web_query: str
    web_docs: List[Document]
    answer: str

      


def retrieve_node(state: State) -> State:
    q = state['question']
    

    block_reason = gateway.input_guardrail(state["question"])
    if block_reason:
     return {"docs": [],"answer": f" Blocked: {block_reason}","verdict": "BLOCKED"}

    docs = state['retriever'].invoke(q)
    
    seen = set()
    deduped_docs = []
    for d in docs:
        key = d.page_content.strip()
        if key not in seen:
            seen.add(key)
            deduped_docs.append(d)

    return {"docs": deduped_docs}

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

    doc_eval_chain = doc_eval_prompt | gateway.get_llm("eval").with_structured_output(DocEvalBatch)
    chunks_text = "\n\n".join(f"[{i}] {d.page_content}" for i, d in enumerate(docs))


    try: 
     result = doc_eval_chain.invoke({"question": q, "chunks": chunks_text})
     # print("DOC EVAL RESULT:", result)
     scores = [0.0] * len(docs)
     for s in result.scores:
       if 0 <= s.index < len(docs):
        scores[s.index] = s.score
    except Exception as e:
        print(f"Error occurred while evaluating documents: {e}")
        if not docs:
            return {"good_docs": [], "verdict": "INCORRECT", "reason": "No docs retrieved."}
        return { 
           "good_docs": docs[:1],
           "verdict": "AMBIGUOUS",  
            "reason": "Evaluator call failed; falling back to top-1 retrieved doc.",
        }
    

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

def needs_rewrite(question: str) -> bool:
    return len(question.strip().split()) > 12

def rewrite_query_node(state:State)->State:

    if not needs_rewrite(state["question"]):
        return {"web_query": state["question"]}
    
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

    rewrite_chain = rewrite_prompt | gateway.get_llm("rewrite").with_structured_output(WebQuery)
    try:
        out = rewrite_chain.invoke({"question": state["question"]})
        return {"web_query": out.query}
    
    except Exception as e:
        print(f"LLM rewrite failed, using fallback: {e}")
        return {"web_query": state["question"]}


def web_search_node(state: State) -> State:
    q = state.get("web_query") or state["question"]

    
    from langchain_tavily import TavilySearch
    tavily = TavilySearch(max_results=2, tavily_api_key=os.getenv("TAVILY_API_KEY"),include_raw_content=False)

    # print("WEB SEARCH QUERY:", q)

    response = tavily.invoke({"query": q})
    # print("TAVILY RAW RESPONSE:", response)
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



    
    # print("VERDICT:", state.get("verdict"))
    # print("DOCS TO USE COUNT:", len(docs_to_use))
   
    
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

    filter_chain = filter_prompt | gateway.get_llm("refine").with_structured_output(RefinedContext)

    context= "\n\n".join(d.page_content for d in docs_to_use).strip()
    # print("CONTEXT LENGTH:", len(context))
    

    strips= decompose_to_sentences(context)
    
   
    try:
     if strips:
            numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(strips))
            kept_strips = filter_chain.invoke({"question": q, "sentences": numbered}).relevant_sentences
     else:
            kept_strips = []
    except Exception as e:
        print(f"[refine_node] LLM filter failed, using fallback: {e}")
        kept_strips = strips  # skip filtering, use everything unfiltered


    # print("REFINED CONTEXT:", refined_context)
    refined_context = "\n".join(kept_strips)




    return {
        "strips": strips,
        "kept_strips": kept_strips,
        "refined_context": refined_context,
    }




def generate_node(state:State)->State:
    refined_context = state["refined_context"]
    if not refined_context.strip():
        refined_context = "\n".join(d.page_content for d in state.get("good_docs", []) + state.get("web_docs", []))


    answer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert video assistant. Answer the user's question 
        based ONLY on the context provided below (which may come from the video transcript or web search) 
        and answer in brief but with detail.

        If the answer is not directly found, infer from related context and provide a reasoned answer.

        Context:
        {context}
        Previous Conversation:
        {chat_history}""",
    ),
    ("human", "{question}"),
])

    rag_chain= answer_prompt | gateway.get_llm("generate")
    try:
     answer = rag_chain.invoke({
        "context": refined_context,
        "question": state["question"],
        "chat_history": state["chat_history"]
    })
     full_answer= answer.content
    except Exception as e:
        print(f"[generate_node] Generation failed even with fallback model: {e}")
        full_answer = "I'm having trouble generating a full answer right now. Please try again in a moment."


    

    verdict = state.get("verdict", "CORRECT")
    if verdict in ("AMBIGUOUS", "INCORRECT"):
     safety_check = gateway.judge_guardrail(full_answer)
     if not safety_check.safe:
      full_answer += f"\n\n Safety check flagged this answer: {safety_check.reason}"
    if verdict == "INCORRECT":
        source_tag = "Web search triggered — answer from live web results\n"
    elif verdict == "AMBIGUOUS":
        source_tag = "Answer from transcript + web search combined\n"
    else:
        source_tag = "Answer from video transcript\n"

    return {"answer": source_tag + full_answer}

#routing 

def route_after_eval(state: State) -> str:
    if state["verdict"] == "CORRECT":
        return "refine"
    else:
        return "rewrite_query"

def route_after_retrieve(state: State) -> str:
    if state.get("verdict") == "BLOCKED":
        return "end"
    else:
        return "eval_each_doc"
    

g = StateGraph(State)

g.add_node("retrieve", retrieve_node)
g.add_node("eval_each_doc", doc_eval_score_node)
g.add_node("rewrite_query", rewrite_query_node)
g.add_node("web_search", web_search_node)
g.add_node("refine", refine_node)
g.add_node("generate", generate_node)

g.add_edge(START, "retrieve")

g.add_conditional_edges(
    "eval_each_doc",
    route_after_eval,
    {
        "refine": "refine",
        "rewrite_query": "rewrite_query",
    },
)
g.add_conditional_edges(
    "retrieve",
    route_after_retrieve,
    {
        "end": END,
        "eval_each_doc": "eval_each_doc",
        
    },
)
g.add_edge("rewrite_query", "web_search")
g.add_edge("web_search", "refine")
g.add_edge("refine", "generate")
g.add_edge("generate", END)

main_graph = g.compile()

# # rag_engine.py
# from typing import List, TypedDict
# from pydantic import BaseModel
# import re
# import os
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.documents import Document

# from langgraph.graph import StateGraph, START, END
# from dotenv import load_dotenv

# # CHANGE: no more ChatMistralAI / get_llm() here — every model, the rate
# # limiter, fallback model, guardrails, and cost tracking now live in
# # llm_gateway.py. This file only orchestrates the graph.
# from . import llm_gateway as gateway

# load_dotenv()

# UPPER_TH = 0.7
# LOWER_TH = 0.3


# class State(TypedDict):
#     question: str
#     chat_history: str
#     docs: List[Document]
#     retriever: object
#     good_docs: List[Document]
#     verdict: str
#     reason: str
#     strips: List[str]
#     kept_strips: List[str]
#     refined_context: str
#     web_query: str
#     web_docs: List[Document]
#     answer: str


# def retrieve_node(state: State) -> State:
#     q = state['question']
#     docs = state['retriever'].invoke(q)

#     seen = set()
#     deduped_docs = []
#     for d in docs:
#         key = d.page_content.strip()
#         if key not in seen:
#             seen.add(key)
#             deduped_docs.append(d)

#     return {"docs": deduped_docs}


# # Score-based evaluator
# class DocScore(BaseModel):
#     index: int
#     score: float
#     reason: str

# class DocEvalBatch(BaseModel):
#     scores: List[DocScore]


# def doc_eval_score_node(state: State) -> State:
#     q = state["question"]
#     docs = state["docs"]

#     doc_eval_prompt = ChatPromptTemplate.from_messages(
#         [
#             (
#                 "system",
#                 "You are a strict retrieval evaluator for RAG.\n"
#                 "You will be given a question and a numbered list of chunks.\n"
#                 "For EACH chunk, return its index, a relevance score in [0.0, 1.0], and a short reason.\n"
#                 "- 1.0: chunk alone is sufficient to answer fully/mostly\n"
#                 "- 0.0: chunk is irrelevant\n"
#                 "Be conservative with high scores.\n"
#                 "Output JSON only.",
#             ),
#             ("human", "Question: {question}\n\nChunks:\n{chunks}"),
#         ]
#     )

#     # CHANGE: model comes from the gateway instead of a local get_llm()
#     doc_eval_chain = doc_eval_prompt | gateway.get_llm("eval").with_structured_output(DocEvalBatch)
#     chunks_text = "\n\n".join(f"[{i}] {d.page_content}" for i, d in enumerate(docs))

#     try:
#         result = doc_eval_chain.invoke({"question": q, "chunks": chunks_text})

#         scores = [0.0] * len(docs)
#         for s in result.scores:
#             if 0 <= s.index < len(docs):
#                 scores[s.index] = s.score

#     except Exception as e:
#         print(f"[doc_eval_score_node] LLM eval failed, using fallback: {e}")
#         if not docs:
#             return {"good_docs": [], "verdict": "INCORRECT", "reason": "No docs retrieved."}
#         return {
#             "good_docs": docs[:1],
#             "verdict": "AMBIGUOUS",
#             "reason": "Evaluator call failed; falling back to top-1 retrieved doc.",
#         }

#     good = [d for d, s in zip(docs, scores) if s > LOWER_TH]

#     if any(s > UPPER_TH for s in scores):
#         return {
#             "good_docs": good,
#             "verdict": "CORRECT",
#             "reason": f"At least one retrieved chunk scored > {UPPER_TH}.",
#         }
#     if len(scores) > 0 and all(s < LOWER_TH for s in scores):
#         return {
#             "good_docs": [],
#             "verdict": "INCORRECT",
#             "reason": f"All retrieved chunks scored < {LOWER_TH}.",
#         }
#     return {
#         "good_docs": good,
#         "verdict": "AMBIGUOUS",
#         "reason": f"No chunk scored > {UPPER_TH}, but not all were < {LOWER_TH}.",
#     }


# class WebQuery(BaseModel):
#     query: str

# def rewrite_query_node(state: State) -> State:

#     rewrite_prompt = ChatPromptTemplate.from_messages(
#         [
#             (
#                 "system",
#                 "Rewrite the user question into a web search query composed of keywords.\n"
#                 "Rules:\n"
#                 "- Keep it short (6–14 words).\n"
#                 "- If the question implies recency (e.g., recent/latest/last week/last month), add a constraint like (last 30 days).\n"
#                 "- Do NOT answer the question.\n"
#                 "- Return JSON with a single key: query",
#             ),
#             ("human", "Question: {question}"),
#         ]
#     )

#     # CHANGE: model comes from the gateway — this is the only cached task
#     rewrite_chain = rewrite_prompt | gateway.get_llm("rewrite").with_structured_output(WebQuery)

#     try:
#         out = rewrite_chain.invoke({"question": state["question"]})
#         return {"web_query": out.query}
#     except Exception as e:
#         print(f"[rewrite_query_node] LLM rewrite failed, using fallback: {e}")
#         return {"web_query": state["question"]}


# def web_search_node(state: State) -> State:
#     q = state.get("web_query") or state["question"]

#     from langchain_tavily import TavilySearch
#     tavily = TavilySearch(max_results=2, tavily_api_key=os.getenv("TAVILY_API_KEY"), include_raw_content=False)

#     response = tavily.invoke({"query": q})
#     results = response.get("results", []) if isinstance(response, dict) else (response or [])

#     web_docs: List[Document] = []

#     for r in results:
#         if not isinstance(r, dict):
#             continue
#         title = r.get("title", "")
#         url = r.get("url", "")
#         content = r.get("raw_content") or r.get("content", "") or r.get("snippet", "")
#         text = f"TITLE: {title}\nURL: {url}\nCONTENT:\n{content}"
#         web_docs.append(Document(page_content=text, metadata={"url": url, "title": title}))

#     return {"web_docs": web_docs}


# def decompose_to_sentences(text: str) -> List[str]:
#     text = re.sub(r"\s+", " ", text).strip()
#     sentences = re.split(r"(?<=[.!?])\s+", text)
#     return [s.strip() for s in sentences if len(s.strip()) > 20]


# class RefinedContext(BaseModel):
#     relevant_sentences: List[str]


# def refine_node(state: State) -> State:

#     q = state["question"]

#     if state.get("verdict") == "CORRECT":
#         docs_to_use = state["good_docs"]
#     elif state.get("verdict") == "INCORRECT":
#         docs_to_use = state["web_docs"]
#     else:  # AMBIGUOUS
#         docs_to_use = state["good_docs"] + state["web_docs"]

#     filter_prompt = ChatPromptTemplate.from_messages(
#         [
#             (
#                 "system",
#                 "You are a strict relevance filter for RAG context.\n"
#                 "You will be given a question and a list of candidate sentences.\n"
#                 "Return ONLY the sentences that directly help answer the question, "
#                 "verbatim, in original order. Output JSON only.",
#             ),
#             ("human", "Question: {question}\n\nSentences:\n{sentences}"),
#         ]
#     )

#     # CHANGE: model comes from the gateway
#     filter_chain = filter_prompt | gateway.get_llm("refine").with_structured_output(RefinedContext)

#     context = "\n\n".join(d.page_content for d in docs_to_use).strip()
#     strips = decompose_to_sentences(context)

#     try:
#         if strips:
#             numbered = "\n".join(f"{i}: {s}" for i, s in enumerate(strips))
#             kept_strips = filter_chain.invoke({"question": q, "sentences": numbered}).relevant_sentences
#         else:
#             kept_strips = []
#     except Exception as e:
#         print(f"[refine_node] LLM filter failed, using fallback: {e}")
#         kept_strips = strips  # skip filtering, use everything unfiltered

#     refined_context = "\n".join(kept_strips)

#     return {
#         "strips": strips,
#         "kept_strips": kept_strips,
#         "refined_context": refined_context,
#     }


# def generate_node(state: State) -> State:
#     refined_context = state["refined_context"]
#     if not refined_context.strip():
#         refined_context = "\n".join(d.page_content for d in state.get("good_docs", []) + state.get("web_docs", []))

#     # guardrail: check the user's question before spending anything on a call
#     block_reason = gateway.input_guardrail(state["question"])
#     if block_reason:
#         return {"answer": f"⚠️ Blocked: {block_reason}"}

#     answer_prompt = ChatPromptTemplate.from_messages([
#         (
#             "system",
#             """You are an expert video assistant. Answer the user's question 
#             based ONLY on the context provided below (which may come from the video transcript or web search) 
#             and answer in brief but with detail.

#             If the answer is not directly found, infer from related context and provide a reasoned answer.

#             Context:
#             {context}
#             Previous Conversation:
#             {chat_history}""",
#         ),
#         ("human", "{question}"),
#     ])

#     # CHANGE: model (primary + fallback already attached inside the gateway)
#     rag_chain = answer_prompt | gateway.get_llm("generate")

#     try:
#         response = rag_chain.invoke({
#             "context": refined_context,
#             "question": state["question"],
#             "chat_history": state["chat_history"],
#         })
#         full_answer = response.content
#     except Exception as e:
#         print(f"[generate_node] Generation failed even with fallback model: {e}")
#         full_answer = "I'm having trouble generating a full answer right now. Please try again in a moment."

#     # guardrail: cheap heuristic check on every answer
#     warning = gateway.output_guardrail(full_answer, refined_context)
#     if warning:
#         full_answer += f"\n\n⚠️ {warning}"

#     verdict = state.get("verdict", "CORRECT")

#     # guardrail: LLM-as-judge for SAFETY (not fact-checking) — only on the
#     # riskier paths (AMBIGUOUS/INCORRECT), since it costs an extra call and
#     # CORRECT-verdict answers are already backed by a high-confidence chunk.
#     if verdict in ("AMBIGUOUS", "INCORRECT"):
#         safety_check = gateway.judge_guardrail(full_answer)
#         if not safety_check.safe:
#             full_answer += f"\n\n⚠️ Safety check flagged this answer: {safety_check.reason}"

#     if verdict == "INCORRECT":
#         source_tag = "🌐 [Web search triggered — answer from live web results]\n"
#     elif verdict == "AMBIGUOUS":
#         source_tag = "📎 [Answer from transcript + web search combined]\n"
#     else:
#         source_tag = "🎬 [Answer from video transcript]\n"

#     return {"answer": source_tag + full_answer}


# def route_after_eval(state: State) -> str:
#     if state["verdict"] == "CORRECT":
#         return "refine"
#     else:
#         return "rewrite_query"


# g = StateGraph(State)

# g.add_node("retrieve", retrieve_node)
# g.add_node("eval_each_doc", doc_eval_score_node)
# g.add_node("rewrite_query", rewrite_query_node)
# g.add_node("web_search", web_search_node)
# g.add_node("refine", refine_node)
# g.add_node("generate", generate_node)

# g.add_edge(START, "retrieve")
# g.add_edge("retrieve", "eval_each_doc")

# g.add_conditional_edges(
#     "eval_each_doc",
#     route_after_eval,
#     {
#         "refine": "refine",
#         "rewrite_query": "rewrite_query",
#     },
# )

# g.add_edge("rewrite_query", "web_search")
# g.add_edge("web_search", "refine")
# g.add_edge("refine", "generate")
# g.add_edge("generate", END)

# main_graph = g.compile()