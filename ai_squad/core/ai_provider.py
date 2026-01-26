"""
AI Provider Abstraction

Handles AI generation with fallback chain:
1. GitHub Copilot SDK (Primary)
2. GitHub Models API (Fallback)
3. OpenAI API (Fallback)
4. Azure OpenAI (Fallback)
5. Template-based (Last Resort)
"""
import os
import logging
import asyncio
import shutil
import subprocess
import threading
import json
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AIProviderType(Enum):
    """Types of AI providers"""
    COPILOT = "copilot"
    GITHUB_MODELS = "github_models"
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
        raise NotImplementedError
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        raise NotImplementedError
    
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
        raise NotImplementedError


class CopilotProvider(AIProvider):
    """GitHub Copilot SDK provider (Primary)"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self._sdk = None
        self._initialized = False
        self._model_cache: Optional[str] = None
        self._cli_path: Optional[str] = None  # Store CLI path for reuse
        
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.COPILOT
    
    def is_available(self) -> bool:
        """Check if Copilot provider is available (non-blocking)"""
        if self._initialized:
            return self._sdk is not None
        
        self._initialized = True
        
        # The Copilot SDK only needs GitHub authentication, not the copilot CLI
        # Check if we have GitHub authentication
        if not self._is_gh_authenticated():
            logger.debug("GitHub not authenticated (required for Copilot SDK)")
            return False
        
        try:
            from copilot import CopilotClient
            # Find copilot CLI executable
            cli_path = self._find_copilot_cli()
            if not cli_path:
                logger.debug("Copilot CLI not found")
                return False
            
            # Store CLI path for use in generation
            self._cli_path = cli_path
            
            # Initialize with explicit path
            self._sdk = CopilotClient({"cli_path": cli_path})
            logger.info("Copilot SDK initialized successfully with CLI at: %s", cli_path)
            return True
        except ImportError:
            logger.debug("Copilot SDK not installed")
            return False
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Copilot SDK initialization failed: %s", e)
            return False
    
    @staticmethod
    def _find_copilot_cli() -> Optional[str]:
        """Find copilot CLI executable"""
        # Check environment variable first
        cli_path = os.getenv("COPILOT_CLI_PATH")
        if cli_path and os.path.exists(cli_path):
            return cli_path
        
        # Try common locations
        common_paths = [
            # VS Code global storage
            os.path.expanduser(r"~\AppData\Roaming\Code\User\globalStorage\github.copilot-chat\copilotCli\copilot.bat"),
            os.path.expanduser(r"~/AppData/Roaming/Code/User/globalStorage/github.copilot-chat/copilotCli/copilot.bat"),
            # npm global
            os.path.expanduser(r"~\AppData\Roaming\npm\copilot.cmd"),
            os.path.expanduser(r"~\AppData\Roaming\npm\copilot"),
            # PATH
            shutil.which("copilot"),
        ]
        
        for path in common_paths:
            if path and os.path.exists(path):
                return path
        
        return None
    
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
                    system_prompt,
                    user_prompt,
                    model,
                    temperature,
                    max_tokens,
                )
            )
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("Copilot generation failed: %s", e, exc_info=True)
            return None
        except Exception as e:
            logger.error("Unexpected Copilot generation error: %s", e, exc_info=True)
            return None

    @staticmethod
    def _is_gh_authenticated() -> bool:
        """Check if gh CLI is authenticated (required for SDK)"""
        try:
            auth = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            return auth.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def _is_copilot_cli_available(self) -> bool:
        """Check if Copilot CLI is available (fast, non-blocking check)"""
        # First, check if copilot command exists (fast check)
        copilot_path = shutil.which("copilot")
        if not copilot_path:
            logger.debug("Copilot CLI not found in PATH")
            return False

        # Only check authentication, skip version check to avoid hangs
        # If gh is authenticated, assume copilot can use it
        return self._is_gh_authenticated()

    @staticmethod
    def _is_copilot_cli_authenticated() -> bool:
        """Deprecated: use _is_gh_authenticated instead"""
        return CopilotProvider._is_gh_authenticated()

    @staticmethod
    def _run_copilot_cli(copilot_path: str, args: List[str]) -> subprocess.CompletedProcess:
        """Run Copilot CLI command with timeout protection"""
        if copilot_path.lower().endswith(".ps1"):
            return subprocess.run(
                ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", copilot_path, *args],
                capture_output=True,
                text=True,
                timeout=5,  # Reduced from 10 to fail fast
                check=False,
            )

        return subprocess.run(
            [copilot_path, *args],
            capture_output=True,
            text=True,
            timeout=5,  # Reduced from 10 to fail fast
            check=False,
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
        except (AttributeError, ValueError, OSError) as e:
            logger.debug("Copilot model discovery failed: %s", e)

        self._model_cache = os.getenv("COPILOT_MODEL", "gpt-5.2-codex")
        return self._model_cache

    def _run_async(self, coroutine):
        try:
            _ = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)

        result: Dict[str, Any] = {"value": None, "error": None}

        def _runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result["value"] = loop.run_until_complete(coroutine)
            except (RuntimeError, ValueError, OSError) as e:
                result["error"] = e
            finally:
                loop.close()

        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join()

        error = result["error"]
        if error is not None:
            raise error
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

        _ = (temperature, max_tokens)

        # Use stored CLI path from initialization
        client_options = {}
        if self._cli_path:
            client_options["cli_path"] = self._cli_path
            
        client = CopilotClient(client_options)
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
            logger.debug("Copilot event: %s", event_type)
            if event_type == "assistant.message":
                content = getattr(event.data, "content", None)
                if content is None and isinstance(event.data, dict):
                    content = event.data.get("content")
                if content:
                    last_message["content"] = content
                    logger.debug("Got message content: %d chars", len(content))
            elif event_type == "session.idle":
                logger.debug("Session idle - completing")
                done.set()
            elif event_type in ("error", "session.error"):
                logger.error("Copilot session error: %s", event.data)
                done.set()

        session.on(on_event)
        await session.send({"prompt": user_prompt})

        # Wait for response with generous timeout for complex prompts
        await asyncio.wait_for(done.wait(), timeout=300)

        await session.destroy()
        await client.stop()

        if last_message["content"]:
            logger.debug("Copilot response received: %d chars", len(last_message["content"]))
            return AIResponse(
                content=last_message["content"],
                provider=AIProviderType.COPILOT,
                model=model_name,
                usage=None
            )

        logger.warning("Copilot returned no content")
        return None


class GitHubModelsProvider(AIProvider):
    """GitHub Models API provider (Fallback #1) with Enterprise support"""
    
    def __init__(self, token: Optional[str] = None, endpoint: Optional[str] = None, org: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN") or self._get_gh_token()
        self.endpoint = endpoint or os.getenv("GITHUB_MODELS_ENDPOINT", "https://models.inference.ai.azure.com")
        self.org = org or os.getenv("GITHUB_MODELS_ORG")  # Enterprise organization
        self._initialized = False
        self._is_enterprise = False
    
    @staticmethod
    def _get_gh_token() -> Optional[str]:
        """Try to get GitHub token from gh CLI"""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return None
        
    @property
    def provider_type(self) -> AIProviderType:
        return AIProviderType.GITHUB_MODELS
    
    def is_available(self) -> bool:
        """Check if GitHub Models API is available"""
        if self._initialized:
            return self.token is not None
            
        self._initialized = True
        
        if not self.token:
            logger.debug("GitHub Models: No GITHUB_TOKEN set")
            return False
            
        # Verify token has access and check for enterprise/premium
        try:
            import requests
            response = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                timeout=5
            )
            if response.status_code == 200:
                user_data = response.json()
                
                # Check for enterprise/premium features
                if self.org:
                    # Verify org membership for enterprise access
                    org_response = requests.get(
                        f"https://api.github.com/orgs/{self.org}/members/{user_data.get('login')}",
                        headers={
                            "Authorization": f"Bearer {self.token}",
                            "Accept": "application/vnd.github.v3+json"
                        },
                        timeout=5
                    )
                    self._is_enterprise = org_response.status_code == 204
                    if self._is_enterprise:
                        logger.info(f"GitHub Models API available (Enterprise: {self.org})")
                    else:
                        logger.info("GitHub Models API available (Personal)")
                else:
                    logger.info("GitHub Models API available")
                return True
            else:
                logger.debug(f"GitHub Models: Token validation failed ({response.status_code})")
                return False
        except Exception as e:
            logger.debug(f"GitHub Models: Token validation error: {e}")
            return False
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096
    ) -> Optional[AIResponse]:
        """Generate using GitHub Models API"""
        if not self.is_available():
            return None
        
        # Map common model names to GitHub Models equivalents
        model_mapping = {
            "gpt-5.2-codex": "gpt-4o",  # Map gpt-5.2-codex to best available model
            "gpt-5.2": "gpt-4o",
            "gpt-4": "gpt-4o",
            "gpt-3.5-turbo": "gpt-4o-mini",
            "claude-sonnet-4.5": "gpt-4o",  # GitHub Models doesn't have Claude
            "claude-3-5-sonnet-20241022": "gpt-4o"
        }
        
        # Default to gpt-4o model
        requested_model = model or "gpt-4o"
        model_name = model_mapping.get(requested_model, requested_model)
        
        try:
            import requests
            
            # GitHub Models API endpoint (supports enterprise)
            url = f"{self.endpoint}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Add enterprise organization context if available
            if self.org and self._is_enterprise:
                headers["X-GitHub-Organization"] = self.org
            
            data = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": temperature,
                "max_tokens": min(max_tokens, 4000)  # GitHub Models free tier limit
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                
                return AIResponse(
                    content=content,
                    provider=AIProviderType.GITHUB_MODELS,
                    model=model_name,
                    usage=usage
                )
            else:
                logger.warning(f"GitHub Models API error: {response.status_code} - {response.text[:200]}")
                return None
                
        except Exception as e:
            logger.warning(f"GitHub Models generation failed: {e}")
            return None


