"""
GitHub-to-IEEE Paper Agent

Fetches a GitHub repository, analyses its contents via an LLM,
and generates a structured IEEE-format research paper with PDF output.
"""

import os
import io
import base64
import json
import re
import requests
import time
from urllib.parse import urlparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


class GitHubPaperAgent:
    """Generates IEEE-format papers from GitHub repositories."""

    def __init__(self, llm_fn=None):
        """
        Args:
            llm_fn: callable(prompt, **kwargs) -> str.
                     Falls back to Groq direct if not provided.
        """
        self._llm = llm_fn or self._default_llm

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _default_llm(prompt: str, **kwargs) -> str:
        """Fallback LLM using shared llm_provider (Ollama -> Groq -> Gemini)."""
        from core_agents.llm_provider import chat_completion
        
        response = chat_completion(
            prompt,
            max_tokens=kwargs.get("max_tokens", 1024),
            temperature=kwargs.get("temperature", 0.25),
        )
        if not response:
            raise RuntimeError("All LLM providers failed to generate a response.")
        return response

    def _chat(
        self,
        prompt: str,
        model: str = "llama-3.3-70b-versatile",
        max_tokens: int = 1024,
        temperature: float = 0.25,
    ) -> str:
        return self._llm(
            prompt, model=model, max_tokens=max_tokens, temperature=temperature
        )

    # ------------------------------------------------------------------
    # GitHub fetching
    # ------------------------------------------------------------------

    @staticmethod
    def parse_repo_url(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Return (owner, repo) from a GitHub URL or (None, None)."""
        url = url.strip().rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        p = urlparse(url)
        if p.netloc != "github.com":
            return None, None
        parts = [x for x in p.path.split("/") if x]
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    @staticmethod
    def _github_headers() -> dict:
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"token {token}"
        return headers

    def fetch_repo(
        self, owner: str, repo: str, max_files: int = 40
    ) -> Dict[str, Any]:
        """Fetch repo metadata, README, file tree and file contents."""
        api = f"https://api.github.com/repos/{owner}/{repo}"
        headers = self._github_headers()

        # --- Repo metadata ---
        r = requests.get(api, headers=headers, timeout=15)
        if r.status_code == 404:
            raise RuntimeError("Repository not found. Check owner/repo name.")
        if r.status_code == 403:
            remaining = r.headers.get("X-RateLimit-Remaining", "0")
            if remaining == "0":
                reset = datetime.fromtimestamp(
                    int(r.headers.get("X-RateLimit-Reset", 0))
                ).strftime("%H:%M:%S")
                raise RuntimeError(
                    f"GitHub API rate limit exceeded. Resets at {reset}. "
                    "Add GITHUB_TOKEN to .env for higher limits."
                )
            raise RuntimeError("GitHub API returned 403 Forbidden.")
        if r.status_code != 200:
            raise RuntimeError(f"GitHub API error: {r.status_code} - {r.reason}")
        meta = r.json()

        # --- README ---
        readme = ""
        try:
            rr = requests.get(f"{api}/readme", headers=headers, timeout=10)
            if rr.status_code == 200:
                readme = base64.b64decode(
                    rr.json().get("content", "")
                ).decode("utf-8", "ignore")
        except Exception:
            pass

        # --- Repo tree ---
        branch = meta.get("default_branch", "main")
        tree_resp = requests.get(
            f"{api}/git/trees/{branch}?recursive=1",
            headers=headers,
            timeout=15,
        )
        if tree_resp.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch repository tree: {tree_resp.status_code}"
            )
        tree = tree_resp.json()

        # Filter relevant source files
        code_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs",
            ".c", ".cpp", ".h", ".rb", ".php", ".swift", ".kt",
            ".md", ".txt", ".yaml", ".yml", ".json", ".toml",
        }
        files = []
        for item in tree.get("tree", []):
            if len(files) >= max_files:
                break
            if item.get("type") != "blob":
                continue
            if item.get("size", 0) > 200_000:
                continue
            ext = os.path.splitext(item["path"])[1].lower()
            if ext in code_extensions:
                files.append(item["path"])

        # --- File contents ---
        contents = []
        for path in files:
            try:
                r = requests.get(
                    f"{api}/contents/{path}", headers=headers, timeout=10
                )
                if r.status_code == 200 and "content" in r.json():
                    text = base64.b64decode(
                        r.json()["content"]
                    ).decode("utf-8", "ignore")
                    contents.append({"path": path, "content": text})
            except Exception:
                continue

        # --- Languages ---
        languages = {}
        try:
            lr = requests.get(f"{api}/languages", headers=headers, timeout=10)
            if lr.status_code == 200:
                languages = lr.json()
        except Exception:
            pass

        return {
            "name": meta.get("name", repo),
            "description": meta.get("description", ""),
            "languages": languages,
            "readme": readme,
            "files": contents,
            "stars": meta.get("stargazers_count", 0),
            "forks": meta.get("forks_count", 0),
        }

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def analyze_repo(self, repo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to extract structured analysis of the repository."""
        prompt = f"""Analyze this GitHub repository for academic paper generation.

Name: {repo_data.get('name')}
Description: {repo_data.get('description')}
Languages: {list(repo_data.get('languages', {}).keys())}
README (first 2000 chars):
{repo_data.get('readme', '')[:2000]}

File listing:
{chr(10).join(f['path'] for f in repo_data.get('files', [])[:30])}

Return ONLY valid JSON (no markdown, no explanation) with these keys:
SYSTEM_PURPOSE, PROPOSED_SOLUTION, KEY_TECHNOLOGIES (array of strings),
PROJECT_TYPE, ARCHITECTURE, INNOVATION, TARGET_DOMAIN, SCALABILITY
"""
        raw = self._chat(
            prompt,
            model="llama-3.1-8b-instant",
            max_tokens=1024,
            temperature=0.2,
        )
        try:
            # Try to extract JSON from response
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                return json.loads(match.group(0))
            return json.loads(raw)
        except Exception:
            return {
                "SYSTEM_PURPOSE": repo_data.get("description", ""),
                "PROPOSED_SOLUTION": "",
                "KEY_TECHNOLOGIES": list(repo_data.get("languages", {}).keys()),
                "PROJECT_TYPE": "",
                "ARCHITECTURE": "",
                "INNOVATION": "",
                "TARGET_DOMAIN": "",
                "SCALABILITY": "",
            }

    # ------------------------------------------------------------------
    # Vector store + paper generation
    # ------------------------------------------------------------------

    def _build_vectorstore(self, repo_data: Dict[str, Any]):
        """Build a FAISS vector store from repo file contents."""
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_huggingface import HuggingFaceEmbeddings

        docs = []
        for f in repo_data.get("files", []):
            docs.append(
                Document(
                    page_content=f["content"],
                    metadata={"source": f["path"]},
                )
            )

        if not docs:
            raise RuntimeError("No files found in the repository to analyze.")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            length_function=len,
        )
        chunks = splitter.split_documents(docs)

        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        return FAISS.from_documents(chunks, embeddings)

    def generate_ieee_paper(
        self,
        repo_data: Dict[str, Any],
        analysis: Dict[str, Any],
        vector_db,
    ) -> Dict[str, str]:
        """Generate all IEEE paper sections using LLM + vector retrieval."""
        sections: Dict[str, str] = {}

        # Title
        title_prompt = f"""Generate a concise IEEE-style paper title.

Project: {repo_data.get('name')}
Domain: {analysis.get('TARGET_DOMAIN', '')}
Technologies: {', '.join(analysis.get('KEY_TECHNOLOGIES', [])[:3])}

Return only the title, no quotes or explanation."""
        sections["title"] = self._chat(
            title_prompt,
            model="llama-3.1-8b-instant",
            max_tokens=80,
            temperature=0.2,
        ).strip().strip('"').strip("'")

        def gen_section(name: str, query: str, words: int, k: int = 4) -> str:
            docs = vector_db.similarity_search(query, k=k)
            context = "\n\n".join(d.page_content for d in docs)
            prompt = f"""Write an IEEE-style {name} section (~{words} words).
Use formal academic language. Do not include section headers.

Project analysis:
- Purpose: {analysis.get('SYSTEM_PURPOSE', '')}
- Solution: {analysis.get('PROPOSED_SOLUTION', '')}
- Technologies: {', '.join(analysis.get('KEY_TECHNOLOGIES', [])[:5])}

Source code context:
{context[:3000]}
"""
            return self._chat(
                prompt,
                model="llama-3.3-70b-versatile",
                max_tokens=words * 2,
                temperature=0.25,
            )

        sections["abstract"] = gen_section(
            "Abstract", "high-level summary and purpose", 200, k=2
        )
        sections["introduction"] = gen_section(
            "Introduction",
            "problem statement, motivation, contributions",
            600,
        )
        sections["methodology"] = gen_section(
            "Methodology", "architecture, algorithms, data flow", 700
        )
        sections["implementation"] = gen_section(
            "Implementation", "core modules and system design", 600
        )
        sections["results"] = gen_section(
            "Results and Evaluation",
            "performance and expected outcomes",
            600,
        )
        sections["conclusion"] = gen_section(
            "Conclusion", "summary and future work", 300
        )

        # References
        refs_prompt = f"""Generate 10 IEEE-style references relevant to:
{sections['title']}

Format each reference as:
[N] Author(s), "Title," Journal/Conference, vol. X, no. Y, pp. ZZ-ZZ, Year.

Return only the references, no other text."""
        sections["references"] = self._chat(
            refs_prompt,
            model="llama-3.3-70b-versatile",
            max_tokens=600,
            temperature=0.2,
        )

        return sections

    # ------------------------------------------------------------------
    # PDF builder
    # ------------------------------------------------------------------

    @staticmethod
    def build_pdf(
        sections: Dict[str, str],
        author: str = "",
        institution: str = "",
    ) -> bytes:
        """Build a PDF from sections and return raw bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "IEEETitle",
            parent=styles["Title"],
            alignment=1,
            fontSize=24,
            spaceAfter=20,
        )
        author_style = ParagraphStyle(
            "IEEEAuthor",
            parent=styles["Heading2"],
            alignment=1,
            fontSize=12,
            spaceAfter=4,
        )
        inst_style = ParagraphStyle(
            "IEEEInst",
            parent=styles["Italic"],
            alignment=1,
            fontSize=10,
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            "IEEEHeading",
            parent=styles["Heading1"],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=16,
        )
        body = styles["Normal"]

        story = []
        story.append(Paragraph(sections.get("title", "Untitled"), title_style))
        if author:
            story.append(Paragraph(author, author_style))
        if institution:
            story.append(Paragraph(institution, inst_style))
        story.append(Spacer(1, 20))

        section_order = [
            ("Abstract", "abstract"),
            ("I. Introduction", "introduction"),
            ("II. Methodology", "methodology"),
            ("III. Implementation", "implementation"),
            ("IV. Results and Evaluation", "results"),
            ("V. Conclusion", "conclusion"),
            ("References", "references"),
        ]

        for heading, key in section_order:
            text = sections.get(key, "")
            if not text:
                continue
            story.append(Paragraph(heading, heading_style))
            for paragraph in text.split("\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    # Escape special XML characters for reportlab
                    paragraph = (
                        paragraph.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    story.append(Paragraph(paragraph, body))
            story.append(Spacer(1, 12))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    # ------------------------------------------------------------------
    # Main pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        repo_url: str,
        author: str = "",
        institution: str = "",
        max_files: int = 40,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        Full pipeline: parse URL → fetch → vectorize → analyze → generate → PDF.

        Returns dict with keys: sections, pdf_base64, repo_name
        """

        def _progress(msg: str):
            if progress_callback:
                progress_callback(msg)

        owner, repo = self.parse_repo_url(repo_url)
        if not owner or not repo:
            raise ValueError("Invalid GitHub URL. Expected format: https://github.com/owner/repo")

        _progress("Fetching repository data...")
        repo_data = self.fetch_repo(owner, repo, max_files=max_files)

        _progress("Building vector database...")
        vector_db = self._build_vectorstore(repo_data)

        _progress("Analyzing repository...")
        analysis = self.analyze_repo(repo_data)

        _progress("Generating IEEE paper sections...")
        sections = self.generate_ieee_paper(repo_data, analysis, vector_db)

        _progress("Building PDF...")
        pdf_bytes = self.build_pdf(sections, author, institution)
        pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

        return {
            "sections": sections,
            "pdf_base64": pdf_b64,
            "repo_name": repo_data.get("name", repo),
            "analysis": analysis,
        }
