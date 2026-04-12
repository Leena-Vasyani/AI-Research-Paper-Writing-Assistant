import os
from typing import Any, Dict, Optional

import google.generativeai as genai

try:
    from groq import Groq
except ImportError:  # pragma: no cover - optional dependency
    Groq = None


class PseudocodeAgent:
    """
    Converts implementation code into professional LaTeX pseudocode for academic papers.
    Uses algorithm2e package formatting standards.
    """

    def __init__(self) -> None:
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()

        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        else:
            self.gemini_model = None
            print(
                "⚠️ GEMINI_API_KEY not found. Pseudocode generation might fail if Groq is also unavailable."
            )

    def _get_system_prompt(self) -> str:
        return (
            "You are an expert Academic Editor for Computer Science research papers (IEEE/ACM standard).\n"
            "Your goal is to convert raw implementation code (Python, C++, Java, etc.) into professional, "
            "mathematical pseudocode formatted for LaTeX using the 'algorithm2e' package.\n\n"
            "### INSTRUCTIONS:\n"
            "1.  **Analyze the Logic:** Identify specific loop structures, conditionals, and core logic. "
            "Ignore boilerplate (imports, print statements, logging, error handling).\n"
            "2.  **Mathematical Notation:**\n"
            "    - Replace assignment `=` with $\\leftarrow$.\n"
            "    - Replace logic `==` with $=$, `!=` with $\\neq$.\n"
            "    - Use mathematical symbols for variables where standard (e.g., use $n$ instead of `len(arr)`, "
            "use $\\sum$ instead of `total_sum`, use $\\eta$ for learning rate).\n"
            "3.  **Formatting Rules:**\n"
            "    - Use the `algorithm2e` package syntax: `\\For`, `\\If`, `\\While`, `\\KwData`, `\\KwResult`.\n"
            "    - Ensure all math variables are enclosed in `$` signs.\n"
            "    - Add meaningful comments using `\\tcc{comment}` if the logic is complex.\n"
            "4.  **Output Constraint:**\n"
            "    - Return ONLY the raw LaTeX code block.\n"
            "    - Do NOT wrap the output in markdown code blocks (like ```latex ... ```).\n"
            "    - Do NOT write introductions (\"Here is your code...\") or conclusions.\n\n"
            "### EXAMPLE INPUT:\n"
            "def find_max(arr):\n"
            "    max_val = arr[0]\n"
            "    for i in range(1, len(arr)):\n"
            "        if arr[i] > max_val:\n"
            "            max_val = arr[i]\n"
            "    return max_val\n\n"
            "### EXAMPLE OUTPUT:\n"
            "\\begin{algorithm}\n"
            "\\caption{Find Maximum Value}\n"
            "\\KwData{Array $A$ of size $n$}\n"
            "\\KwResult{Maximum value $m$}\n"
            "$m \\leftarrow A[0]$\\;\n"
            "\\For{$i \\leftarrow 1$ \\KwTo $n-1$}{\n"
            "    \\If{$A[i] > m$}{\n"
            "        $m \\leftarrow A[i]$\\;\n"
            "    }\n"
            "}\n"
            "\\Return{$m$}\\;\n"
            "\\end{algorithm}"
        )

    def _generate_with_gemini(self, code: str) -> Optional[str]:
        if not self.gemini_model:
            return None
        try:
            prompt = f"{self._get_system_prompt()}\n\n### INPUT CODE:\n{code}\n\n### OUTPUT:"
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.95,
                    "max_output_tokens": 2048,
                },
            )
            if response and response.text:
                text = response.text.strip()
                if "```latex" in text:
                    text = text.split("```latex")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                return text
            return None
        except Exception as exc:  # pragma: no cover - external provider
            print(f"⚠️ Gemini Error in PseudocodeAgent: {exc}")
            return None

    def _generate_with_groq(self, code: str) -> Optional[str]:
        if not self.groq_api_key or Groq is None:
            return None
        try:
            client = Groq(api_key=self.groq_api_key)
            prompt = f"{self._get_system_prompt()}\n\n### INPUT CODE:\n{code}\n\n### OUTPUT:"
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                top_p=0.95,
                max_tokens=2048,
            )
            text = response.choices[0].message.content.strip()
            if "```latex" in text:
                text = text.split("```latex")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return text
        except Exception as exc:  # pragma: no cover - external provider
            print(f"⚠️ Groq Error in PseudocodeAgent: {exc}")
            return None

    def convert_to_pseudocode(self, code: str, algorithm_name: str = "") -> Dict[str, Any]:
        """
        Convert implementation code to LaTeX pseudocode.

        Args:
            code: Source code to convert
            algorithm_name: Optional name for the algorithm (used in caption)

        Returns:
            Dictionary with latex_code and metadata
        """
        if not code.strip():
            return {"success": False, "error": "Code input is empty.", "latex_code": ""}

        latex_code = self._generate_with_gemini(code)
        provider = "gemini"

        if not latex_code:
            latex_code = self._generate_with_groq(code)
            provider = "groq"

        if not latex_code:
            return {
                "success": False,
                "error": "Failed to generate pseudocode from both providers.",
                "latex_code": "",
            }

        return {
            "success": True,
            "latex_code": latex_code,
            "provider": provider,
            "algorithm_name": algorithm_name,
        }


if __name__ == "__main__":
    agent = PseudocodeAgent()
    test_code = """
    def binary_search(arr, target):
        left = 0
        right = len(arr) - 1
        while left <= right:
            mid = (left + right) // 2
            if arr[mid] == target:
                return mid
            elif arr[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return -1
    """
    result = agent.convert_to_pseudocode(test_code, "Binary Search")
    print(result["latex_code"])
