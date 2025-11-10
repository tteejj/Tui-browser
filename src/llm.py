"""
LLM integration layer with multi-provider support
"""
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests


@dataclass
class LLMResponse:
    """Response from LLM"""
    text: str
    success: bool
    error: Optional[str] = None
    tokens_used: Optional[int] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> LLMResponse:
        """Generate response from prompt"""
        pass


class OllamaProvider(LLMProvider):
    """Local LLM via Ollama"""

    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> LLMResponse:
        """Generate response using Ollama API"""
        try:
            url = f"{self.base_url}/api/generate"

            # Build messages
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            payload = {
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            response = requests.post(url, json=payload, timeout=60)

            if response.status_code != 200:
                return LLMResponse(
                    text="",
                    success=False,
                    error=f"Ollama error: {response.status_code} {response.text}"
                )

            data = response.json()
            text = data.get('response', '')

            return LLMResponse(
                text=text,
                success=True,
                tokens_used=data.get('eval_count', 0)
            )

        except requests.exceptions.ConnectionError:
            return LLMResponse(
                text="",
                success=False,
                error="Cannot connect to Ollama. Is it running? (ollama serve)"
            )
        except Exception as e:
            return LLMResponse(
                text="",
                success=False,
                error=f"Ollama error: {str(e)}"
            )


class GoogleProvider(LLMProvider):
    """Google Gemini API"""

    def __init__(self, model: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY env variable.")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> LLMResponse:
        """Generate response using Google Gemini API"""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                self.model,
                system_instruction=system_prompt
            )

            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens
                )
            )

            return LLMResponse(
                text=response.text,
                success=True,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None
            )

        except ImportError:
            return LLMResponse(
                text="",
                success=False,
                error="google-generativeai not installed. Run: pip install google-generativeai"
            )
        except Exception as e:
            return LLMResponse(
                text="",
                success=False,
                error=f"Google API error: {str(e)}"
            )


class OpenAIProvider(LLMProvider):
    """OpenAI API (GPT models)"""

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env variable.")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> LLMResponse:
        """Generate response using OpenAI API"""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            return LLMResponse(
                text=response.choices[0].message.content,
                success=True,
                tokens_used=response.usage.total_tokens
            )

        except ImportError:
            return LLMResponse(
                text="",
                success=False,
                error="openai not installed. Run: pip install openai"
            )
        except Exception as e:
            return LLMResponse(
                text="",
                success=False,
                error=f"OpenAI API error: {str(e)}"
            )


class AnthropicProvider(LLMProvider):
    """Anthropic Claude API"""

    def __init__(self, model: str = "claude-3-haiku-20240307", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY env variable.")

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000) -> LLMResponse:
        """Generate response using Anthropic API"""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.api_key)

            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)

            return LLMResponse(
                text=response.content[0].text,
                success=True,
                tokens_used=response.usage.input_tokens + response.usage.output_tokens
            )

        except ImportError:
            return LLMResponse(
                text="",
                success=False,
                error="anthropic not installed. Run: pip install anthropic"
            )
        except Exception as e:
            return LLMResponse(
                text="",
                success=False,
                error=f"Anthropic API error: {str(e)}"
            )


