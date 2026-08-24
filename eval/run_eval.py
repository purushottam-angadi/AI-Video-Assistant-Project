
import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.rag_engine import main_graph
from core import llm_gateway as gateway
from dotenv import load_dotenv
load_dotenv()

from langsmith import Client, traceable
from ragas import evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import LLMContextPrecision, LLMContextRecall, Faithfulness, AnswerRelevancy
from datasets import Dataset

dataset_name = "video-assistant-eval"
client = Client()

# ---- 1. Create/reuse the LangSmith dataset (same as before) ----
if client.has_dataset(dataset_name=dataset_name):
    print(f"Dataset '{dataset_name}' already exists. Skipping creation.")
    dataset = client.read_dataset(dataset_name=dataset_name)
else:
    print(f"Creating dataset '{dataset_name}'...")
    dataset = client.create_dataset(dataset_name=dataset_name)

    json_path = os.path.join(os.path.dirname(__file__), "test_dataset.json")
    with open(json_path, "r") as f:
        test_data = json.load(f)

    for item in test_data:
        client.create_example(
            inputs={"question": item["question"]},
            outputs={"answer": item["answer"]},
            dataset_id=dataset.id
        )
    print(f"Uploaded {len(test_data)} examples to '{dataset_name}'.")


# ---- 2. Pipeline wrapped with @traceable so each run is logged/traced in LangSmith ----
@traceable(name="corrective_rag_pipeline")
def corrective_rag_pipeline(question: str) -> dict:
    state = main_graph.invoke({"question": question, "chat_history": ""})

    refined_context = state.get("refined_context", "")
    if refined_context.strip():
        contexts = [refined_context]
    else:
        docs = state.get("good_docs", []) + state.get("web_docs", [])
        contexts = [d.page_content for d in docs]

    return {"answer": state["answer"], "contexts": contexts}


# ---- 3. Run pipeline over every LangSmith example, build the ragas dataset ----
examples = list(client.list_examples(dataset_name=dataset_name))

rows = []
for ex in examples:
    question = ex.inputs["question"]
    reference = ex.outputs.get("answer", "")

    result = corrective_rag_pipeline(question)  # traced automatically in LangSmith

    rows.append({
        "user_input": question,
        "response": result["answer"],
        "retrieved_contexts": result["contexts"],
        "reference": reference,
    })

ragas_dataset = Dataset.from_list(rows)

# ---- 4. Run all four ragas metrics; traces show up in LangSmith too ----
evaluator_llm = LangchainLLMWrapper(gateway.get_llm("eval"))

result = evaluate(
    dataset=ragas_dataset,
    metrics=[LLMContextPrecision(), LLMContextRecall(), Faithfulness(), AnswerRelevancy()],
    llm=evaluator_llm,
)

print(result)
result.to_pandas().to_csv("ragas_results.csv", index=False)



import sys, os, json
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from core.simple_rag_engine import query as simple_query
from core.rag_engine import main_graph, get_llm
from dotenv import load_dotenv
load_dotenv()

from langsmith import Client
from langsmith.evaluation import evaluate
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from tenacity import retry, wait_exponential, stop_after_attempt

dataset_name = "video-assistant-eval"
client = Client()

if client.has_dataset(dataset_name=dataset_name):
    print(f"Dataset '{dataset_name}' already exists. Skipping creation.")
    dataset = client.read_dataset(dataset_name=dataset_name)
else:
    print(f"Creating dataset '{dataset_name}'...")
    dataset = client.create_dataset(dataset_name=dataset_name)

    json_path = os.path.join(os.path.dirname(__file__), "test_dataset.json")
    with open(json_path, "r") as f:
        test_data = json.load(f)

    for item in test_data:
        client.create_example(
            inputs={"question": item["question"]},
            outputs={"answer": item["answer"]},
            dataset_id=dataset.id
        )
    print(f"Uploaded {len(test_data)} examples to '{dataset_name}'.")


def simple_rag_pipeline(inputs: dict) -> dict:
    result = simple_query(inputs["question"])
    contexts = [c["text"] for c in result.get("contexts", [])]
    return {"answer": result["answer"], "contexts": contexts}


