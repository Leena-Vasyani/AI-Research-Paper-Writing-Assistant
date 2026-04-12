import os
from typing import Dict, Any, Optional
try:
    from google import genai
except ImportError:
    genai = None
try:
    from groq import Groq
except ImportError:
    Groq = None
try:
    from core_agents.llm_provider import chat_completion as _llm_chat
except Exception:
    _llm_chat = None  # type: ignore[assignment]

class DiagramAgent:
    """
    Generates Mermaid.js diagram code from text descriptions.
    Supports flowcharts, sequence diagrams, gantt charts, entity relationship diagrams, etc.
    """
    
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        
        if self.gemini_api_key and genai is not None:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                self.gemini_model_name = "gemini-2.5-flash"
            except Exception as e:
                print(f"⚠️ Gemini init failed: {e}")
                self.gemini_client = None
                self.gemini_model_name = None
        else:
            self.gemini_client = None
            self.gemini_model_name = None
            if not self.gemini_api_key:
                print("⚠️ GEMINI_API_KEY not found. Diagram generation might fail if Groq is also unavailable.")

    def _generate_with_gemini(self, prompt: str) -> Optional[str]:
        if not self.gemini_client or not self.gemini_model_name:
            return None
        try:
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=prompt,
                config={
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "max_output_tokens": 2048,
                }
            )
            if response and response.text:
                # Extract code block if present
                text = response.text.strip()
                if "```mermaid" in text:
                    text = text.split("```mermaid")[1].split("```")[0].strip()
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0].strip()
                return text
            return None
        except Exception as e:
            print(f"⚠️ Gemini Error in DiagramAgent: {e}")
            return None

    def _generate_with_groq(self, prompt: str) -> Optional[str]:
        if not self.groq_api_key or Groq is None:
            return None
        try:
            client = Groq(api_key=self.groq_api_key)
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                top_p=0.9,
                max_tokens=2048,
            )
            text = response.choices[0].message.content.strip()
            if "```mermaid" in text:
                text = text.split("```mermaid")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return text
        except Exception as e:
            print(f"⚠️ Groq Error in DiagramAgent: {e}")
            return None

    def _generate_with_ollama(self, prompt: str) -> Optional[str]:
        if _llm_chat is None:
            return None
        try:
            text = _llm_chat(prompt, max_tokens=2048, temperature=0.2, top_p=0.9)
            if not text:
                return None
            if "```mermaid" in text:
                text = text.split("```mermaid")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return text
        except Exception as e:
            print(f"⚠️ Ollama Error in DiagramAgent: {e}")
            return None

    def generate_diagram(self, description: str, diagram_type: str = "auto") -> Dict[str, Any]:
        """
        Generate Mermaid code from text description.
        
        Args:
            description: Text description of the diagram
            diagram_type: Optional hint for diagram type (flowchart, sequence, er, etc.)
        
        Returns:
            Dictionary with mermaid_code and metadata
        """
        prompt = f"""
        You are an expert system architect and diagram designer. 
        Convert the following text description into a valid Mermaid.js diagram code.
        
        Instruction:
        - Use the best suited diagram type (flowchart, sequence, class, state, entityRelationship, gantt, pie, flowchart TD, etc.)
        - Diagram Type Hint: {diagram_type}
        - Only output the Mermaid code block.
        - Do not include any explanations or conversational text.
        - Ensure syntax is correct and follows Mermaid.js standards.
        - If the description implies hierarchy, use top-down or left-to-right flowcharts.
        
        Text Description:
        {description}
        
        Mermaid Code:
        """
        
        # Try Ollama first, then Gemini, then Groq
        mermaid_code = self._generate_with_ollama(prompt)
        provider = "ollama"

        if not mermaid_code:
            mermaid_code = self._generate_with_gemini(prompt)
            provider = "gemini"

        if not mermaid_code:
            mermaid_code = self._generate_with_groq(prompt)
            provider = "groq"
            
        if not mermaid_code:
            return {
                "success": False,
                "error": "Failed to generate diagram code from both providers.",
                "mermaid_code": ""
            }
            
        return {
            "success": True,
            "mermaid_code": mermaid_code,
            "provider": provider,
            "diagram_type": diagram_type
        }

if __name__ == "__main__":
    # Test
    agent = DiagramAgent()
    res = agent.generate_diagram("A simple login process where user enters credentials, system validates, and either redirects to home or shows error.")
    print(res["mermaid_code"])
