from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List

from core_agents.query_agent import ScientificQueryAgent
from core_agents.retrieval_agent import PaperRetrievalAgent
from core_agents.summarization_agent import PaperSummarizationAgent
from core_agents.plagiarism_agent import PlagiarismDetectionAgent
from fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig

from api.schemas import (
    QueryRequest,
    RetrieveRequest,
    SummarizeRequest,
    DraftRequest,
    PlagiarismRequest,
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
