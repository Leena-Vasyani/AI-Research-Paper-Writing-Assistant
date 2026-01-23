# 🔎 Plagiarism Detection Agent

## Overview

Professional plagiarism detection system that analyzes generated research paper drafts for similarity against source papers. Provides detailed rewrite suggestions and paraphrasing strategies.

## ✨ Features

### Phase 1: Core Detection (✅ Complete)

- **Sentence-level similarity detection** using sentence transformers
- **Multi-level scoring system**:
  - ✅ Good: < 30% similarity
  - ⚠️ Moderate: 30-50% similarity
  - 🚨 High: > 50% similarity
- **Section-wise analysis** (Abstract, Introduction, Related Work)
- **Comprehensive plagiarism reports** with statistics

### Phase 2: Detailed Suggestions (✅ Complete)

- **Sentence highlighting** for plagiarized content
- **Alternative phrasing suggestions**
- **Paraphrasing strategies**:
  - Synonym replacement
  - Sentence restructuring
  - Concept reframing
  - Proper attribution techniques
- **Severity-based recommendations** (different strategies for high/moderate/low similarity)

### Phase 3: UI Integration (✅ Complete)

- **New navigation page**: 🔎 Plagiarism Check
- **Visual score display** with color-coded status
- **Interactive section analysis** with expandable results
- **Export functionality** for plagiarism reports
- **Detailed sentence-by-sentence breakdown**

### Phase 4: External API Support (✅ Complete)

- **Framework for external plagiarism APIs**
- **Support for free API services** (when configured):
  - Copyleaks free tier
  - PlagiarismCheck.org API
  - Custom search engines
- **Graceful fallback** to local checking
- **Rate limiting** and respectful API usage

---

## 🚀 Usage

### Basic Workflow

1. **Generate Draft**: Complete the draft generation step first
2. **Navigate**: Go to 🔎 Plagiarism Check page
3. **Run Check**: Click "🚀 Run Plagiarism Check"
4. **Review Results**: Analyze flagged sentences and suggestions
5. **Export Report**: Download detailed plagiarism report

### Understanding Results

#### Overall Score

- **Score**: Weighted average similarity across all sections
- **Status**: Overall plagiarism severity level
- **Statistics**: Total/flagged sentences and percentages

#### Section Analysis

Each section (Abstract, Introduction, Related Work) shows:

- Plagiarism score (%)
- Number of flagged sentences
- Severity status
- Detailed sentence breakdowns

#### Flagged Sentences

For each flagged sentence, you get:

- **Similarity score**: How similar to source (%)
- **Severity**: High/Moderate classification
- **Your draft**: The sentence from your draft
- **Source match**: The matching sentence from source papers
- **Suggestions**: 5-8 specific rewrite recommendations
- **Strategies**: 3-4 rewriting techniques with examples

---

## 🔧 Configuration

### Plagiarism Thresholds

Default thresholds in `plagiarism_agent.py`:

```python
self.thresholds = {
    'low': 0.30,      # < 30% = Good
    'moderate': 0.50,  # 30-50% = Moderate
    'high': 0.50       # > 50% = High plagiarism
}
```

You can adjust these in the agent initialization.

### External API Integration (Optional)

To enable external plagiarism checking:

