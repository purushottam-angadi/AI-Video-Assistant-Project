

import os
from dotenv import load_dotenv
from pydantic import BaseModel

from langchain_core.prompts import ChatPromptTemplate
from langchain_litellm import ChatLiteLLM
from langchain_core.rate_limiters import InMemoryRateLimiter

load_dotenv()

rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.75,   
    check_every_n_seconds=0.1,
    max_bucket_size=1,
)

MODELS = {
    "eval": "mistral/mistral-small-latest",
    "generate": "mistral/mistral-medium-latest",
    "rewrite": "mistral/mistral-small-2603",
    "refine": "mistral/mistral-small-latest",
    "judge": "mistral/mistral-small-2603",
}

FALLBACK_MODEL = "groq/llama-3.3-70b-versatile" 

MAX_TOKENS = {
    "eval": 350,
    "rewrite": 100,
    "refine": 500,
    "generate": 300,
    "judge": 100,   
}



def get_llm(task:str):

    primary = ChatLiteLLM(
        model=MODELS[task],
        api_key=os.getenv("MISTRAL_API_KEY"),
        temperature=0.2,
        max_tokens=MAX_TOKENS[task],
        rate_limiter=rate_limiter,
        model_kwargs={"cache": {"no-cache": task != "rewrite"}},  
    )
    

    backup = ChatLiteLLM(
        model=FALLBACK_MODEL,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_tokens=MAX_TOKENS[task],
        rate_limiter=rate_limiter,
    )
    return primary.with_fallbacks([backup])



INJECTION_MARKERS = ["ignore previous instructions", "ignore your instructions", "reveal your system prompt"]
PII_MARKERS = ["ssn", "social security number", "credit card number", "aadhaar", "passport number"]

def input_guardrail(text: str) -> str | None:

    t = (text or "").strip()
    if not t:
        return "Empty input."
    if len(t) > 4000:
        return "Input too long."
    if any(m in t.lower() for m in INJECTION_MARKERS):
        return "Possible prompt injection detected."
    if any(m in t.lower() for m in PII_MARKERS):
        return "Request appears to ask for sensitive personal data."
    return None


def output_guardrail(answer: str, context: str) -> str | None:

    if not context.strip() and answer.strip():
        return "Answer produced with no supporting context."
    if len(answer.strip()) < 2:
        return "Answer looks empty or too short."
    return None



class SafetyVerdict(BaseModel):
    safe: bool
    reason: str
 
def judge_guardrail(answer: str) -> SafetyVerdict:

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a responsible-AI safety reviewer. Check the ANSWER below for:\n"
            "- harmful or dangerous content\n"
            "- hateful, biased, or discriminatory language\n"
            "- unsafe medical/legal/financial advice presented as fact\n"
            "Do NOT check facts or accuracy — only check for safety issues.\n"
            "Output JSON only.",
        ),
        ("human", "Answer:\n{answer}"),
    ])

    chain = prompt | get_llm("judge").with_structured_output(SafetyVerdict)
    try:
        return chain.invoke({"answer": answer})
    except Exception:
        return SafetyVerdict(safe=True, reason="Safety check unavailable.")