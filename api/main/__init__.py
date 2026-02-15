from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, List
import os
import json
import re

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
from core_agents.pseudocode_agent import PseudocodeAgent
from fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig

from api.schemas import (
    QueryRequest,
    RetrieveRequest,
    SummarizeRequest,
    DraftRequest,
    PlagiarismRequest,
    RefineBlockRequest,
    DiagramRequest,
    PseudocodeRequest,
    FormatCommandRequest,
    FormatIEEERequest,
    CompilePDFRequest,
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
pseudocode_agent = PseudocodeAgent()


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


def _parse_json_block(text: str) -> Dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _format_with_groq(prompt: str) -> Dict[str, Any] | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            top_p=0.1,
            max_tokens=300,
        )
        content = response.choices[0].message.content.strip()
        return _parse_json_block(content)
    except Exception:
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


@app.post("/api/pseudocode")
def convert_to_pseudocode(req: PseudocodeRequest) -> Dict[str, Any]:
    try:
        return pseudocode_agent.convert_to_pseudocode(req.code, req.algorithm_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/format-commands")
def format_commands(req: FormatCommandRequest) -> Dict[str, Any]:
    try:
        prompt = (
            "You are a layout assistant for academic papers. "
            "Return ONLY strict JSON with this schema: "
            "{\"cssUpdates\": {\"--col-count\": 1}, "
            "\"editorCommands\": [{\"target\": \"abstract\", \"action\": \"toggleBold\"}]}. "
            "Rules: output JSON only, no markdown. "
            "Allowed css keys: --col-count, --col-gap, --font-size, --margin-x, --margin-y. "
            "Allowed editor actions: toggleBold, toggleItalic, toggleHeading1, toggleHeading2. "
            f"Current settings: {req.settings}. "
            f"Available targets: {req.available_targets}. "
            f"User request: {req.prompt}"
        )

        data = _format_with_groq(prompt)
        if not data:
            return {"cssUpdates": {}, "editorCommands": [], "provider": "fallback"}

        css_updates = data.get("cssUpdates", {}) if isinstance(data, dict) else {}
        editor_cmds = data.get("editorCommands", []) if isinstance(data, dict) else []
        if not isinstance(css_updates, dict):
            css_updates = {}
        if not isinstance(editor_cmds, list):
            editor_cmds = []

        normalized_cmds = []
        for cmd in editor_cmds:
            if not isinstance(cmd, dict):
                continue
            target = str(cmd.get("target", "")).strip()
            action = str(cmd.get("action", "")).strip()
            if not target or not action:
                continue
            normalized_cmds.append({"target": target, "action": action})

        return {
            "cssUpdates": css_updates,
            "editorCommands": normalized_cmds,
            "provider": "groq",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _format_ieee_with_ai(raw_text: str, format_type: str) -> Dict[str, Any] | None:
    """Use AI to structure raw text into IEEE format HTML."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or Groq is None:
        return None
    
    prompt = f"""You are an IEEE research paper formatting expert. Convert the following raw text into well-structured HTML for an IEEE {format_type} paper.

CRITICAL RULES:
0. First pass: fix grammar, punctuation, capitalization, and sentence flow while preserving technical meaning.
1. Detect and structure sections: Title, Abstract, Introduction, Methodology, Results, Discussion, Conclusion, References
2. Use this HTML structure:
   - Title: <h1>TITLE HERE</h1>
   - Section headers (I. INTRODUCTION): <h1>I. INTRODUCTION</h1>
   - Subsection headers (A. Background): <h2>A. Background</h2>
   - Paragraphs: <p>text</p>
   - Bold: <strong>text</strong>
   - Italic: <em>text</em>
   - Lists: <ul><li>item</li></ul> or <ol><li>item</li></ol>

3. TABLES - VERY IMPORTANT: Convert ASCII tables or tabular data into proper HTML tables:
   <table>
     <thead><tr><th>Header1</th><th>Header2</th></tr></thead>
     <tbody><tr><td>Data1</td><td>Data2</td></tr></tbody>
   </table>
     - If a table is malformed (inconsistent delimiters/column counts), normalize it:
         - infer separators (|, tabs, commas, multiple spaces)
         - infer header row when present
         - ensure each row has the same number of columns (pad missing cells with empty strings)
         - remove decorative ASCII border rows

4. EQUATIONS - Convert LaTeX/math notation:
   - Inline math like $x^2$ becomes: <em>x²</em>
   - Block equations become: <blockquote><em>Equation: content</em></blockquote>
   - Greek letters: $\\alpha$ → α, $\\beta$ → β, $\\delta$ → δ, $\\lambda$ → λ
   - Subscripts: $x_i$ → x<sub>i</sub>
   - Superscripts: $x^2$ → x<sup>2</sup>

5. For references, format as: <p>[1] Author, "Title," Journal, year.</p>
6. Use Roman numerals (I, II, III) for main sections
7. Use letters (A, B, C) for subsections  
8. Make the abstract content italic with <em>
9. Return ONLY the HTML content, no explanations or markdown code blocks

RAW TEXT:
{raw_text[:12000]}

Return the formatted HTML:"""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000,
        )
        html_content = response.choices[0].message.content.strip()
        
        # Clean up any markdown code blocks
        if html_content.startswith("```"):
            html_content = re.sub(r'^```\w*\n?', '', html_content)
            html_content = re.sub(r'\n?```$', '', html_content)
        
        # Count detected elements
        sections = len(re.findall(r'<h1>', html_content, re.IGNORECASE))
        equations = len(re.findall(r'\[Equation:', html_content))
        references = len(re.findall(r'\[\d+\]', html_content))
        
        return {
            "success": True,
            "formatted_html": html_content,
            "sections_detected": sections,
            "equations_found": equations,
            "references_found": references,
            "provider": "groq"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/format-ieee")
def format_ieee(req: FormatIEEERequest) -> Dict[str, Any]:
    """Format raw text to IEEE paper structure using AI."""
    try:
        result = _format_ieee_with_ai(req.raw_text, req.format_type)
        
        if result and result.get("success"):
            return result
        
        # Fallback: basic formatting without AI
        lines = req.raw_text.strip().split('\n')
        html_parts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect patterns
            if line.isupper() and len(line) < 100:
                html_parts.append(f"<h1>{line}</h1>")
            elif re.match(r'^[IVX]+\.\s', line):
                html_parts.append(f"<h1>{line}</h1>")
            elif re.match(r'^[A-Z]\.\s', line):
                html_parts.append(f"<h2>{line}</h2>")
            elif re.match(r'^\d+\)\s', line):
                html_parts.append(f"<p>{line}</p>")
            else:
                html_parts.append(f"<p>{line}</p>")
        
        return {
            "success": True,
            "formatted_html": "\n".join(html_parts),
            "sections_detected": len([p for p in html_parts if '<h1>' in p]),
            "equations_found": 0,
            "references_found": 0,
            "provider": "fallback",
            "error": result.get("error") if result else "AI unavailable"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


import subprocess
import tempfile
import base64
import shutil


@app.post("/api/compile-pdf")
def compile_pdf(req: CompilePDFRequest) -> Dict[str, Any]:
    """Compile LaTeX to PDF using pdflatex."""
    try:
        # Check if pdflatex is available
        pdflatex_path = shutil.which("pdflatex")
        if not pdflatex_path:
            return {
                "success": False,
                "error": "pdflatex not found. Install TeX Live or MiKTeX to enable PDF compilation.",
                "compilation_log": "pdflatex executable not found in PATH"
            }
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_file = os.path.join(tmpdir, "paper.tex")
            pdf_file = os.path.join(tmpdir, "paper.pdf")
            
            # Write LaTeX file
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(req.latex_code)
            
            # Run pdflatex twice for references
            for _ in range(2):
                result = subprocess.run(
                    [pdflatex_path, "-interaction=nonstopmode", "-output-directory", tmpdir, tex_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            
            # Check if PDF was created
            if os.path.exists(pdf_file):
                with open(pdf_file, 'rb') as f:
                    pdf_bytes = f.read()
                
                return {
                    "success": True,
                    "pdf_base64": base64.b64encode(pdf_bytes).decode('utf-8'),
                    "compilation_log": result.stdout[-2000:] if result.stdout else ""
                }
            else:
                return {
                    "success": False,
                    "error": "PDF compilation failed",
                    "compilation_log": result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
                }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Compilation timeout (60s exceeded)",
            "compilation_log": ""
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "compilation_log": ""
        }

