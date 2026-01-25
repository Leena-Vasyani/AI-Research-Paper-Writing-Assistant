# Citation Agent - Improvements for Plagiarism Handling

## Overview

The citation agent has been enhanced to **automatically cite plagiarized sentences** by connecting them to their source papers. This solves plagiarism issues while maintaining academic integrity.

---

## Key Improvements

### 1. **New Method: `add_citations_to_draft_with_plagiarism()`**

- **Priority 1**: Automatically cites flagged plagiarized sentences from the plagiarism detection report
- **Priority 2**: Adds citations to other academic claims using pattern matching
- **Tracks**: Which papers were cited for plagiarism vs. general academic support

**How it works:**

```python
result = citation_agent.add_citations_to_draft(
    draft_sections={"abstract": "...", "introduction": "..."},
    retrieved_papers=[{paper data}],
    plagiarism_results={plagiarism report},  # NEW: Plagiarism detection results
    citation_style="apa"
)
```

### 2. **Smart Wrapper Method: `add_citations_to_draft()`**

- Automatically detects if plagiarism results are provided
- Routes to plagiarism-aware citation method if available
- Falls back to basic citation method for backward compatibility
- **No code changes needed** in existing implementations!

### 3. **Better Citation Relevance Calculation**

- Improved semantic matching between sentences and papers
- Counts how many key terms appear in title/abstract
- Weights recent papers more highly
- Uses available relevance scores from retrieval agent

---

## Workflow Integration

### **Current Flow (After Plagiarism Detection):**

```
1. Generate Draft
   ↓
2. Run Plagiarism Detection
   ↓
3. Add Citations with Plagiarism Priority  ← NEW
   ↓
4. Return Cited Draft (plagiarism ~= 0%)
```

### **Citation Priority:**

1. **HIGH PRIORITY** 🔴: Plagiarized sentences → Cited from source papers
2. **MEDIUM PRIORITY** 🟡: Academic claims → Cited from relevant papers
3. **ORIGINAL** 🟢: Unique analysis → No citation needed

---

## Output Features

### Citation Report Includes:

- ✅ Number of flagged sentences cited
- ✅ Total citations added
- ✅ Unique papers cited
- ✅ Papers cited for plagiarism (highlighted)
- ✅ Proper citation formatting (APA/IEEE/MLA)

### Returned Data:

```python
{
    "cited_draft": {
        "abstract": "Text with citations...",
        "introduction": "Text with citations...",
        "related_work": "Text with citations...",
        "references": "Formatted reference list"
    },
    "citations_added": 12,
    "plagiarism_citations": 8,  # NEW: Plagiarism-specific
    "references": [list of formatted citations],
    "citation_map": {paper_id: citation_info}
}
```

---

## Expected Results

### Before (42-56% Plagiarism):

```
"This paper presents a comprehensive investigation of LLM in Healthcare..."
└─ PLAGIARISM: 79% similar to source paper
```

### After (< 10% Plagiarism):

```
"This paper presents a comprehensive investigation of LLM in Healthcare.
(Smith et al., 2021)"
└─ PROPERLY CITED: Source paper acknowledged
```

---

## Integration with Research Paper Generator

### In `research_paper.py`:

```python
# After plagiarism detection
citation_agent = CitationAgent()

# Pass plagiarism results to add citations automatically
cited_result = citation_agent.add_citations_to_draft(
    draft_sections=st.session_state.generated_draft,
    retrieved_papers=st.session_state.retrieved_papers,
    plagiarism_results=plagiarism_report,  # From plagiarism agent
    citation_style="apa"
)

# Display cited draft with reduced plagiarism
st.session_state.final_draft = cited_result["cited_draft"]
```

---

## Benefits

✅ **Eliminates Plagiarism**: Flagged content becomes properly cited  
✅ **Maintains Academic Integrity**: Uses source papers appropriately  
✅ **Smart Prioritization**: Focuses on high-plagiarism sentences first  
✅ **Flexible**: Works with any plagiarism detection format  
✅ **Backward Compatible**: Existing code still works  
✅ **Professional Output**: Proper citations in multiple formats  
✅ **Transparent**: Shows which papers were cited for plagiarism

---

## Citation Styles Supported

- **APA**: (Author, Year)
- **IEEE**: [1], [2], etc.
- **MLA**: (Author Last Page)

---

## Technical Details

### Plagiarism Detection Format Expected:

```python
{
    "section_analysis": {
        "abstract": {
            "flagged_sentences": [
                {
                    "sentence": "Original text...",
                    "source": "Source paper title",
                    "similarity": 0.79
                }
            ]
        }
    }
}
```

### Automatic Paper Matching:

- Searches for source paper title in retrieved papers
- Falls back to semantic similarity if exact match not found
- Uses highest-relevance papers for citation
- Prevents duplicate citations (same paper cited multiple times)

---

## Implementation Status

✅ Citation agent code updated  
✅ Backward compatibility maintained  
✅ Plagiarism integration ready  
✅ All citation formats implemented  
⏳ **Next**: Integrate into research_paper.py workflow
