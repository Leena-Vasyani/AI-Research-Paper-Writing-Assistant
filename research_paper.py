import streamlit as st
import json
import time
from datetime import datetime

# Import all agents
from core_agents.query_agent import ScientificQueryAgent
from core_agents.retrieval_agent import PaperRetrievalAgent
from core_agents.summarization_agent import PaperSummarizationAgent
from core_agents.training_data_manager import TrainingDataManager
from fine_tuning.drafting_agent_trainer import auto_train_if_ready
from fine_tuning.fine_tuned_drafting_agent import get_drafting_agent, DraftingConfig

# Page configuration
st.set_page_config(
    page_title="Research Paper Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    .section-box {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
        border-left: 5px solid #667eea;
    }
    .paper-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .keyword-tag {
        background: #e2e8f0;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        margin: 0.2rem;
        display: inline-block;
    }
    .model-badge {
        background: #d4edda;
        color: #155724;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    .summary-section {
        background: #f8fafc;
        border-left: 4px solid #4299e1;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 8px;
    }
    .insight-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

class ResearchPaperGeneratorUI:
    def __init__(self):
        # Initialize all agents
        self.query_agent = ScientificQueryAgent()
        self.retrieval_agent = PaperRetrievalAgent()
        self.summarization_agent = PaperSummarizationAgent()
        self.data_manager = TrainingDataManager()
        load_css()
        
    def setup_sidebar(self):
        with st.sidebar:
            st.markdown("""
            <div style='text-align: center; margin-bottom: 2rem;'>
                <h1 style='color: #667eea;'>🔬 ResearchGen</h1>
                <p style='color: #718096;'>Real-time AI Research Assistant</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Navigation
            page = st.radio(
                "Navigation",
                ["🏠 Dashboard", "🎯 Topic Analysis", "🔍 Paper Retrieval", 
                 "📊 Summary Analysis", "✍️ Draft Generation", "📁 Output Management"],
                label_visibility="collapsed"
            )
            
            st.markdown("---")
            
            # Quick Stats
            st.markdown("### 📈 Quick Stats")
            col1, col2 = st.columns(2)
            with col1:
                papers_count = len(st.session_state.get('retrieved_papers', []))
                st.metric("Papers", papers_count)
            with col2:
                drafts_count = 1 if st.session_state.get('generated_draft') else 0
                st.metric("Drafts", drafts_count)
                
            st.markdown("---")
            
            # Training Status
            st.markdown("### 🎯 AI Training")
            stats = self.data_manager.get_training_statistics()
            
            st.metric("Research Projects", stats['total_samples'])
            st.metric("Total References", stats['total_references'])
            
            if stats['total_samples'] > 0:
                progress = min(stats['total_samples'] / 5, 1.0)
                st.progress(progress)
                st.caption(f"{stats['total_samples']}/5 projects")
            
            if stats['total_samples'] >= 3:
                if st.button("🚀 Train AI Model", use_container_width=True):
                    st.session_state.training_triggered = True
            
            st.markdown("---")
            
            # Footer
            st.markdown("""
            <div style='text-align: center; color: #718096; font-size: 0.8rem;'>
                <p>Real-time Research Generator</p>
                <p>Powered by arXiv & Transformers</p>
            </div>
            """, unsafe_allow_html=True)
            
        return page
    
    def dashboard_page(self):
        st.markdown('<div class="main-header">🔬 Research Paper Generator</div>', unsafe_allow_html=True)
        
        # Training trigger
        if st.session_state.get('training_triggered'):
            with st.sidebar:
                with st.spinner("🔄 Training AI with your research data..."):
                    try:
                        if auto_train_if_ready():
                            st.success("🎉 AI trained successfully!")
                        else:
                            st.warning("Need more projects (3+)")
                    except Exception as e:
                        st.error(f"Training failed: {e}")
                    st.session_state.training_triggered = False
        
        # Hero Section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="section-box">
                <h2>🚀 Real-time Research Paper Generation</h2>
                <p style="font-size: 1.1rem; line-height: 1.6;">
                Generate comprehensive research papers using real data from arXiv. 
                Our system retrieves actual papers, generates summaries using NLP, 
                and creates professional drafts with AI.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 2rem;">
                <div style="font-size: 4rem;">📚</div>
                <p>Real Data • Real AI</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Quick Start
        st.markdown("### 🚀 Quick Start")
        with st.form("quick_start"):
            research_topic = st.text_input(
                "Research Topic *",
                placeholder="e.g., Large Language Models in Healthcare"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                num_keywords = st.slider("Keywords", 5, 15, 8)
            with col2:
                num_papers = st.slider("Papers", 3, 15, 5)
            
            if st.form_submit_button("🎯 Start Generation", use_container_width=True):
                if research_topic:
                    st.session_state.research_topic = research_topic
                    st.session_state.num_keywords = num_keywords
                    st.session_state.num_papers = num_papers
                    st.success("✅ Topic saved! Go to Topic Analysis →")
                    st.rerun()
                else:
                    st.error("Please enter a topic")
    
    def topic_analysis_page(self):
        st.markdown('<div class="main-header">🎯 Topic Analysis</div>', unsafe_allow_html=True)
        
        # Configuration
        with st.expander("🔧 Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                research_topic = st.text_input(
                    "Research Topic",
                    value=st.session_state.get('research_topic', ''),
                    placeholder="Enter your research topic"
                )
                
            with col2:
                num_keywords = st.slider(
                    "Keywords to Extract",
                    5, 15,
                    st.session_state.get('num_keywords', 8)
                )
            
            if st.button("💾 Save", use_container_width=True):
                if research_topic:
                    st.session_state.research_topic = research_topic
                    st.session_state.num_keywords = num_keywords
                    st.success("Saved!")
                else:
                    st.error("Enter a topic")
        
        if not st.session_state.get('research_topic'):
            st.warning("⚠️ Please enter a research topic above")
            return
        
        st.markdown("### 🔍 AI Analysis")
        
        if st.button("🧠 Analyze Topic", use_container_width=True, type="primary"):
            with st.spinner("Analyzing with SciBERT..."):
                progress_bar = st.progress(0)
                
                try:
                    # REAL analysis using SciBERT
                    for i in range(50):
                        time.sleep(0.01)
                        progress_bar.progress((i + 1) * 2)
                    
                    query_result = self.query_agent.run(
                        st.session_state.research_topic,
                        top_keywords=st.session_state.num_keywords
                    )
                    st.session_state.query_result = query_result
                    st.success("✅ Analysis complete!")
                    
                except Exception as e:
                    st.error(f"Analysis error: {str(e)}")
                    st.info("Please check your internet connection")
        
        # Display Results
        if st.session_state.get('query_result'):
            result = st.session_state.query_result
            
            st.markdown("### 📋 Results")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                <div class="section-box">
                    <h4>Topic</h4>
                    <p style="font-size: 1.2rem;">{result["original_topic"]}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("#### 🔑 Keywords")
                keywords_html = "".join([f'<span class="keyword-tag">{kw}</span>' 
                                        for kw in result["keywords"]])
                st.markdown(f'<div>{keywords_html}</div>', unsafe_allow_html=True)
            
            with col2:
                st.metric("Keywords", len(result["keywords"]))
                st.metric("Subtopics", len(result["subtopics"]))
            
            st.markdown("---")
            st.success("✅ Ready! Navigate to **Paper Retrieval** →")
    
    def retrieval_page(self):
        st.markdown('<div class="main-header">🔍 Paper Retrieval</div>', unsafe_allow_html=True)
        
        if not st.session_state.get('query_result'):
            st.warning("⚠️ Complete topic analysis first!")
            return
        
        query_result = st.session_state.query_result
        
        st.markdown("### 📥 Retrieve from arXiv")
        
        num_papers = st.session_state.get('num_papers', 5)
        
        if st.button("🚀 Retrieve Papers", use_container_width=True, type="primary"):
            with st.spinner(f"Fetching {num_papers} papers from arXiv..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    status_text.text("🔍 Building search query...")
                    progress_bar.progress(20)
                    
                    # REAL arXiv retrieval
                    status_text.text("📡 Querying arXiv API...")
                    progress_bar.progress(40)
                    
                    papers = self.retrieval_agent.retrieve_papers_multi_query(
                        query_result['keywords'],
                        query_result['subtopics'],
                        max_results=num_papers
                    )
                    
                    progress_bar.progress(80)
                    status_text.text("📊 Ranking papers...")
                    
                    # Calculate relevance scores
                    for paper in papers:
                        paper['relevance'] = self.retrieval_agent.calculate_relevance_score(
                            paper, query_result['keywords']
                        )
                    
                    # Sort by relevance
                    papers.sort(key=lambda x: x['relevance'], reverse=True)
                    
                    st.session_state.retrieved_papers = papers
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")
                    
                    st.success(f"✅ Retrieved {len(papers)} real papers from arXiv!")
                    
                except Exception as e:
                    st.error(f"Retrieval error: {str(e)}")
                    st.info("Check internet connection or try fewer papers")
        
        # Display Papers
        if hasattr(st.session_state, 'retrieved_papers'):
            st.markdown(f"### 📋 Retrieved Papers ({len(st.session_state.retrieved_papers)})")
            
            for i, paper in enumerate(st.session_state.retrieved_papers, 1):
                with st.expander(f"📄 {i}. {paper['title']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Authors:** {paper['authors_str']}")
                        st.write(f"**Published:** {paper['published']}")
                        st.write(f"**Category:** {paper['primary_category']}")
                        st.write(f"**Abstract:** {paper['abstract'][:300]}...")
                        st.write(f"[📥 PDF]({paper['pdf_url']})")
                    
                    with col2:
                        relevance_pct = paper.get('relevance', 0.5) * 100
                        color = "🟢" if relevance_pct > 70 else "🟡" if relevance_pct > 50 else "🟠"
                        st.metric("Relevance", f"{relevance_pct:.0f}%", color)
            
            st.markdown("---")
            st.success("✅ Ready! Navigate to **Summary Analysis** →")
    
    def summary_analysis_page(self):
        st.markdown('<div class="main-header">📊 Summary Analysis</div>', unsafe_allow_html=True)
        
        if not hasattr(st.session_state, 'retrieved_papers'):
            st.warning("⚠️ Retrieve papers first!")
            return
        
        st.markdown("### 🔍 Generate Comprehensive Summary")
        
        # Configuration options
        with st.expander("⚙️ Summary Configuration", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                include_executive_summary = st.checkbox("Executive Summary", value=True)
                include_methods = st.checkbox("Methodologies", value=True)
            with col2:
                include_findings = st.checkbox("Key Findings", value=True)
                include_gaps = st.checkbox("Research Gaps", value=True)
        
        if st.button("🧠 Generate Comprehensive Summary", use_container_width=True, type="primary"):
            with st.spinner("Analyzing papers with NLP..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # REAL summarization using the new method
                    status_text.text("📥 Extracting and combining paper content...")
                    progress_bar.progress(20)
                    
                    # Generate comprehensive summary using the new method
                    comprehensive_summary = self.summarization_agent.generate_comprehensive_summary(
                        st.session_state.retrieved_papers,
                        st.session_state.query_result['keywords']
                    )
                    
                    progress_bar.progress(60)
                    status_text.text("🔍 Organizing by sections and extracting insights...")
                    
                    # Format for display
                    formatted_summary = self.summarization_agent.format_summary_for_display(
                        comprehensive_summary
                    )
                    
                    st.session_state.comprehensive_summary = comprehensive_summary
                    st.session_state.formatted_summary = formatted_summary
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Complete!")
                    
                    st.success("✅ Comprehensive summary generated!")
                    
                except Exception as e:
                    st.error(f"Summarization error: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display Comprehensive Summary
        if hasattr(st.session_state, 'comprehensive_summary'):
            summary = st.session_state.comprehensive_summary
            
            st.markdown("### 📋 Comprehensive Summary of All Papers")
            
            # Metadata
            with st.expander("📊 Analysis Metadata", expanded=False):
                meta = summary["metadata"]
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Papers", meta["total_papers"])
                with col2:
                    st.metric("Full Text Papers", meta["papers_with_full_text"])
                with col3:
                    st.metric("Keywords", len(meta["keywords"]))
            
            # Executive Summary
            if include_executive_summary:
                st.markdown("### 📝 Executive Summary")
                st.markdown('<div class="summary-section">', unsafe_allow_html=True)
                st.write(summary["executive_summary"])
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Section Summaries
            st.markdown("### 🔬 Section-wise Synthesis")
            
            tabs = st.tabs(list(summary["section_summaries"].keys()))
            
            for tab, (section_name, section_content) in zip(tabs, summary["section_summaries"].items()):
                with tab:
                    st.markdown('<div class="summary-section">', unsafe_allow_html=True)
                    st.write(section_content)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Key Insights
            if include_methods or include_findings:
                st.markdown("### 💡 Key Insights")
                
                insights = summary["key_insights"]
                
                if include_methods and insights["methodological_approaches"]:
                    st.markdown("#### 🛠️ Methodological Approaches")
                    for insight in insights["methodological_approaches"][:5]:
                        st.markdown(f'<div class="insight-card">• {insight}</div>', unsafe_allow_html=True)
                
                if include_findings and insights["major_findings"]:
                    st.markdown("#### 📊 Major Findings")
                    for insight in insights["major_findings"][:5]:
                        st.markdown(f'<div class="insight-card">• {insight}</div>', unsafe_allow_html=True)
            
            # Research Gaps
            if include_gaps and summary["research_gaps"]:
                st.markdown("### 🔍 Identified Research Gaps")
                for gap in summary["research_gaps"][:5]:
                    st.markdown(f'<div class="insight-card">• {gap}</div>', unsafe_allow_html=True)
            
            # Final Synthesis
            st.markdown("### 🎯 Final Synthesis")
            st.info(summary["synthesis"])
            
            # Download formatted summary
            st.markdown("---")
            st.download_button(
                "📥 Download Full Summary",
                data=st.session_state.formatted_summary,
                file_name=f"comprehensive_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            st.markdown("---")
            st.success("✅ Ready! Navigate to **Draft Generation** →")
    
    def draft_generation_page(self):
        st.markdown('<div class="main-header">✍️ Pattern-Based Draft Generation</div>', unsafe_allow_html=True)
        
        if not hasattr(st.session_state, 'comprehensive_summary'):
            st.warning("⚠️ Generate comprehensive summary first!")
            return
        
        # Configuration
        with st.expander("⚙️ Configuration", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                temperature = st.slider("Creativity", 0.1, 1.0, 0.7)
            with col2:
                max_length = st.slider("Max Length", 300, 800, 500)
        
        st.markdown("### 🎨 Generate Draft")
        
        if st.button("✨ Generate", use_container_width=True, type="primary"):
            with st.spinner("Generating clean academic draft..."):
                progress_bar = st.progress(0)
                
                try:
                    # Use clean drafting agent
                    config = DraftingConfig(
                        temperature=temperature,
                        max_new_tokens=max_length  # Use max_new_tokens instead of max_length
                    )
                    
                    drafting_agent = get_drafting_agent(config)
                    
                    progress_bar.progress(33)
                    
                    # Generate using comprehensive summary
                    draft = drafting_agent.generate_complete_draft(
                        st.session_state.research_topic,
                        st.session_state.comprehensive_summary,
                        st.session_state.query_result['keywords']
                    )
                    
                    st.session_state.generated_draft = draft
                    st.session_state.used_fine_tuned = drafting_agent.is_fine_tuned
                    
                    progress_bar.progress(100)
                    
                    # Collect training data
                    if not st.session_state.get('data_collected'):
                        self.data_manager.add_completed_research(
                            st.session_state.research_topic,
                            st.session_state.query_result,
                            st.session_state.comprehensive_summary,
                            draft
                        )
                        st.session_state.data_collected = True
                        
                        stats = self.data_manager.get_training_statistics()
                        if stats['total_samples'] >= 3:
                            st.info("💡 You can now train a custom AI model!")
                    
                    st.success("✅ Clean draft generated!")
                    
                except Exception as e:
                    st.error(f"Generation error: {e}")
                    import traceback
                    st.code(traceback.format_exc())
        
        # Display Draft
        if hasattr(st.session_state, 'generated_draft'):
            model_type = "Fine-tuned AI" if st.session_state.get('used_fine_tuned') else "Base AI"
            st.markdown(f"### 📝 Draft <span class='model-badge'>{model_type}</span>", 
                    unsafe_allow_html=True)
            
            tab1, tab2, tab3 = st.tabs(["Abstract", "Introduction", "Related Work"])
            
            with tab1:
                st.write(st.session_state.generated_draft["abstract"])
                st.caption(f"{len(st.session_state.generated_draft['abstract'].split())} words")
            
            with tab2:
                st.write(st.session_state.generated_draft["introduction"])
                st.caption(f"{len(st.session_state.generated_draft['introduction'].split())} words")
            
            with tab3:
                st.write(st.session_state.generated_draft["related_work"])
                st.caption(f"{len(st.session_state.generated_draft['related_work'].split())} words")
            
            # Download
            st.markdown("---")
            draft_content = f"""RESEARCH PAPER DRAFT
    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    Topic: {st.session_state.research_topic}
    Model: {model_type}

    ABSTRACT
    {st.session_state.generated_draft['abstract']}

    INTRODUCTION
    {st.session_state.generated_draft['introduction']}

    RELATED WORK
    {st.session_state.generated_draft['related_work']}
    """
            
            st.download_button(
                "📥 Download Draft",
                data=draft_content,
                file_name=f"draft_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    def output_management_page(self):
        st.markdown('<div class="main-header">📁 Output Management</div>', unsafe_allow_html=True)
        
        # Stats
        stats = self.data_manager.get_training_statistics()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Research Projects", stats['total_samples'])
        with col2:
            st.metric("Total References", stats['total_references'])
        with col3:
            st.metric("Topics Covered", stats['topics_covered'])
        
        # Exports
        st.markdown("### 📤 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.get('generated_draft'):
                draft_content = f"""DRAFT\n\n{st.session_state.generated_draft['abstract']}\n\n{st.session_state.generated_draft['introduction']}\n\n{st.session_state.generated_draft['related_work']}"""
                st.download_button(
                    "📄 Draft",
                    data=draft_content,
                    file_name="draft.txt",
                    use_container_width=True
                )
            else:
                st.button("📄 Draft", disabled=True, use_container_width=True)
        
        with col2:
            if st.session_state.get('query_result'):
                query_content = json.dumps(st.session_state.query_result, indent=2)
                st.download_button(
                    "🔗 Query Data",
                    data=query_content,
                    file_name="query.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.button("🔗 Query Data", disabled=True, use_container_width=True)
        
        with col3:
            if stats['total_samples'] > 0:
                training_data = json.dumps(self.data_manager.training_data, indent=2)
                st.download_button(
                    "📚 Training Data",
                    data=training_data,
                    file_name="training.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.button("📚 Training Data", disabled=True, use_container_width=True)
        
        # Display comprehensive summary if available
        if hasattr(st.session_state, 'formatted_summary'):
            st.markdown("### 📊 Comprehensive Summary")
            with st.expander("View Summary"):
                st.text(st.session_state.formatted_summary)
                
            st.download_button(
                "📥 Download Comprehensive Summary",
                data=st.session_state.formatted_summary,
                file_name="comprehensive_summary.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    def run(self):
        # Initialize session state
        if 'research_topic' not in st.session_state:
            st.session_state.research_topic = ""
        if 'num_keywords' not in st.session_state:
            st.session_state.num_keywords = 8
        if 'num_papers' not in st.session_state:
            st.session_state.num_papers = 5
        if 'training_triggered' not in st.session_state:
            st.session_state.training_triggered = False
        if 'data_collected' not in st.session_state:
            st.session_state.data_collected = False
        
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