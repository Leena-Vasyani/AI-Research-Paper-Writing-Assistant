# Citation Agent - Integration Code Reference

## Complete Integration Summary

All changes made to integrate the Citation Agent into `research_paper.py`:

---

## 1. Import Statement (Line 12)

```python
from core_agents.citation_agent import CitationAgent
```

**Location:** Top of file with other agent imports

**Purpose:** Imports the CitationAgent class for use in the application

---

## 2. Agent Initialization (Line 93)

```python
class ResearchPaperGeneratorUI:
    def __init__(self):
        # Initialize all agents
        self.query_agent = ScientificQueryAgent()
        self.retrieval_agent = PaperRetrievalAgent()
        self.summarization_agent = PaperSummarizationAgent()
        self.data_manager = TrainingDataManager()
        self.plagiarism_agent = PlagiarismDetectionAgent()
        self.citation_agent = CitationAgent()  # ← NEW LINE
        load_css()
```

**Purpose:** Creates instance of CitationAgent available to all methods

---

## 3. Navigation Menu Update (Line 111)

```python
page = st.radio(
    "Navigation",
    [
        "🏠 Dashboard", 
        "🎯 Topic Analysis", 
        "🔍 Paper Retrieval", 
        "📊 Summary Analysis", 
        "✍️ Draft Generation", 
        "🔎 Plagiarism Check", 
        "📚 Apply Citations",          # ← NEW
        "📁 Output Management"
    ],
    label_visibility="collapsed"
)
```

**Purpose:** Adds new navigation item for Apply Citations page

---

## 4. Post-Plagiarism Info (Line 845)

```python
st.markdown("---")
st.success("✅ Review flagged sections and apply suggested changes to reduce plagiarism!")

st.info("💡 **Next Step**: Navigate to **📚 Apply Citations** to automatically cite plagiarized sentences →")  # ← NEW
```

**Location:** End of `plagiarism_check_page()` method

**Purpose:** Guides user to next step after plagiarism check

---

## 5. New Page Method (Lines 847-1004)

### Method Signature:
```python
def apply_citations_page(self):
    st.markdown('<div class="main-header">📚 Apply Citations</div>', unsafe_allow_html=True)
```

### Page Components:

#### A. Validation
```python
if not hasattr(st.session_state, 'plagiarism_report'):
    st.warning("⚠️ Run plagiarism check first!")
    return

if not hasattr(st.session_state, 'generated_draft'):
    st.warning("⚠️ Generate a draft first!")
    return
```

#### B. Settings
```python
with st.expander("⚙️ Citation Settings", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        citation_style = st.selectbox(
            "Citation Style",
            ["APA", "IEEE", "MLA"],
            index=0,
            key="citation_style"
        ).lower()
    with col2:
        auto_cite_all = st.checkbox(
            "Auto-cite all flagged sentences",
            value=True,
            help="If unchecked, will only cite high-similarity content"
        )
```

#### C. Citation Application
```python
if st.button("🔗 Apply Citations", use_container_width=True, type="primary"):
    with st.spinner("🔗 Adding citations to flagged sentences..."):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("📝 Processing draft sections...")
            progress_bar.progress(20)
            
            # MAIN CALL TO CITATION AGENT
            citation_result = self.citation_agent.add_citations_to_draft(
                draft_sections=st.session_state.generated_draft,
                retrieved_papers=st.session_state.retrieved_papers,
                plagiarism_results=st.session_state.plagiarism_report,
                citation_style=citation_style
            )
            
            progress_bar.progress(70)
            status_text.text("✨ Formatting final document...")
            
            st.session_state.cited_draft = citation_result["cited_draft"]
            st.session_state.citation_data = citation_result
            
            progress_bar.progress(100)
            status_text.text("✅ Complete!")
            
            st.success("✅ Citations applied successfully!")
            
        except Exception as e:
            st.error(f"Citation error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
```

#### D. Results Display
```python
if hasattr(st.session_state, 'cited_draft'):
    citation_data = st.session_state.citation_data
    
    st.markdown("### 📝 Cited Draft")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Citations Added", citation_data["citations_added"])
    with col2:
        st.metric("Plagiarism Citations", citation_data["plagiarism_citations"])
    with col3:
        st.metric("Unique Papers", len(set(ref['paper_info']['title'] for ref in citation_data["references"])))
```

#### E. Content Display
```python
tab1, tab2, tab3, tab4 = st.tabs(["Abstract", "Introduction", "Related Work", "References"])

with tab1:
    st.write(cited_draft["abstract"])
    st.caption(f"{len(cited_draft['abstract'].split())} words")

with tab2:
    st.write(cited_draft["introduction"])
    st.caption(f"{len(cited_draft['introduction'].split())} words")

with tab3:
    st.write(cited_draft["related_work"])
    st.caption(f"{len(cited_draft['related_work'].split())} words")

with tab4:
    st.markdown(cited_draft["references"])
```

