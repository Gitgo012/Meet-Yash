import os
import time
import logging
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from groq import Groq

from personality import SYSTEM_PROMPT
from context_builder import build_system_prompt
from rag.query_router import resolve_profile
from rag.retriever import retrieve_resume_context

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meet-yash")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip() or "openai/gpt-oss-120b"

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(api_key=GEMINI_API_KEY)
groq_client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

MODELS = [
    model.strip()
    for model in os.getenv(
        "GEMINI_MODELS",
        "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash,gemini-3.5-flash"
    ).split(",")
    if model.strip()
]

app = FastAPI(
    title="Meet Yash API",
    description="Conversational AI representation of Yash",
    version="1.2.0"
)

frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = list({
    frontend_url,
    "http://localhost:5173",
    "http://127.0.0.1:5173"
})
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ProfileChoice = Literal[
    "auto", "data_analyst", "data_scientist", "data_engineer", "genai", "general"
]

class Message(BaseModel):
    role: Literal["user", "model"]
    content: str = Field(min_length=1, max_length=4000)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[Message] = Field(default_factory=list)
    profile: ProfileChoice = "auto"

class SourceReference(BaseModel):
    source_file: str
    profile: str
    similarity: float

class ChatResponse(BaseModel):
    reply: str
    model_used: str
    selected_profile: str
    detected_profile: str
    sources: list[SourceReference] = Field(default_factory=list)

def is_retryable_error(error):
    status = getattr(error, "code", None)
    if status is None:
        status = getattr(error, "status_code", None)
    error_text = str(error).upper()
    return (
        str(status) in ("429", "503")
        or "503 UNAVAILABLE" in error_text
        or "429 RESOURCE_EXHAUSTED" in error_text
        or "SERVICE_UNAVAILABLE" in error_text
    )

def generate_gemini_response(contents, system_prompt):
    last_error = None
    for index, model_name in enumerate(MODELS):
        attempts = 2 if index == 0 else 1
        for attempt in range(attempts):
            try:
                logger.info("Trying Gemini model: %s (attempt %s)", model_name, attempt + 1)
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.75,
                        max_output_tokens=500
                    )
                )
                reply = response.text
                if not reply:
                    raise RuntimeError("Model returned an empty response.")
                return reply.strip(), model_name
            except Exception as error:
                last_error = error
                logger.warning("Gemini model %s failed: %s", model_name, error)
                if not is_retryable_error(error):
                    raise
                if attempt < attempts - 1:
                    time.sleep(1.5 * (2 ** attempt))
    logger.error("All Gemini models failed: %s", last_error)
    raise RuntimeError("All Gemini models failed.")

def generate_response(contents, system_prompt):
    if groq_client:
        try:
            messages = [{"role": "system", "content": system_prompt}]
            for msg in contents:
                text_content = "".join(part.text or "" for part in msg.parts)
                messages.append({
                    "role": "assistant" if msg.role == "model" else "user",
                    "content": text_content
                })
            logger.info("Trying Groq...")
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_completion_tokens=500
            )
            reply = response.choices[0].message.content
            if reply and reply.strip():
                return reply.strip(), f"Groq / {GROQ_MODEL}"
        except Exception as error:
            logger.warning("Groq failed: %s. Switching to Gemini.", error)

    try:
        reply, model_name = generate_gemini_response(contents, system_prompt)
        return reply, f"Gemini / {model_name}"
    except Exception as error:
        logger.exception("Both AI providers failed: %s", error)
        raise HTTPException(
            status_code=503,
            detail="Our AI services are temporarily unavailable. Please try again shortly."
        )

@app.get("/")
def home():
    return {
        "status": "online",
        "application": "Meet Yash",
        "message": "Your AI conversation with Yash."
    }

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "models_configured": len(MODELS),
        "groq_configured": bool(groq_client),
        "rag_configured": bool(os.getenv("DATABASE_URL") and GEMINI_API_KEY)
    }

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    contents = []
    for msg in request.history[-12:]:
        contents.append(types.Content(
            role=msg.role,
            parts=[types.Part(text=msg.content)]
        ))
    contents.append(types.Content(
        role="user",
        parts=[types.Part(text=request.message)]
    ))

    detected_profile = resolve_profile(request.message)
    if request.profile == "auto":
        effective_profile = detected_profile
    else:
        effective_profile = request.profile

    rag_context, source_refs = retrieve_resume_context(
        query=request.message,
        profile=effective_profile
    )

    system_prompt = build_system_prompt(
        SYSTEM_PROMPT,
        rag_context=rag_context,
        selected_profile=request.profile,
        detected_profile=effective_profile
    )

    try:
        reply, model_used = generate_response(contents, system_prompt)
        return ChatResponse(
            reply=reply,
            model_used=model_used,
            selected_profile=request.profile,
            detected_profile=effective_profile,
            sources=source_refs
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Chat endpoint failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to generate a response. Please try again."
        )
