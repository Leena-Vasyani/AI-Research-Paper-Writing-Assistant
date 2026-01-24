from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List
import os

try:
    from groq import Groq
except Exception:
    Groq = None

try:
    import google.generativeai as genai
except Exception:
    genai = None

from core_agents.query_agent import ScientificQueryAgent
from core_agents.retrieval_agent import PaperRetrievalAgent
from core_agents.summarization_agent import PaperSummarizationAgent
from core_agents.plagiarism_agent import PlagiarismDetectionAgent
from core_agents.diagram_agent import DiagramAgent
from fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig

from api.schemas import (
    QueryRequest,
    RetrieveRequest,
    SummarizeRequest,
    DraftRequest,
    PlagiarismRequest,
    RefineBlockRequest,
    DiagramRequest,
)

app = FastAPI(title="ResearchGen API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

query_agent = ScientificQueryAgent()
retrieval_agent = PaperRetrievalAgent()
summarization_agent = PaperSummarizationAgent()
plagiarism_agent = PlagiarismDetectionAgent()
diagram_agent = DiagramAgent()


def _refine_with_groq(prompt: str) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            top_p=0.9,
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return None


def _refine_with_gemini(prompt: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or genai is None:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.3, "top_p": 0.9, "max_output_tokens": 400},
        )
        return response.text.strip() if response and response.text else None
    except Exception:
        return None


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.post("/api/query")
def analyze_topic(req: QueryRequest) -> Dict[str, Any]:
    try:
        return query_agent.run(req.text, top_keywords=req.top_keywords)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/retrieve")
def retrieve_papers(req: RetrieveRequest) -> List[Dict[str, Any]]:
    try:
        if req.use_multi_query and req.subtopics:
            return retrieval_agent.retrieve_papers_multi_query(
                req.keywords, req.subtopics, max_results=req.max_results
            )
        return retrieval_agent.retrieve_papers(req.keywords, max_results=req.max_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/summarize")
def summarize(req: SummarizeRequest) -> Dict[str, Any]:
    try:
        return summarization_agent.generate_comprehensive_summary(req.papers, req.keywords)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/draft")
def draft(req: DraftRequest) -> Dict[str, str]:
    try:
        config = DraftingConfig()
        if req.config:
            config.max_new_tokens = req.config.max_new_tokens
            config.min_new_tokens = req.config.min_new_tokens
            config.temperature = req.config.temperature
            config.top_p = req.config.top_p
            config.repetition_penalty = req.config.repetition_penalty
            config.num_beams = req.config.num_beams
            config.no_repeat_ngram_size = req.config.no_repeat_ngram_size

        drafting_agent = get_drafting_agent(config)
        return drafting_agent.generate_complete_draft(
            req.research_topic, req.comprehensive_summary, req.keywords
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plagiarism")
def plagiarism(req: PlagiarismRequest) -> Dict[str, Any]:
    try:
        return plagiarism_agent.check_plagiarism(
            req.generated_draft, req.source_papers, req.research_topic
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refine-block")
def refine_block(req: RefineBlockRequest) -> Dict[str, Any]:
    try:
        mode = req.mode.lower().strip()
        instruction = {
            "expand": "Expand the text into a well-structured paragraph.",
            "academic": "Rewrite the text in formal academic tone.",
            "refine": "Refine clarity and flow without changing meaning.",
        }.get(mode, "Refine clarity and flow without changing meaning.")

        prompt = (
            "You are an academic writing assistant. Do not add new facts. "
            f"{instruction}\n\nText:\n{req.text}"
        )

        output = _refine_with_groq(prompt)
        provider = "groq"
        if not output:
            output = _refine_with_gemini(prompt)
            provider = "gemini"

        if not output:
            output = req.text.strip()
            provider = "fallback"

        return {"refined_text": output, "provider": provider}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diagram")
def generate_diagram(req: DiagramRequest) -> Dict[str, Any]:
    try:
        return diagram_agent.generate_diagram(req.description, req.diagram_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