class OpenAIProvider(AIProvider):
    """OpenAI API provider (Fallback #2)"""
    
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
            from openai import OpenAI  # type: ignore[import-not-found]
            self._client = OpenAI(api_key=self.api_key)
            logger.info("OpenAI client initialized successfully")
            return True
        except ImportError:
            logger.debug("OpenAI SDK not installed (pip install openai)")
            return False
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("OpenAI initialization failed: %s", e)
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
                model=model or "gpt-5.2-codex",
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
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("OpenAI generation failed: %s", e)
        
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
            from openai import AzureOpenAI  # type: ignore[import-not-found]
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
        except (OSError, RuntimeError, ValueError) as e:
            logger.warning("Azure OpenAI initialization failed: %s", e)
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
        except (RuntimeError, ValueError, OSError) as e:
            logger.warning("Azure OpenAI generation failed: %s", e)
        
        return None


class AIProviderChain:
    """
    Chain of AI providers with automatic fallback.
    
    Priority order:
    1. GitHub Copilot SDK (requires Copilot CLI installed and authenticated)
    2. GitHub Models API (requires GITHUB_TOKEN)
    3. OpenAI API (requires OPENAI_API_KEY)
    4. Azure OpenAI (requires AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT)
    5. Template-based fallback (always available)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._providers: List[AIProvider] = []
        self._active_provider: Optional[AIProvider] = None
        self._initialized = False
        self._provider_order: List[str] = ["copilot", "github_models", "openai", "azure_openai"]
        self.configure(self.config)

    def configure(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Update runtime configuration for provider order selection."""
        if config is not None:
            self.config = config

        runtime_cfg = {}
        if isinstance(self.config, dict):
            runtime_cfg = self.config.get("runtime", {}) or {}

        provider_order = runtime_cfg.get("provider_order")
        if isinstance(provider_order, list) and provider_order:
            self._provider_order = [p for p in provider_order if isinstance(p, str)]
        else:
            provider = runtime_cfg.get("provider")
            if isinstance(provider, str):
                self._provider_order = [provider, "github_models", "openai", "azure_openai"]
    
    def _initialize_providers(self):
        """Initialize provider chain in priority order (with timeout protection)"""
        if self._initialized:
            return
        
        self._initialized = True
        
        logger.debug(f"Initializing provider chain with order: {self._provider_order}")
        
        # Get runtime config for provider-specific settings
        runtime_cfg = {}
        if isinstance(self.config, dict):
            runtime_cfg = self.config.get("runtime", {}) or {}
        
        # Priority order: Copilot -> GitHub Models -> OpenAI -> Azure OpenAI
        providers_config = {
            "copilot": CopilotProvider,
            "github_models": GitHubModelsProvider,
            "openai": OpenAIProvider,
            "azure_openai": AzureOpenAIProvider,
        }
        
        for name in self._provider_order:
            provider_class = providers_config.get(name)
            if not provider_class:
                continue
            try:
                # Pass enterprise config to GitHub Models provider
                if name == "github_models":
                    github_config = runtime_cfg.get("github_models", {}) or {}
                    provider = provider_class(
                        endpoint=github_config.get("endpoint"),
                        org=github_config.get("org")
                    )
                else:
                    provider = provider_class()
                # Wrap is_available() check with timeout to prevent hangs
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Provider {name} check timed out")
                
                # Set 3 second timeout for provider checks (Windows doesn't support signal.SIGALRM)
                # Use threading timeout instead
                import threading
                available = [False]
                exception = [None]
                
                def check_provider():
                    try:
                        available[0] = provider.is_available()
                    except Exception as e:
                        exception[0] = e
                
                thread = threading.Thread(target=check_provider, daemon=True)
                thread.start()
                thread.join(timeout=3.0)  # 3 second timeout
                
                if thread.is_alive():
                    # Timeout - provider check is hanging
                    logger.debug("Provider %s check timed out (hanging)", name)
                    continue
                
                if exception[0]:
                    raise exception[0]
                
                if available[0]:
                    self._providers.append(provider)
                    logger.info("AI Provider available: %s", name)
            except (OSError, RuntimeError, ValueError, TimeoutError) as e:
                logger.debug("AI Provider %s initialization error: %s", name, e)
        
        if self._providers:
            self._active_provider = self._providers[0]
            logger.info("Primary AI Provider: %s", self._active_provider.provider_type.value)
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
                logger.debug("Trying provider: %s", provider.provider_type.value)
                response = provider.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                if response:
                    logger.info("AI generation successful using %s", provider.provider_type.value)
                    return response
                else:
                    logger.debug("Provider %s returned None, trying next", provider.provider_type.value)
            except (RuntimeError, ValueError, OSError) as e:
                logger.warning("Provider %s failed: %s", provider.provider_type.value, e)
                continue
        
        logger.error(
            "All AI providers failed. Please configure at least one AI provider:\\n"
            "  - GitHub Copilot: Run 'gh auth login'\\n"
            "  - GitHub Models: Set GITHUB_TOKEN\\n"
            "  - OpenAI: Set OPENAI_API_KEY\\n"
            "  - Azure OpenAI: Configure Azure credentials"
        )
        return None


def get_ai_provider(config: Optional[Dict[str, Any]] = None) -> AIProviderChain:
    """Get the global AI provider chain"""
    instance = getattr(get_ai_provider, "_instance", None)
    if instance is None:
        instance = AIProviderChain(config=config)
        setattr(get_ai_provider, "_instance", instance)
    elif config is not None:
        instance.configure(config)
    return instance


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
