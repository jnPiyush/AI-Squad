"""
AI Provider Abstraction

Handles AI generation with fallback chain:
1. GitHub Copilot SDK (Primary)
2. OpenAI API (Fallback)
3. Azure OpenAI (Fallback)
4. Template-based (Last Resort)
"""
import os
import logging
import asyncio
import shutil
import subprocess
import threading
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AIProviderType(Enum):
    """Types of AI providers"""
    COPILOT = "copilot"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    TEMPLATE = "template"


@dataclass
class AIResponse:
    """Response from AI provider"""
    content: str
    provider: AIProviderType
    model: str
    usage: Optional[Dict[str, int]] = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @property
    @abstractmethod
    def provider_type(self) -> AIProviderType:
        """Get provider type"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass
    
    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        """Generate content using this provider"""
        pass


class CopilotProvider(AIProvider):
    """GitHub Copilot SDK provider (Primary)"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self._sdk = None
        self._initialized = False
        self._model_cache: Optional[str] = None
        
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.COPILOT
    
    def is_available(self) -> bool:
        if self._initialized:
            return self._sdk is not None
        
        self._initialized = True
        
        if not self._is_copilot_cli_available():
            logger.debug("Copilot CLI not available or not authenticated")
            return False
        
        try:
            from copilot import CopilotClient
            # CopilotClient uses CLI auth; no token parameter is required.
            self._sdk = CopilotClient()
            logger.info("Copilot SDK initialized successfully")
            return True
        except ImportError:
            logger.debug("Copilot SDK not installed")
            return False
        except Exception as e:
            logger.warning(f"Copilot SDK initialization failed: {e}")
            return False
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        if not self.is_available():
            return None
        
        try:
            return self._run_async(
                self._generate_async(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
        except Exception as e:
            logger.warning(f"Copilot generation failed: {e}")
            return None

    def _is_copilot_cli_available(self) -> bool:
        copilot_path = shutil.which("copilot")
        if not copilot_path:
            return False

        try:
            version = self._run_copilot_cli(copilot_path, ["--version"])
            if version.returncode != 0:
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

        return self._is_copilot_cli_authenticated(copilot_path)

    @staticmethod
    def _is_copilot_cli_authenticated(copilot_path: str) -> bool:
        try:
            auth = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return auth.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    @staticmethod
    def _run_copilot_cli(copilot_path: str, args: List[str]) -> subprocess.CompletedProcess:
        if copilot_path.lower().endswith(".ps1"):
            return subprocess.run(
                ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", copilot_path, *args],
                capture_output=True,
                text=True,
                timeout=10
            )

        return subprocess.run(
            [copilot_path, *args],
            capture_output=True,
            text=True,
            timeout=10
        )

    def _select_model(self, requested_model: Optional[str]) -> str:
        if requested_model:
            return requested_model

        if self._model_cache:
            return self._model_cache

        try:
            if hasattr(self._sdk, "models"):
                models = self._sdk.models.list()
                items = None
                if isinstance(models, dict):
                    items = models.get("data")
                elif hasattr(models, "data"):
                    items = models.data
                elif isinstance(models, list):
                    items = models

                if items:
                    for item in items:
                        if isinstance(item, dict):
                            model_id = item.get("id") or item.get("name")
                        else:
                            model_id = getattr(item, "id", None) or getattr(item, "name", None)
                        if model_id:
                            self._model_cache = model_id
                            return model_id
        except Exception as e:
            logger.debug(f"Copilot model discovery failed: {e}")

        self._model_cache = os.getenv("COPILOT_MODEL", "gpt-4.1")
        return self._model_cache

    def _run_async(self, coroutine):
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result: Dict[str, Any] = {"value": None, "error": None}

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result["value"] = loop.run_until_complete(coroutine)
            except Exception as e:
                result["error"] = e
            finally:
                loop.close()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        if result["error"]:
            raise result["error"]
        return result["value"]

    async def _generate_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> Optional[AIResponse]:
        from copilot import CopilotClient

        client = CopilotClient()
        await client.start()

        model_name = self._select_model(model)
        session_options: Dict[str, Any] = {"model": model_name}
        if system_prompt:
            session_options["systemMessage"] = {"content": system_prompt}

        session = await client.create_session(session_options)

        done = asyncio.Event()
        last_message: Dict[str, Optional[str]] = {"content": None}

        def on_event(event):
            event_type = getattr(event.type, "value", event.type)
            if event_type == "assistant.message":
                content = getattr(event.data, "content", None)
                if content is None and isinstance(event.data, dict):
                    content = event.data.get("content")
                if content:
                    last_message["content"] = content
            elif event_type == "session.idle":
                done.set()

        session.on(on_event)
        await session.send({"prompt": user_prompt})

        await asyncio.wait_for(done.wait(), timeout=120)

        await session.destroy()
        await client.stop()

        if last_message["content"]:
            return AIResponse(
                content=last_message["content"],
                provider=AIProviderType.COPILOT,
                model=model_name,
                usage=None
            )

        return None


class OpenAIProvider(AIProvider):
    """OpenAI API provider (Fallback)"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
        self._initialized = False
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.OPENAI
    
    def is_available(self) -> bool:
        if self._initialized:
            return self._client is not None
        
        self._initialized = True
        
        if not self.api_key:
            logger.debug("OpenAI: No OPENAI_API_KEY set")
            return False
        
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
            return True
        except ImportError:
            logger.debug("OpenAI SDK not installed (pip install openai)")
            return False
        except Exception as e:
            logger.warning(f"OpenAI initialization failed: {e}")
            return False
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        if not self.is_available():
            return None
        
        try:
            response = self._client.chat.completions.create(
                model=model or "gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response and response.choices:
                return AIResponse(
                    content=response.choices[0].message.content,
                    provider=AIProviderType.OPENAI,
                    model=model or "gpt-4",
                    usage=response.usage.model_dump() if response.usage else None
                )
        except Exception as e:
            logger.warning(f"OpenAI generation failed: {e}")
        
        return None


class AzureOpenAIProvider(AIProvider):
    """Azure OpenAI provider (Fallback)"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        deployment: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        self._client = None
        self._initialized = False
    
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.AZURE_OPENAI
    
    def is_available(self) -> bool:
        if self._initialized:
            return self._client is not None
        
        self._initialized = True
        
        if not self.api_key or not self.endpoint:
            logger.debug("Azure OpenAI: Missing AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT")
            return False
        
        try:
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=self.api_key,
                api_version="2024-02-15-preview",
                azure_endpoint=self.endpoint
            )
            logger.info("Azure OpenAI client initialized successfully")
            return True
        except ImportError:
            logger.debug("OpenAI SDK not installed (pip install openai)")
            return False
        except Exception as e:
            logger.warning(f"Azure OpenAI initialization failed: {e}")
            return False
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        if not self.is_available():
            return None
        
        try:
            response = self._client.chat.completions.create(
                model=model or self.deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response and response.choices:
                return AIResponse(
                    content=response.choices[0].message.content,
                    provider=AIProviderType.AZURE_OPENAI,
                    model=model or self.deployment,
                    usage=response.usage.model_dump() if response.usage else None
                )
        except Exception as e:
            logger.warning(f"Azure OpenAI generation failed: {e}")
        
        return None


class AIProviderChain:
    """
    Chain of AI providers with automatic fallback.
    
    Priority order:
    1. GitHub Copilot SDK (requires Copilot CLI installed and authenticated)
    2. OpenAI API (requires OPENAI_API_KEY)
    3. Azure OpenAI (requires AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT)
    4. Template-based fallback (always available)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._providers: List[AIProvider] = []
        self._active_provider: Optional[AIProvider] = None
        self._initialized = False
    
    def _initialize_providers(self):
        """Initialize provider chain in priority order"""
        if self._initialized:
            return
        
        self._initialized = True
        
        # Priority order: Copilot -> OpenAI -> Azure OpenAI
        providers_config = [
            ("copilot", CopilotProvider),
            ("openai", OpenAIProvider),
            ("azure_openai", AzureOpenAIProvider),
        ]
        
        for name, provider_class in providers_config:
            try:
                provider = provider_class()
                if provider.is_available():
                    self._providers.append(provider)
                    logger.info(f"AI Provider available: {name}")
            except Exception as e:
                logger.debug(f"AI Provider {name} initialization error: {e}")
        
        if self._providers:
            self._active_provider = self._providers[0]
            logger.info(f"Primary AI Provider: {self._active_provider.provider_type.value}")
        else:
            logger.warning("No AI providers available. Using template fallback.")
    
    @property
    def active_provider(self) -> Optional[AIProvider]:
        """Get the currently active provider"""
        self._initialize_providers()
        return self._active_provider
    
    @property
    def provider_type(self) -> AIProviderType:
        """Get the type of the active provider"""
        self._initialize_providers()
        if self._active_provider:
            return self._active_provider.provider_type
        return AIProviderType.TEMPLATE
    
    def is_ai_available(self) -> bool:
        """Check if any AI provider is available"""
        self._initialize_providers()
        return len(self._providers) > 0
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        self._initialize_providers()
        return [p.provider_type.value for p in self._providers]
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        """
        Generate content using the provider chain.
        
        Tries each provider in order until one succeeds.
        """
        self._initialize_providers()
        
        for provider in self._providers:
            try:
                response = provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if response:
                    logger.info(f"Generated using {provider.provider_type.value}")
                    return response
            except Exception as e:
                logger.warning(f"Provider {provider.provider_type.value} failed: {e}")
                continue
        
        logger.warning("All AI providers failed. Falling back to templates.")
        return None


# Global singleton for easy access
_provider_chain: Optional[AIProviderChain] = None


def get_ai_provider() -> AIProviderChain:
    """Get the global AI provider chain"""
    global _provider_chain
    if _provider_chain is None:
        _provider_chain = AIProviderChain()
    return _provider_chain


def generate_content(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.5,
    max_tokens: int = 4096
) -> Optional[AIResponse]:
    """
    Convenience function to generate content using the provider chain.
    
    Returns:
        AIResponse if successful, None if all providers failed (use template fallback)
    """
    return get_ai_provider().generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens
    )