def corrective_rag_pipeline(inputs: dict) -> dict:
    state = main_graph.invoke({
        "question": inputs["question"],
        "chat_history": ""
    })

    refined_context = state.get("refined_context", "")
    if refined_context.strip():
        contexts = [refined_context]
    else:
        docs = state.get("good_docs", []) + state.get("web_docs", [])
        contexts = [d.page_content for d in docs]

    return {"answer": state["answer"], "contexts": contexts}


class CombinedGrade(BaseModel):
    correctness_score: float
    correctness_reason: str
    faithfulness_score: float
    faithfulness_reason: str

grade_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are grading a RAG system's answer on two dimensions.\n"
        "Question: {question}\n"
        "Reference answer: {reference}\n"
        "Retrieved context: {context}\n"
        "Generated answer: {prediction}\n\n"
        "1. Correctness (0.0-1.0): does the generated answer capture the core "
        "meaning of the reference answer, even if phrased differently, shorter, "
        "or missing minor details? Be generous — do not penalize for wording, "
        "extra detail, or structure.\n"
        "2. Faithfulness (0.0-1.0): is the generated answer supported by the "
        "retrieved context, or does it include claims not found in it "
        "(hallucination)? If context is empty, score faithfulness 0.0.\n"
        "Output JSON only.",
    ),
    ("human", "Grade this now."),
])

grade_chain = grade_prompt | get_llm().with_structured_output(CombinedGrade)


MAX_CONTEXT_CHARS = 6000  # keep the grading prompt well under the model's token limit

def truncate_text(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[truncated]"


@retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
def safe_invoke(chain, inputs: dict):
    return chain.invoke(inputs)

class RelevanceGrade(BaseModel):
    answer_relevance_score: float
    answer_relevance_reason: str

answer_relevance_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Question: {question}\n"
        "Generated answer: {prediction}\n\n"
        "Score Answer Relevance (0.0-1.0): does the answer directly address "
        "the question, without being off-topic, evasive, or answering a "
        "different question? Output JSON only.",
    ),
    ("human", "Grade this now."),
])

answer_relevance_chain = answer_relevance_prompt | get_llm().with_structured_output(RelevanceGrade)


class ContextGrade(BaseModel):
    context_relevance_score: float
    context_relevance_reason: str

context_relevance_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Question: {question}\n"
        "Retrieved context: {context}\n\n"
        "Score Context Relevance (0.0-1.0): how much of the retrieved context "
        "is actually useful for answering the question, versus irrelevant "
        "filler? If context is empty, score 0.0. Output JSON only.",
    ),
    ("human", "Grade this now."),
])

context_relevance_chain = context_relevance_prompt | get_llm().with_structured_output(ContextGrade)

def context_relevance_evaluator(run, example):
    question = example.inputs.get("question", "")
    contexts = run.outputs.get("contexts", [])
    context_text = "\n\n".join(contexts) if contexts else "(no context retrieved)"
    context_text = truncate_text(context_text)

    result = safe_invoke(context_relevance_chain, {
        "question": question,
        "context": context_text
    })

    return {"key": "context_relevance", "score": result.context_relevance_score, "comment": result.context_relevance_reason}
class RelevanceGrade(BaseModel):
    answer_relevance_score: float
    answer_relevance_reason: str

answer_relevance_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "Question: {question}\n"
        "Generated answer: {prediction}\n\n"
        "Score Answer Relevance (0.0-1.0): does the answer directly address "
        "the question, without being off-topic, evasive, or answering a "
        "different question? Output JSON only.",
    ),
    ("human", "Grade this now."),
])

answer_relevance_chain = answer_relevance_prompt | get_llm().with_structured_output(RelevanceGrade)


def answer_relevance_evaluator(run, example):
    question = example.inputs.get("question", "")
    prediction = run.outputs.get("answer", "")

    result = safe_invoke(answer_relevance_chain, {
        "question": question,
        "prediction": prediction
    })

    return {"key": "answer_relevance", "score": result.answer_relevance_score, "comment": result.answer_relevance_reason}




def combined_evaluator(run, example):
    question = example.inputs.get("question", "")
    reference = example.outputs.get("answer", "")
    prediction = run.outputs.get("answer", "")
    contexts = run.outputs.get("contexts", [])
    context_text = "\n\n".join(contexts) if contexts else "(no context retrieved)"
    context_text = truncate_text(context_text)

    result = safe_invoke(grade_chain, {
        "question": question,
        "reference": reference,
        "context": context_text,
        "prediction": prediction
    })

    return [
        {"key": "correctness", "score": result.correctness_score, "comment": result.correctness_reason},
        {"key": "faithfulness", "score": result.faithfulness_score, "comment": result.faithfulness_reason},
    ]