class LLMManager:
    """
    Manages LLM providers with fallback support
    """

    def __init__(self, primary_provider: LLMProvider,
                 fallback_provider: Optional[LLMProvider] = None):
        self.primary = primary_provider
        self.fallback = fallback_provider

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 2000,
                 use_fallback: bool = True) -> LLMResponse:
        """
        Generate response with fallback support

        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            use_fallback: Whether to use fallback on primary failure

        Returns:
            LLMResponse
        """
        # Try primary
        response = self.primary.generate(prompt, system_prompt, temperature, max_tokens)

        if response.success:
            return response

        # Try fallback if enabled and available
        if use_fallback and self.fallback:
            print(f"⚠ Primary LLM failed ({response.error}), trying fallback...")
            response = self.fallback.generate(prompt, system_prompt, temperature, max_tokens)

        return response

    def generate_json(self, prompt: str, system_prompt: Optional[str] = None,
                      temperature: float = 0.3, max_tokens: int = 2000,
                      use_fallback: bool = True) -> Dict[str, Any]:
        """
        Generate JSON response

        Automatically adds instruction to return valid JSON
        """
        json_instruction = "\n\nReturn ONLY valid JSON. No markdown, no explanation."
        full_prompt = prompt + json_instruction

        response = self.generate(full_prompt, system_prompt, temperature, max_tokens, use_fallback)

        if not response.success:
            return {"error": response.error}

        # Try to parse JSON
        text = response.text.strip()

        # Remove markdown code blocks if present
        if text.startswith('```'):
            lines = text.split('\n')
            text = '\n'.join(lines[1:-1]) if len(lines) > 2 else text
            text = text.replace('```json', '').replace('```', '').strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Return error but include raw text for debugging
            return {
                "error": f"Invalid JSON: {str(e)}",
                "raw_text": text
            }


def create_llm_manager(config: Dict[str, Any]) -> LLMManager:
    """
    Factory function to create LLM manager from config

    Config format:
    {
        "provider": "ollama" | "google" | "openai" | "anthropic",
        "model": "model-name",
        "api_key": "key" (optional, uses env var if not provided),
        "fallback_provider": "provider-name" (optional),
        "fallback_model": "model-name" (optional)
    }
    """

    # Create primary provider
    provider_name = config.get('provider', 'ollama').lower()
    model = config.get('model')
    api_key = config.get('api_key')

    providers = {
        'ollama': lambda: OllamaProvider(model or "llama3.2:3b"),
        'google': lambda: GoogleProvider(model or "gemini-1.5-flash", api_key),
        'openai': lambda: OpenAIProvider(model or "gpt-4o-mini", api_key),
        'anthropic': lambda: AnthropicProvider(model or "claude-3-haiku-20240307", api_key)
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}")

    primary = providers[provider_name]()

    # Create fallback provider if specified
    fallback = None
    fallback_provider_name = config.get('fallback_provider')
    if fallback_provider_name:
        fallback_model = config.get('fallback_model')
        fallback_api_key = config.get('fallback_api_key')

        if fallback_provider_name in providers:
            try:
                if fallback_provider_name == 'ollama':
                    fallback = OllamaProvider(fallback_model or "llama3.2:3b")
                elif fallback_provider_name == 'google':
                    fallback = GoogleProvider(fallback_model or "gemini-1.5-flash", fallback_api_key)
                elif fallback_provider_name == 'openai':
                    fallback = OpenAIProvider(fallback_model or "gpt-4o-mini", fallback_api_key)
                elif fallback_provider_name == 'anthropic':
                    fallback = AnthropicProvider(fallback_model or "claude-3-haiku-20240307", fallback_api_key)
            except Exception as e:
                print(f"⚠ Warning: Could not create fallback provider: {e}")

    return LLMManager(primary, fallback)


if __name__ == "__main__":
    # Test LLM providers
    print("Testing LLM providers...\n")

    # Test Ollama (local)
    print("=== Testing Ollama ===")
    try:
        ollama = OllamaProvider(model="llama3.2:3b")
        response = ollama.generate("Say 'Hello from Ollama' and nothing else.")
        print(f"Success: {response.success}")
        print(f"Response: {response.text}")
        print(f"Tokens: {response.tokens_used}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== Testing LLM Manager with JSON ===")
    config = {
        "provider": "ollama",
        "model": "llama3.2:3b"
    }
    manager = create_llm_manager(config)

    prompt = """
    Return a JSON object with these fields:
    - status: "ok"
    - message: "Test successful"
    - number: 42
    """

    result = manager.generate_json(prompt)
    print(f"Result: {json.dumps(result, indent=2)}")
