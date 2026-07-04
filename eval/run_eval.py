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
    return {"answer": result["answer"]}


def corrective_rag_pipeline(inputs: dict) -> dict:
    state = main_graph.invoke({
        "question": inputs["question"],
        "chat_history": ""
    })
    return {"answer": state["answer"]}


class Grade(BaseModel):
    score: float
    reason: str

grade_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a lenient, generous grader comparing a generated answer to a reference answer.\n"
        "Question: {question}\n"
        "Reference answer: {reference}\n"
        "Generated answer: {prediction}\n\n"
        "Give a score between 0.0 and 1.0:\n"
        "- 1.0: captures the main idea, even if phrased differently, shorter, or missing minor details\n"
        "- 0.5: partially relevant, gets some of it right but misses important points\n"
        "- 0.0: completely wrong, irrelevant, or no answer\n"
        "Be generous — do not penalize for different wording, extra detail, or different structure. "
        "Focus only on whether the core meaning is conveyed.\n"
        "Output JSON only.",
    ),
    ("human", "Grade this now."),
])

grade_chain = grade_prompt | get_llm().with_structured_output(Grade)

def correctness_evaluator(run, example):
    question = example.inputs.get("question", "")
    reference = example.outputs.get("answer", "")
    prediction = run.outputs.get("answer", "")

    result = grade_chain.invoke({
        "question": question,
        "reference": reference,
        "prediction": prediction
    })

    return {"key": "correctness", "score": result.score, "comment": result.reason}


print("Running Simple RAG eval...")
results_simple = evaluate(
    simple_rag_pipeline,
    data=dataset_name,
    evaluators=[correctness_evaluator],
    experiment_prefix="simple-rag"
)

print("Running Corrective RAG eval...")
results_crag = evaluate(
    corrective_rag_pipeline,
    data=dataset_name,
    evaluators=[correctness_evaluator],
    experiment_prefix="corrective-rag"
)

simple_df = results_simple.to_pandas()
crag_df = results_crag.to_pandas()

simple_correctness = simple_df["feedback.correctness"].mean()
crag_correctness = crag_df["feedback.correctness"].mean()

improvement = (crag_correctness - simple_correctness) / simple_correctness * 100

print("\n--- RESULTS ---")
print(f"Correctness: Simple={simple_correctness:.2f} | CRAG={crag_correctness:.2f} | Improvement={improvement:.1f}%")