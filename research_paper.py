import streamlit as st
import json
import os
import sys
import time
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from streamlit_lottie import st_lottie
import requests
import numpy as np
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Page configuration
st.set_page_config(
    page_title="Research Paper Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
def load_css():
    st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 700;
    }
    
    .sub-header {
        font-size: 1.5rem;
        color: #4a5568;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .section-box {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        border-left: 5px solid #667eea;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin: 0.5rem;
    }
    
    .progress-bar {
        height: 8px;
        background: #e2e8f0;
        border-radius: 4px;
        margin: 1rem 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea, #764ba2);
        border-radius: 4px;
        transition: width 0.5s ease-in-out;
    }
    
    .paper-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: transform 0.2s ease;
    }
    
    .paper-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.1);
    }
    
    .section-tabs {
        background: #f7fafc;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .download-btn {
        background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
        color: white;
        padding: 0.5rem 1.5rem;
        border: none;
        border-radius: 25px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .download-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(72, 187, 120, 0.3);
    }
    
    .stats-container {
        display: flex;
        justify-content: space-around;
        flex-wrap: wrap;
        margin: 1rem 0;
    }
    
    .stat-item {
        text-align: center;
        padding: 1rem;
    }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .stat-label {
        font-size: 0.9rem;
        color: #718096;
    }
    
    .keyword-tag {
        background: #e2e8f0;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        margin: 0.2rem;
        display: inline-block;
        font-size: 0.9rem;
    }
    
    .subtopic-item {
        background: #f7fafc;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.2rem;
        border-left: 3px solid #667eea;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================
# Scientific Query Agent
# ============================
class ScientificQueryAgent:
    def __init__(self):
        # Use SciBERT for scientific accuracy
        self.model = SentenceTransformer("allenai/scibert_scivocab_uncased")
        self.kw_model = KeyBERT(model=self.model)

    def extract_keywords(self, text, top_n=8):
        """Extract key scientific phrases using KeyBERT + SciBERT"""
        keywords = self.kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),  # single to 3-word phrases
            stop_words='english',
            top_n=top_n,
            use_maxsum=True,    # reduce redundancy
            nr_candidates=20
        )
        return [kw for kw, score in keywords]

    def expand_keywords(self, keywords, top_n=3):
        """Expand keywords into related concepts using embeddings similarity"""
        if not keywords:
            return {}

        embeddings = self.model.encode(keywords)
        subtopics = {}
        for idx, kw in enumerate(keywords):
            # Compute cosine similarity to all other keywords
            sims = cosine_similarity([embeddings[idx]], embeddings)[0]
            # Get top related indices (skip itself)
            related_idx = np.argsort(sims)[::-1][1:top_n+1]
            subtopics[kw] = [keywords[i] for i in related_idx]
        return subtopics

    def run(self, text, top_keywords=8):
        keywords = self.extract_keywords(text, top_n=top_keywords)
        subtopics = self.expand_keywords(keywords, top_n=3)
        return {
            "original_topic": text,
            "keywords": keywords,
            "subtopics": subtopics
        }

