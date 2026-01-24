import os
from core_agents.summarization_agent import PaperSummarizationAgent

SAMPLE_TEXT = """
Deep learning has become a dominant approach for stock market prediction due to its ability to learn non-linear patterns in noisy financial time series. Recent studies compare LSTM, CNN, and hybrid architectures, showing improved accuracy over traditional statistical baselines. However, challenges such as market volatility, data sparsity, and model interpretability remain significant barriers to deployment. Several papers emphasize the importance of feature engineering, incorporating technical indicators and macroeconomic signals. Future research should focus on robust evaluation protocols and the integration of alternative data sources such as news and social media.
""".strip()


def main() -> None:
    agent = PaperSummarizationAgent(use_api=True)
    keywords = ["deep learning", "stock market", "prediction", "LSTM", "CNN"]

    providers = ["groq", "gemini", "local"]
    for provider in providers:
        if provider == "groq" and not agent.groq_client:
            print("[groq] Skipped: GROQ_API_KEY not set or Groq client unavailable.")
            continue
        if provider == "gemini" and not agent.gemini_model:
            print("[gemini] Skipped: GEMINI_API_KEY not set or Gemini client unavailable.")
            continue

        print("\n" + "=" * 80)
        print(f"Provider: {provider}")
        print("=" * 80)
        summary = agent.summarize_text_with_provider(
            provider=provider,
            text=SAMPLE_TEXT,
            keywords=keywords,
            section_name="Summary Quality Check",
            target_words=280
        )
        print(summary if summary else "No summary generated.")


if __name__ == "__main__":
    main()