#### F. Citation Details
```python
with st.expander("View all citations", expanded=False):
    for i, ref in enumerate(citation_data["references"], 1):
        st.markdown(f"**[{i}] {ref['paper_info']['title']}**")
        st.write(f"Authors: {ref['paper_info']['authors']}")
        st.write(f"Year: {ref['paper_info']['year']}")
        st.write(f"Citation: {ref['reference']}")
        st.divider()
```

#### G. Download
```python
full_cited_content = f"""RESEARCH PAPER (WITH CITATIONS)
    Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    Topic: {st.session_state.research_topic}
    Model: {"Fine-tuned AI" if st.session_state.get('used_fine_tuned') else "Base AI"}
    Citations: {citation_data['citations_added']}

    ABSTRACT
    {cited_draft['abstract']}

    INTRODUCTION
    {cited_draft['introduction']}

    RELATED WORK
    {cited_draft['related_work']}

    REFERENCES
    {cited_draft['references']}
    """

st.download_button(
    "📥 Download Cited Draft",
    data=full_cited_content,
    file_name=f"cited_draft_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
    mime="text/plain",
    use_container_width=True
)
```

---

## 6. Navigation Routing (Lines 1110-1112)

```python
elif page == "📚 Apply Citations":
    self.apply_citations_page()
```

**Location:** Main `run()` method navigation switch

**Purpose:** Routes to the new citations page when selected

---

## 7. Export Updates (Lines 1130-1146)

### Before:
```python
col1, col2, col3 = st.columns(3)

with col1:
    if st.session_state.get('generated_draft'):
        # ... export draft
```

### After:
```python
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.session_state.get('generated_draft'):
        # ... export draft

with col4:
    if st.session_state.get('cited_draft'):
        cited_content = f"""CITED DRAFT\n\n{st.session_state.cited_draft['abstract']}\n\n{st.session_state.cited_draft['introduction']}\n\n{st.session_state.cited_draft['related_work']}\n\nREFERENCES\n{st.session_state.cited_draft['references']}"""
        st.download_button(
            "📚 Cited Draft",
            data=cited_content,
            file_name="cited_draft.txt",
            use_container_width=True
        )
    else:
        st.button("📚 Cited Draft", disabled=True, use_container_width=True)
```

**Purpose:** Allows export of both original draft and cited draft

---

## Data Flow Architecture

```
research_paper.py (Streamlit UI)
         │
         ├─→ citation_agent.add_citations_to_draft()
         │
         └─→ Inputs:
             ├─ draft_sections: Dict[str, str]
             │  └─ From: st.session_state.generated_draft
             │
             ├─ retrieved_papers: List[Dict]
             │  └─ From: st.session_state.retrieved_papers
             │
             ├─ plagiarism_results: Dict
             │  └─ From: st.session_state.plagiarism_report
             │
             └─ citation_style: str
                └─ From: user selection (apa/ieee/mla)
         
         Returns:
         {
             "cited_draft": {...},
             "citations_added": int,
             "plagiarism_citations": int,
             "references": List[Dict],
             "citation_map": Dict
         }
         
         Stored in:
         └─ st.session_state.cited_draft
         └─ st.session_state.citation_data
```

---

## Key Integration Points

### 1. **Dependency Chain**
```
topic analysis → retrieve papers → summarize → generate draft → 
plagiarism check → APPLY CITATIONS → export
```

### 2. **Session State Usage**
```python
st.session_state.generated_draft      # From draft generation
st.session_state.retrieved_papers     # From paper retrieval
st.session_state.plagiarism_report    # From plagiarism check
st.session_state.cited_draft          # OUTPUT: from citations
st.session_state.citation_data        # OUTPUT: statistics
```

### 3. **Error Handling**
```python
try:
    citation_result = self.citation_agent.add_citations_to_draft(...)
except Exception as e:
    st.error(f"Citation error: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
```

---

## Testing the Integration

### CLI Test:
```bash
streamlit run research_paper.py
```

### UI Test Flow:
1. Dashboard → Enter topic
2. Topic Analysis → Analyze
3. Paper Retrieval → Retrieve papers
4. Summary Analysis → Generate summary
5. Draft Generation → Generate draft
6. Plagiarism Check → Check plagiarism
7. **Apply Citations** → Apply citations ← NEW!
8. Output Management → Export

---

## Complete Integration Checklist

✅ Citation agent imported
✅ Citation agent initialized
✅ Navigation menu updated
✅ New apply_citations_page() method created
✅ Citation application logic implemented
✅ Results display formatted
✅ Download functionality added
✅ Session state management
✅ Error handling implemented
✅ Navigation routing added
✅ Export options updated

---

## Total Lines Changed

- **Lines Added:** ~160
- **Files Modified:** 1 (research_paper.py)
- **New Methods:** 1 (apply_citations_page)
- **New Classes:** 0 (uses existing CitationAgent)
- **Breaking Changes:** None (backward compatible)

---

## Summary

The Citation Agent has been fully integrated with:
- ✅ Complete UI/UX
- ✅ Session state management
- ✅ Error handling
- ✅ Progress tracking
- ✅ Statistics display
- ✅ Download functionality

**The system is ready for production use!** 🚀
