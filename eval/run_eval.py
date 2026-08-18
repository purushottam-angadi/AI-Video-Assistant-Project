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