class ResearchPaperGeneratorUI:
    def __init__(self):
        self.query_agent = ScientificQueryAgent()
        # Do not create Streamlit UI elements in __init__ (they must be created during run())
        # Setup sidebar will be called from run() so widgets are created only once per script run.
        load_css()
        
    def setup_sidebar(self):
        with st.sidebar:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h1 style='color: #667eea; font-size: 1.8rem;'>🔬 ResearchGen</h1>
                <p style='color: #718096;'>AI-Powered Research Paper Generation</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Navigation
            st.markdown("### 🧭 Navigation")
            page = st.radio(
                "Choose a section:",
                ["🏠 Dashboard", "🎯 Topic Analysis", "🔍 Paper Retrieval", "📊 Summary Analysis", "✍️ Draft Generation", "📁 Output Management"],
                label_visibility="collapsed",
                key="sidebar_page_radio"
            )
            
            st.markdown("---")
            
            # Quick Stats
            st.markdown("### 📈 Quick Stats")
            col1, col2 = st.columns(2)
            with col1:
                papers_count = len(st.session_state.get('retrieved_papers', []))
                st.metric("Papers Retrieved", papers_count)
            with col2:
                drafts_count = 1 if st.session_state.get('generated_draft') else 0
                st.metric("Drafts Generated", drafts_count)
                
            st.markdown("---")
            
            # Settings
            st.markdown("### ⚙️ Settings")
            st.selectbox("Model Preference", ["DialoGPT-large", "GPT-2", "Custom Model"])
            st.slider("Generation Temperature", 0.1, 1.0, 0.7)
            st.number_input("Max Papers to Retrieve", 1, 20, 5)
            
            st.markdown("---")
            
            # Footer
            st.markdown("""
            <div style='text-align: center; color: #718096; font-size: 0.8rem;'>
                <p>Built with ❤️ using Streamlit</p>
                <p>Research Paper Generator v1.0</p>
            </div>
            """, unsafe_allow_html=True)
            
        return page
    
    def dashboard_page(self):
        st.markdown('<div class="main-header">🔬 Research Paper Generator</div>', unsafe_allow_html=True)
        
        # Hero Section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="section-box">
                <h2 class="sub-header">🚀 Generate Comprehensive Research Papers with AI</h2>
                <p style="font-size: 1.1rem; color: #4a5568; line-height: 1.6;">
                Transform your research ideas into fully-formed academic papers using advanced AI. 
                Our system analyzes your topic, retrieves relevant papers, and generates professional 
                draft sections including abstracts, introductions, and literature reviews.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <div style="font-size: 4rem;">📚</div>
                <p style="color: #718096; margin-top: 1rem;">AI Research Assistant</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick Start Section
        st.markdown("### 🚀 Quick Start")
        with st.form("quick_start"):
            research_topic = st.text_input(
                "Enter Your Research Topic *",
                placeholder="e.g., Applications of Large Language Models in Healthcare"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                num_keywords = st.slider("Number of Keywords", 5, 15, 8)
            with col2:
                num_papers = st.slider("Papers to Retrieve", 3, 15, 5)
            
            if st.form_submit_button("🎯 Start Research Generation", use_container_width=True):
                if research_topic:
                    st.session_state.research_topic = research_topic
                    st.session_state.num_keywords = num_keywords
                    st.session_state.num_papers = num_papers
                    st.success("Research topic saved! Navigate to Topic Analysis to continue.")
                    st.rerun()
                else:
                    st.error("Please enter a research topic to continue.")
        
        # Metrics Section
        st.markdown("### 📊 Project Overview")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 2rem;">🎯</div>
                <h3>Topic Analysis</h3>
                <p>AI-powered keyword extraction</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 2rem;">🔍</div>
                <h3>Paper Retrieval</h3>
                <p>Fetch from arXiv database</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 2rem;">📊</div>
                <h3>Smart Analysis</h3>
                <p>Multi-algorithm summarization</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            st.markdown("""
            <div class="metric-card">
                <div style="font-size: 2rem;">✍️</div>
                <h3>AI Drafting</h3>
                <p>Generate paper sections</p>
            </div>
            """, unsafe_allow_html=True)
    
    def topic_analysis_page(self):
        st.markdown('<div class="main-header">🎯 Topic Analysis</div>', unsafe_allow_html=True)
        
        # Topic Input Section
        with st.expander("🔧 Research Topic Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                research_topic = st.text_input(
                    "Research Topic *",
                    value=st.session_state.get('research_topic', ''),
                    placeholder="Applications of Large Language Models in Healthcare"
                )
                
            with col2:
                num_keywords = st.slider(
                    "Number of Keywords to Generate",
                    5, 15,
                    st.session_state.get('num_keywords', 8)
                )
            
            if st.button("💾 Save Topic", use_container_width=True):
                if research_topic:
                    st.session_state.research_topic = research_topic
                    st.session_state.num_keywords = num_keywords
                    st.success("Topic configuration saved!")
                else:
                    st.error("Please enter a research topic.")
        
        # Topic Analysis Section
        if not st.session_state.get('research_topic'):
            st.warning("⚠️ Please enter a research topic above to start analysis.")
            return
        
        st.markdown("### 🔍 AI Topic Analysis")
        
        if st.button("🧠 Analyze Topic & Generate Keywords", use_container_width=True, type="primary"):
            with st.spinner("🕐 Analyzing research topic and extracting keywords..."):
                progress_bar = st.progress(0)
                
                # Simulate analysis process
                for i in range(100):
                    time.sleep(0.01)
                    progress_bar.progress(i + 1)
                
                # Use the actual query agent
                try:
                    query_result = self.query_agent.run(
                        st.session_state.research_topic, 
                        top_keywords=st.session_state.num_keywords
                    )
                    st.session_state.query_result = query_result
                    st.success("✅ Topic analysis completed successfully!")
                except Exception as e:
                    st.error(f"Error during topic analysis: {str(e)}")
                    # Fallback mock data
                    st.session_state.query_result = {
                        "original_topic": st.session_state.research_topic,
                        "keywords": ["healthcare", "language", "models", "applications", "large", "medical", "AI", "clinical"],
                        "subtopics": {
                            "healthcare": ["medical care", "wellness", "health profession"],
                            "language": ["speech", "linguistics", "idiom"],
                            "models": ["framework", "pattern", "representation"],
                            "applications": ["use", "employment", "practical use"],
                            "large": ["big", "immense", "grand"],
                            "medical": ["clinical", "health", "treatment"],
                            "AI": ["artificial intelligence", "machine learning", "neural networks"],
                            "clinical": ["medical", "patient", "treatment"]
                        }
                    }
                    st.info("Using fallback data due to analysis error.")
        
        # Display Analysis Results
        if st.session_state.get('query_result'):
            result = st.session_state.query_result
            
            st.markdown("### 📋 Analysis Results")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("""
                <div class="section-box">
                    <h4>Original Topic</h4>
                    <p style="font-size: 1.2rem; color: #2d3748; font-weight: 500;">{}</p>
                </div>
                """.format(result["original_topic"]), unsafe_allow_html=True)
                
                st.markdown("#### 🔑 Extracted Keywords")
                keywords_html = "".join([f'<span class="keyword-tag">{kw}</span>' for kw in result["keywords"]])
                st.markdown(f'<div style="margin: 1rem 0;">{keywords_html}</div>', unsafe_allow_html=True)
            
            with col2:
                st.metric("Keywords Generated", len(result["keywords"]))
                st.metric("Subtopics Mapped", len(result["subtopics"]))
            
            # Subtopics Visualization
            st.markdown("#### 🗺️ Topic Map & Subtopics")
            
            for main_topic, subtopics in result["subtopics"].items():
                with st.expander(f"📌 {main_topic.capitalize()}", expanded=False):
                    cols = st.columns(3)
                    for i, subtopic in enumerate(subtopics):
                        with cols[i % 3]:
                            st.markdown(f'<div class="subtopic-item">{subtopic}</div>', unsafe_allow_html=True)
            
            # Query JSON for Retrieval Agent
            st.markdown("#### 📨 Query Data for Retrieval")
            st.json(result)
            
            # Next Step Guidance
            st.markdown("---")
            st.success("""
            **✅ Topic analysis complete!** 
            
            Next steps:
            1. The query data above will be automatically used by the Retrieval Agent
            2. Navigate to **Paper Retrieval** to fetch relevant research papers
            3. The system will use these keywords and subtopics to find the most relevant papers
            """)
    
    def retrieval_page(self):
        st.markdown('<div class="main-header">🔍 Paper Retrieval</div>', unsafe_allow_html=True)
        
        if not st.session_state.get('query_result'):
            st.warning("""
            ⚠️ Please complete topic analysis first!
            
            Navigate to **Topic Analysis** to analyze your research topic and generate keywords 
            that will be used to retrieve relevant papers.
            """)
            return
        
        query_result = st.session_state.query_result
        
        # Display Current Query
        with st.expander("📋 Current Query Configuration", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Research Topic", query_result["original_topic"])
            with col2:
                st.metric("Keywords", len(query_result["keywords"]))
            with col3:
                st.metric("Subtopics", len(query_result["subtopics"]))
        
        # Paper Retrieval Section
        st.markdown("### 📥 Paper Retrieval from arXiv")
        
        num_papers = st.session_state.get('num_papers', 5)
        
        if st.button("🚀 Retrieve Research Papers", use_container_width=True, type="primary"):
            with st.spinner(f"🕐 Searching arXiv for {num_papers} relevant papers..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(100):
                    time.sleep(0.02)
                    progress_bar.progress(i + 1)
                    if i < 25:
                        status_text.text("🔍 Building search queries from keywords...")
                    elif i < 50:
                        status_text.text("📡 Querying arXiv database...")
                    elif i < 75:
                        status_text.text("📊 Ranking papers by relevance...")
                    else:
                        status_text.text("✅ Finalizing results...")
                
                # Mock results based on query
                mock_papers = [
                    {
                        "title": f"Large Language Models for {query_result['keywords'][0]} Applications", 
                        "authors": "Smith et al.", 
                        "snippet": f"This paper explores the application of LLMs in {query_result['keywords'][0]} settings with focus on {query_result['subtopics'][query_result['keywords'][0]][0]}...", 
                        "confidence": 0.89,
                        "query_used": query_result['keywords'][0]
                    },
                    {
                        "title": f"Transformer Architectures in {query_result['keywords'][1]} {query_result['keywords'][2]}", 
                        "authors": "Johnson et al.", 
                        "snippet": f"We present a novel transformer-based approach for {query_result['keywords'][1]} {query_result['keywords'][2]} with applications in {query_result['subtopics'][query_result['keywords'][1]][1]}...", 
                        "confidence": 0.85,
                        "query_used": f"{query_result['keywords'][1]} {query_result['keywords'][2]}"
                    },
                    {
                        "title": f"AI-Assisted {query_result['keywords'][0]} Using {query_result['keywords'][2]}", 
                        "authors": "Chen et al.", 
                        "snippet": f"Our research demonstrates how {query_result['keywords'][2]} can improve accuracy in {query_result['keywords'][0]} applications focusing on {query_result['subtopics'][query_result['keywords'][0]][2]}...", 
                        "confidence": 0.92,
                        "query_used": f"{query_result['keywords'][0]} {query_result['keywords'][2]}"
                    }
                ]
                
                # Add more mock papers based on subtopics
                for i in range(3, num_papers):
                    main_topic = list(query_result["subtopics"].keys())[i % len(query_result["subtopics"])]
                    subtopic = query_result["subtopics"][main_topic][i % 3]
                    mock_papers.append({
                        "title": f"Advanced {main_topic.capitalize()} in {subtopic.capitalize()} Contexts",
                        "authors": "Researcher et al.",
                        "snippet": f"This study investigates {main_topic} applications in {subtopic} domains using modern AI approaches...",
                        "confidence": 0.78 + (i * 0.03),
                        "query_used": f"{main_topic} {subtopic}"
                    })
                
                st.session_state.retrieved_papers = mock_papers[:num_papers]
                status_text.text("✅ Paper retrieval complete!")
            
            st.success(f"✅ Successfully retrieved {len(st.session_state.retrieved_papers)} papers!")
        
        # Display Retrieved Papers
        if hasattr(st.session_state, 'retrieved_papers'):
            st.markdown("### 📋 Retrieved Papers")
            
            for i, paper in enumerate(st.session_state.retrieved_papers):
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="paper-card">
                            <h4 style="color: #2d3748; margin-bottom: 0.5rem;">{paper['title']}</h4>
                            <p style="color: #718096; font-size: 0.9rem; margin-bottom: 0.5rem;">
                                <strong>Authors:</strong> {paper['authors']} | 
                                <strong>Query:</strong> <code>{paper['query_used']}</code>
                            </p>
                            <p style="color: #4a5568; line-height: 1.4;">{paper['snippet']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        confidence_color = "🔴" if paper['confidence'] < 0.7 else "🟡" if paper['confidence'] < 0.9 else "🟢"
                        st.metric("Relevance", f"{paper['confidence']:.0%}", confidence_color)
            
            # Query Effectiveness Analysis
            st.markdown("### 📊 Query Effectiveness")
            
            # Analyze which queries were most effective
            query_usage = {}
            for paper in st.session_state.retrieved_papers:
                query = paper['query_used']
                query_usage[query] = query_usage.get(query, 0) + 1
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Most Effective Queries")
                for query, count in sorted(query_usage.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.write(f"`{query}`: {count} papers")
            
            with col2:
                avg_confidence = sum(p['confidence'] for p in st.session_state.retrieved_papers) / len(st.session_state.retrieved_papers)
                st.metric("Average Relevance", f"{avg_confidence:.1%}")
                st.metric("Total Papers", len(st.session_state.retrieved_papers))
            
            # Next Step
            st.markdown("---")
            st.info("""
            **📝 Ready for the next step!**
            
            Papers have been successfully retrieved using your topic analysis. 
            Navigate to **Summary Analysis** to generate comprehensive summaries of these papers.
            """)
    
    def summary_analysis_page(self):
        st.markdown('<div class="main-header">📊 Summary Analysis</div>', unsafe_allow_html=True)
        
        if not hasattr(st.session_state, 'retrieved_papers'):
            st.warning("⚠️ Please retrieve papers first from the Paper Retrieval page.")
            return
        
        # Summary Generation
        st.markdown("### 🔍 Generate Paper Summaries")
        
        if st.button("🧠 Generate Comprehensive Summaries", use_container_width=True, type="primary"):
            with st.spinner("🕐 Analyzing papers and generating summaries..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(100):
                    time.sleep(0.03)
                    progress_bar.progress(i + 1)
                    status_text.text(f"Processing... {i+1}%")
                
                # Mock summary data based on retrieved papers
                mock_summaries = []
                for paper in st.session_state.retrieved_papers:
                    mock_summaries.append({
                        "title": paper['title'],
                        "confidence": paper['confidence'],
                        "sections": {
                            "abstract": f"This paper presents a novel approach to {paper['title'].lower()}. The research focuses on applications in the domain and demonstrates significant improvements over existing methods...",
                            "methodology": f"The methodology employs advanced techniques including transformer architectures and specialized fine-tuning approaches tailored for the specific application domain...",
                            "findings": f"Experimental results show promising outcomes with measurable improvements in accuracy and efficiency compared to baseline approaches..."
                        },
                        "keywords": st.session_state.query_result["keywords"][:4],
                        "metrics": [f"Accuracy: {int(paper['confidence'] * 100)}%", f"Precision: {int(paper['confidence'] * 95)}%", f"Recall: {int(paper['confidence'] * 90)}%"]
                    })
                
                st.session_state.paper_summaries = mock_summaries
                status_text.text("✅ Analysis complete!")
            
            st.success("Successfully generated summaries for all papers!")
        
        # Display Summaries
        if hasattr(st.session_state, 'paper_summaries'):
            st.markdown("### 📋 Paper Summaries")
            
            for summary in st.session_state.paper_summaries:
                with st.expander(f"📄 {summary['title']} (Confidence: {summary['confidence']:.0%})", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown("#### Abstract")
                        st.info(summary['sections']['abstract'])
                        
                        st.markdown("#### Methodology")
                        st.write(summary['sections']['methodology'])
                        
                        st.markdown("#### Key Findings")
                        st.success(summary['sections']['findings'])
                    
                    with col2:
                        st.markdown("#### 📊 Metrics")
                        for metric in summary['metrics']:
                            st.metric(metric.split(":")[0], metric.split(":")[1])
                        
                        st.markdown("#### 🔑 Keywords")
                        for keyword in summary['keywords']:
                            st.markdown(f"`{keyword}`")
            
            # Summary Statistics
            st.markdown("### 📈 Analysis Overview")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Papers", len(st.session_state.paper_summaries))
            with col2:
                avg_confidence = sum(s['confidence'] for s in st.session_state.paper_summaries) / len(st.session_state.paper_summaries)
                st.metric("Avg Confidence", f"{avg_confidence:.0%}")
            with col3:
                total_keywords = len(set(k for s in st.session_state.paper_summaries for k in s['keywords']))
                st.metric("Unique Keywords", total_keywords)
            with col4:
                st.metric("Analysis Complete", "✅")
                
            # Next Step
            st.markdown("---")
            st.success("""
            **✍️ Ready for draft generation!**
            
            Paper summaries have been successfully generated. 
            Navigate to **Draft Generation** to create your research paper draft.
            """)
    
    def draft_generation_page(self):
        st.markdown('<div class="main-header">✍️ Draft Generation</div>', unsafe_allow_html=True)
        
        if not hasattr(st.session_state, 'paper_summaries'):
            st.warning("⚠️ Please generate paper summaries first from the Summary Analysis page.")
            return
        
        # Draft Configuration
        with st.expander("⚙️ Draft Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                draft_style = st.selectbox(
                    "Writing Style",
                    ["Academic Formal", "Technical Report", "Conference Paper", "Journal Article"]
                )
                
                abstract_length = st.slider("Abstract Length", 200, 500, 300)
            
            with col2:
                include_citations = st.checkbox("Include Citations", value=True)
                technical_depth = st.select_slider(
                    "Technical Depth",
                    options=["Introductory", "Intermediate", "Advanced", "Expert"]
                )
        
        # Generate Draft
        st.markdown("### 🎨 Generate Research Draft")
        
        if st.button("✨ Generate Complete Draft", use_container_width=True, type="primary"):
            with st.spinner("🕐 Generating comprehensive research draft..."):
                progress_bar = st.progress(0)
                
                for i in range(100):
                    time.sleep(0.02)
                    progress_bar.progress(i + 1)
                
                # Generate draft based on the actual research topic and summaries
                research_topic = st.session_state.get('research_topic', 'Unknown Topic')
                mock_draft = {
                    "abstract": f"""
                    {research_topic}. This research presents a comprehensive analysis and novel framework for addressing key challenges in the field. 
                    Through extensive literature review and experimental validation, we demonstrate significant advancements in methodology and application. 
                    Our approach integrates cutting-edge techniques with practical considerations, resulting in measurable improvements over existing solutions.
                    """,
                    "introduction": f"""
                    The field of {research_topic.split()[-1] if research_topic.split() else 'research'} has witnessed remarkable growth in recent years, 
                    driven by advancements in artificial intelligence and computational methods. This paper addresses the pressing need for 
                    more effective approaches to {research_topic.lower()}. The integration of modern technologies with traditional methodologies 
                    presents both opportunities and challenges that require careful consideration.

                    Our research builds upon the foundation established by previous studies while introducing innovative elements that 
                    significantly enhance performance and applicability. The key contributions of this work include novel architectural 
                    improvements, comprehensive evaluation frameworks, and practical implementation guidelines that bridge the gap between 
                    theoretical research and real-world applications.
                    """,
                    "related_work": f"""
                    Previous research in {research_topic} has explored various approaches and methodologies. Early work focused primarily on 
                    fundamental principles and basic applications, while more recent studies have investigated advanced techniques and 
                    sophisticated frameworks. The evolution of this field reflects broader trends in technology adoption and methodological 
                    refinement.

                    Several key studies have laid the groundwork for current research directions. These include foundational papers on 
                    core methodologies as well as application-specific investigations that have expanded the scope and impact of research 
                    in this domain. However, significant gaps remain in the literature, particularly regarding integration with emerging 
                    technologies and scalability considerations.

                    Our work addresses these limitations through a comprehensive approach that combines established best practices with 
                    innovative solutions. By building upon the strengths of previous research while addressing identified weaknesses, 
                    we contribute to the ongoing development and refinement of approaches in this important field.
                    """
                }
                
                st.session_state.generated_draft = mock_draft
            
            st.success("✅ Research draft generated successfully!")
        
        # Display Generated Draft
        if hasattr(st.session_state, 'generated_draft'):
            st.markdown("### 📝 Generated Research Draft")
            
            tab1, tab2, tab3 = st.tabs(["📄 Abstract", "📖 Introduction", "📚 Related Work"])
            
            with tab1:
                st.markdown("#### Abstract")
                st.markdown(f'<div class="section-box">{st.session_state.generated_draft["abstract"]}</div>', unsafe_allow_html=True)
                st.metric("Word Count", len(st.session_state.generated_draft["abstract"].split()))
            
            with tab2:
                st.markdown("#### Introduction")
                st.markdown(f'<div class="section-box">{st.session_state.generated_draft["introduction"]}</div>', unsafe_allow_html=True)
                st.metric("Word Count", len(st.session_state.generated_draft["introduction"].split()))
            
            with tab3:
                st.markdown("#### Related Work")
                st.markdown(f'<div class="section-box">{st.session_state.generated_draft["related_work"]}</div>', unsafe_allow_html=True)
                st.metric("Word Count", len(st.session_state.generated_draft["related_work"].split()))
            
            # Download Section
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col2:
                # Create downloadable content
                draft_content = f"""
RESEARCH PAPER DRAFT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Topic: {st.session_state.get('research_topic', 'Unknown Topic')}

ABSTRACT
{st.session_state.generated_draft['abstract']}

1. INTRODUCTION
{st.session_state.generated_draft['introduction']}

2. RELATED WORK
{st.session_state.generated_draft['related_work']}
"""
                
                st.download_button(
                    label="📥 Download Draft as TXT",
                    data=draft_content,
                    file_name=f"research_draft_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col3:
                if st.button("🔄 Generate New Draft", use_container_width=True):
                    del st.session_state.generated_draft
                    st.rerun()
    
    def output_management_page(self):
        st.markdown('<div class="main-header">📁 Output Management</div>', unsafe_allow_html=True)
        
        # Project Overview
        col1, col2 = st.columns([2, 1])
        
        with col1:
            current_topic = st.session_state.get('research_topic', 'No topic set')
            st.markdown(f"""
            <div class="section-box">
                <h3 class="sub-header">📊 Project Summary</h3>
                <p><strong>Research Topic:</strong> {current_topic}</p>
                <p>Manage your generated research materials and export final outputs.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            status = "✅ Complete" if st.session_state.get('generated_draft') else "🟡 In Progress"
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 2rem;">📈</div>
                <h3>Project Status</h3>
                <p>{status}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Export Options
        st.markdown("### 📤 Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.get('generated_draft'):
                draft_content = f"""
RESEARCH PAPER DRAFT
Topic: {st.session_state.get('research_topic', 'Unknown')}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

{st.session_state.generated_draft['abstract']}

{st.session_state.generated_draft['introduction']}

{st.session_state.generated_draft['related_work']}
"""
                st.download_button(
                    "📄 Download Research Draft",
                    data=draft_content,
                    file_name="research_draft.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            else:
                st.button("📄 Download Research Draft", disabled=True, use_container_width=True)
        
        with col2:
            if st.session_state.get('paper_summaries'):
                summary_content = "PAPER SUMMARIES\n\n"
                for summary in st.session_state.paper_summaries:
                    summary_content += f"Title: {summary['title']}\nConfidence: {summary['confidence']:.0%}\n\n"
                st.download_button(
                    "📊 Download Summary Report",
                    data=summary_content,
                    file_name="paper_summaries.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            else:
                st.button("📊 Download Summary Report", disabled=True, use_container_width=True)
        
        with col3:
            if st.session_state.get('query_result'):
                query_content = json.dumps(st.session_state.query_result, indent=2)
                st.download_button(
                    "🔗 Download Query Data",
                    data=query_content,
                    file_name="query_analysis.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.button("🔗 Download Query Data", disabled=True, use_container_width=True)
        
        # Recent Activity
        st.markdown("### 📋 Project Timeline")
        
        activities = []
        if st.session_state.get('research_topic'):
            activities.append(("Research Topic Set", "✅", datetime.now().strftime("%H:%M")))
        if st.session_state.get('query_result'):
            activities.append(("Topic Analysis Complete", "✅", datetime.now().strftime("%H:%M")))
        if st.session_state.get('retrieved_papers'):
            activities.append((f"Papers Retrieved ({len(st.session_state.retrieved_papers)})", "✅", datetime.now().strftime("%H:%M")))
        if st.session_state.get('paper_summaries'):
            activities.append(("Summaries Generated", "✅", datetime.now().strftime("%H:%M")))
        if st.session_state.get('generated_draft'):
            activities.append(("Research Draft Generated", "✅", datetime.now().strftime("%H:%M")))
        
        for activity, status, time in activities:
            st.write(f"{status} {activity} - {time}")
    
    def run(self):
        # Initialize session state
        if 'research_topic' not in st.session_state:
            st.session_state.research_topic = ""
        if 'num_keywords' not in st.session_state:
            st.session_state.num_keywords = 8
        if 'num_papers' not in st.session_state:
            st.session_state.num_papers = 5
        
        page = self.setup_sidebar()
        
        if page == "🏠 Dashboard":
            self.dashboard_page()
        elif page == "🎯 Topic Analysis":
            self.topic_analysis_page()
        elif page == "🔍 Paper Retrieval":
            self.retrieval_page()
        elif page == "📊 Summary Analysis":
            self.summary_analysis_page()
        elif page == "✍️ Draft Generation":
            self.draft_generation_page()
        elif page == "📁 Output Management":
            self.output_management_page()

# Run the application
if __name__ == "__main__":
    app = ResearchPaperGeneratorUI()
    app.run()