1. **Sign up for a free API** (options):

   - [Copyleaks](https://copyleaks.com/) - Free tier available
   - [PlagiarismCheck.org](https://plagiarismcheck.org/) - API available
   - [Google Custom Search API](https://developers.google.com/custom-search) - 100 queries/day free

2. **Add your API key** in `core_agents/plagiarism_agent.py`:

   ```python
   def _check_with_plagiarism_detector_api(self, text: str) -> Optional[Dict]:
       # Add your API configuration here
       api_key = "YOUR_API_KEY_HERE"  # Replace with your key
       api_url = "https://api.your-service.com/check"
       # ... rest of implementation
   ```

3. **Enable in UI**: Check "🌐 Use External API Validation" option

---

## 📊 Example Report

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     PLAGIARISM DETECTION REPORT                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 ANALYSIS METADATA
────────────────────────────────────────────────────────────────────────────────
Research Topic: Deep Learning for Stock Market Prediction
Analysis Date: 2026-01-04 15:30:00
Source Papers: 5
Source Sentences: 234

🎯 OVERALL RESULTS
────────────────────────────────────────────────────────────────────────────────
Plagiarism Score: 38.5%
Status: MODERATE
Message: Moderate plagiarism detected. Review flagged sections.

📊 STATISTICS
────────────────────────────────────────────────────────────────────────────────
Total Sentences Analyzed: 15
Sentences Flagged: 6
Percentage Flagged: 40.0%

📑 SECTION-WISE ANALYSIS
────────────────────────────────────────────────────────────────────────────────

⚠️ ABSTRACT
────────────────────────────────────────────────────────────────────────────────
Plagiarism Score: 42.3%
Total Sentences: 5
Flagged Sentences: 2
Status: MODERATE

🚩 Flagged Sentences (2):

  [1] Similarity: 65.2% (HIGH)
  Draft: This paper explores deep learning techniques for stock prediction...
  Source: Deep learning techniques have revolutionized stock market prediction...

  📝 REWRITE SUGGESTIONS:
     🚨 HIGH SIMILARITY: Complete rewrite recommended
        → Restructure the entire sentence with new phrasing
        → Change sentence structure (active ↔ passive voice)
        → Use different synonyms for key terms

     💡 PARAPHRASING TECHNIQUES:
        1. Synonym Replacement:
           - Replace common words with academic alternatives
           - Example: 'shows' → 'demonstrates', 'uses' → 'employs'

        2. Sentence Restructuring:
           - Start with a different clause
           - Change from simple to complex sentence structure

  🔧 REWRITE STRATEGIES:
     • Synonym Substitution: Replace key words with synonyms while maintaining meaning
     • Sentence Restructuring: Change sentence order and structure (active/passive voice)
     • Concept Reframing: Express the same idea from a different perspective

📚 GENERAL REWRITING GUIDELINES
────────────────────────────────────────────────────────────────────────────────
  • Always paraphrase in your own words - don't just replace individual words
  • Add your own analysis and interpretation to differentiate from sources
  • Use proper citations when referring to specific ideas from papers
  • Combine ideas from multiple sources to create original synthesis
  • Restructure sentences completely rather than minor word changes
```

---

## 🧪 Testing

Run the standalone test:

```powershell
.\venv\Scripts\python core_agents\plagiarism_agent.py
```

This will:

- Load the plagiarism detection model
- Test with sample draft and papers
- Generate a full plagiarism report
- Show all suggestions and strategies

---

## 🎯 Best Practices

### For Students/Researchers

1. **Run early**: Check plagiarism before finalizing your draft
2. **Review all flagged sentences**: Even low-moderate matches
3. **Apply suggestions**: Use the provided rewriting strategies
4. **Cite properly**: Always attribute ideas to original sources
5. **Iterate**: Re-run check after making changes

### For Developers

1. **Model selection**: `all-MiniLM-L6-v2` for speed, `allenai/scibert_scivocab_uncased` for accuracy
2. **Batch processing**: Process sentences in batches for efficiency
3. **Caching**: Consider caching embeddings for repeated checks
4. **Rate limiting**: Be respectful when using external APIs

---

## 🔬 Technical Details

### Similarity Detection

- **Model**: Sentence-BERT (sentence-transformers)
- **Method**: Cosine similarity between sentence embeddings
- **Granularity**: Sentence-level analysis
- **Comparison**: Against all source paper sentences

### Scoring Algorithm

```
Overall Score = Σ(section_score × section_sentences) / total_sentences
Section Score = Average similarity of all sentences in section
Sentence Score = Maximum similarity to any source sentence
```

### Performance

- **Speed**: ~1-2 seconds per section (5-10 sentences)
- **Accuracy**: High for semantic similarity, lower for structural plagiarism
- **Memory**: ~500MB for model, scales with paper count

---

## 📝 Future Enhancements

Potential improvements:

- [ ] Auto-rewrite functionality (currently manual)
- [ ] Multi-language support
- [ ] Citation extraction and formatting
- [ ] Plagiarism trend tracking over time
- [ ] Integration with more external APIs
- [ ] Real-time plagiarism checking as you type
- [ ] Support for paraphrase detection
- [ ] Integration with reference managers

---

## 🐛 Troubleshooting

### Common Issues

**Issue**: "Model loading failed"

- **Solution**: Check internet connection, model downloads on first use

**Issue**: "No source content available"

- **Solution**: Ensure papers were retrieved successfully with abstracts

**Issue**: "All sentences flagged as high plagiarism"

- **Solution**: Generated draft may be too similar to sources - needs more original content

**Issue**: "External API not working"

- **Solution**: Verify API key is configured correctly, check API rate limits

### Debug Mode

Enable detailed logging by checking terminal output during plagiarism check.

---

## 📄 License & Credits

**Created**: January 4, 2026  
**Developer**: Professional AI Research Assistant  
**Models Used**:

- sentence-transformers/all-MiniLM-L6-v2
- Optional: allenai/scibert_scivocab_uncased

**Dependencies**:

- sentence-transformers >= 2.2.2
- scikit-learn >= 1.3.0
- numpy >= 1.24.0

---

## 📞 Support

For issues or questions:

1. Check this README
2. Review terminal output for detailed error messages
3. Examine flagged sentences and suggestions carefully
4. Ensure all dependencies are installed: `pip install -r requirements.txt`

---

**Remember**: Plagiarism detection is a tool to improve your writing. Always:

- ✅ Paraphrase in your own words
- ✅ Add your unique analysis and insights
- ✅ Cite sources properly
- ✅ Combine ideas from multiple sources
- ✅ Review and revise based on suggestions

Good luck with your research! 🚀
