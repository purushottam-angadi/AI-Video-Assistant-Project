from fastapi import FastAPI , HTTPException, Depends, status
from pydantic import BaseModel
from api.auth import auth_router, get_current_user, init_db

from core.rag_engine import main_graph
from process.main import run_pipeline

app = FastAPI(title="VideoMind API")

init_db()
app.include_router(auth_router)


class ProcessRequest(BaseModel):
    source:  str
    language: str ="english"

class ProcessResponse(BaseModel):
    title: str
    transcript: str
    summary: str
    action_items: str
    key_decisions: str
    open_questions: str

class ChatRequest(BaseModel):
    question: str
    chat_history: str = ""


class ChatResponse(BaseModel):
    answer: str

RETRIEVER_STORE: dict[str,object]={}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/process", response_model=ProcessResponse)
def process_videos(req: ProcessRequest, user_id: str = Depends(get_current_user)):
    try:
        result = run_pipeline(req.source, req.language, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    RETRIEVER_STORE[user_id] = result["retriever"]
    return ProcessResponse(
        title=result["title"],
        transcript=result["transcript"],
        summary=result["summary"],
        action_items=result["action_items"],
        key_decisions=result["key_decisions"],
        open_questions=result["open_questions"],
    )

@app.post("/chat", response_model=ChatResponse)

def chat(req: ChatRequest, user_id: str= Depends(get_current_user)):
    retriever=RETRIEVER_STORE.get(user_id)
    if retriever is None:
        raise HTTPException(status_code=400, detail="No processed video found for this user. Call /process first")

    try:
        state = main_graph.invoke({
            "question": req.question,
            "chat_history": req.chat_history,
            "retriever": retriever,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
 
    return ChatResponse(answer=state.get("answer", ""))