# print("Running Simple RAG eval...")
# results_simple = evaluate(
#     simple_rag_pipeline,
#     data=dataset_name,
#     evaluators=[combined_evaluator],
#     experiment_prefix="simple-rag",
#     max_concurrency=1,
# )

print("Running Corrective RAG eval...")
results_crag = evaluate(
    corrective_rag_pipeline,
    data=dataset_name,
    evaluators=[combined_evaluator, context_relevance_evaluator, answer_relevance_evaluator],
    experiment_prefix="corrective-rag",
    max_concurrency=1,
)

# simple_df = results_simple.to_pandas()
crag_df = results_crag.to_pandas()


# def print_comparison(metric_key: str, label: str):
#     col = f"feedback.{metric_key}"
#     simple_score = simple_df[col].mean()
#     crag_score = crag_df[col].mean()
#     improvement = (
#         (crag_score - simple_score) / simple_score * 100
#         if simple_score != 0 else float("nan")
#     )
#     print(f"{label}: Simple={simple_score:.2f} | CRAG={crag_score:.2f} | Improvement={improvement:.1f}%")


# print("\n--- RESULTS ---")
# print_comparison("correctness", "Correctness")
# print_comparison("faithfulness", "Faithfulness")



# from core.vector_store import get_pinecone_client, get_embeddings, get_retriever
# from langchain_pinecone import PineconeVectorStore

# # reuse an existing indexed transcript for eval — same user_id/index you used
# # when you ran run_pipeline() for that video
# EVAL_INDEX_NAME = "meeting-transcripts-384"   # <- your real index name
# EVAL_USER_ID = "default_user"                  # <- whatever user_id that transcript was stored under

# embeddings = get_embeddings()
# vector_store = PineconeVectorStore(index_name=EVAL_INDEX_NAME, embedding=embeddings)

# # you also need the same chunks list to build BM25 for the hybrid retriever
# # simplest: just use the plain vector retriever for eval if you don't have the chunks handy
# retriever = vector_store.as_retriever(
#     search_type="similarity",
#     search_kwargs={"k": 4, "filter": {"user_id": EVAL_USER_ID}},
# )

# import sys, os, json
# sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# from core.rag_engine import main_graph
# from core import llm_gateway as gateway
# from dotenv import load_dotenv
# load_dotenv()

# from langsmith import Client
# from langsmith.evaluation import evaluate
# from langchain_core.prompts import ChatPromptTemplate
# from pydantic import BaseModel
# from tenacity import retry, wait_exponential, stop_after_attempt

# dataset_name = "video-assistant-eval"
# client = Client()

# if client.has_dataset(dataset_name=dataset_name):
#     print(f"Dataset '{dataset_name}' already exists. Skipping creation.")
#     dataset = client.read_dataset(dataset_name=dataset_name)
# else:
#     print(f"Creating dataset '{dataset_name}'...")
#     dataset = client.create_dataset(dataset_name=dataset_name)

#     json_path = os.path.join(os.path.dirname(__file__), "test_dataset.json")
#     with open(json_path, "r") as f:
#         test_data = json.load(f)

#     for item in test_data:
#         client.create_example(
#             inputs={"question": item["question"]},
#             outputs={"answer": item["answer"]},
#             dataset_id=dataset.id
#         )
#     print(f"Uploaded {len(test_data)} examples to '{dataset_name}'.")


# def corrective_rag_pipeline(inputs: dict) -> dict:
#     state = main_graph.invoke({
#         "question": inputs["question"],
#         "chat_history": "",
#         "retriever": retriever
#     })

#     refined_context = state.get("refined_context", "")
#     if refined_context.strip():
#         contexts = [refined_context]
#     else:
#         docs = state.get("good_docs", []) + state.get("web_docs", [])
#         contexts = [d.page_content for d in docs]

#     return {"answer": state["answer"], "contexts": contexts}


# llm = gateway.get_llm("eval")

# MAX_CONTEXT_CHARS = 6000

# def truncate_text(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
#     if len(text) <= max_chars:
#         return text
#     return text[:max_chars] + "\n...[truncated]"


# @retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5))
# def safe_invoke(chain, inputs: dict):
#     return chain.invoke(inputs)


# # ---- Context Precision: are the retrieved chunks relevant? (retrieval side) ----
# class ScoreOnly(BaseModel):
#     score: float
#     reason: str

# context_precision_chain = ChatPromptTemplate.from_messages([
#     ("system",
#      "Question: {question}\nRetrieved context: {context}\n\n"
#      "Score Context Precision (0.0-1.0): what fraction of the retrieved "
#      "context is actually relevant to answering the question? Output JSON only."),
#     ("human", "Grade this."),
# ]) | llm.with_structured_output(ScoreOnly)

# def context_precision_evaluator(run, example):
#     context = truncate_text("\n\n".join(run.outputs.get("contexts", [])) or "(no context retrieved)")
#     r = safe_invoke(context_precision_chain, {"question": example.inputs["question"], "context": context})
#     return {"key": "context_precision", "score": r.score, "comment": r.reason}


# # ---- Context Recall: did retrieval get everything needed vs. reference answer? (retrieval side) ----
# context_recall_chain = ChatPromptTemplate.from_messages([
#     ("system",
#      "Reference answer: {reference}\nRetrieved context: {context}\n\n"
#      "Score Context Recall (0.0-1.0): how much of the information needed to "
#      "produce the reference answer is present in the retrieved context? Output JSON only."),
#     ("human", "Grade this."),
# ]) | llm.with_structured_output(ScoreOnly)

# def context_recall_evaluator(run, example):
#     context = truncate_text("\n\n".join(run.outputs.get("contexts", [])) or "(no context retrieved)")
#     reference = example.outputs.get("answer", "")
#     r = safe_invoke(context_recall_chain, {"reference": reference, "context": context})
#     return {"key": "context_recall", "score": r.score, "comment": r.reason}


# # ---- Faithfulness: is the answer grounded in context, no hallucination? (generation side) ----
# faithfulness_chain = ChatPromptTemplate.from_messages([
#     ("system",
#      "Retrieved context: {context}\nGenerated answer: {prediction}\n\n"
#      "Score Faithfulness (0.0-1.0): is every claim in the answer supported by "
#      "the context? Penalize hallucinated claims. If context is empty, score 0.0. Output JSON only."),
#     ("human", "Grade this."),
# ]) | llm.with_structured_output(ScoreOnly)

# def faithfulness_evaluator(run, example):
#     context = truncate_text("\n\n".join(run.outputs.get("contexts", [])) or "(no context retrieved)")
#     prediction = run.outputs.get("answer", "")
#     r = safe_invoke(faithfulness_chain, {"context": context, "prediction": prediction})
#     return {"key": "faithfulness", "score": r.score, "comment": r.reason}


# # ---- Answer Relevancy: does the answer address the question? (generation side) ----
# answer_relevancy_chain = ChatPromptTemplate.from_messages([
#     ("system",
#      "Question: {question}\nGenerated answer: {prediction}\n\n"
#      "Score Answer Relevancy (0.0-1.0): does the answer directly address the "
#      "question, without being off-topic or evasive? Output JSON only."),
#     ("human", "Grade this."),
# ]) | llm.with_structured_output(ScoreOnly)

# def answer_relevancy_evaluator(run, example):
#     prediction = run.outputs.get("answer", "")
#     r = safe_invoke(answer_relevancy_chain, {"question": example.inputs["question"], "prediction": prediction})
#     return {"key": "answer_relevancy", "score": r.score, "comment": r.reason}


# print("Running Corrective RAG eval...")
# results = evaluate(
#     corrective_rag_pipeline,
#     data=dataset_name,
#     evaluators=[
#         context_precision_evaluator,
#         context_recall_evaluator,
#         faithfulness_evaluator,
#         answer_relevancy_evaluator,
#     ],
#     experiment_prefix="corrective-rag",
#     max_concurrency=1,
# )

# df = results.to_pandas()
# for metric in ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]:
#     col = f"feedback.{metric}"
#     if col in df.columns:
#         print(f"{metric}: {df[col].mean():.2f}")