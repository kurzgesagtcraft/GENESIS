"""
LLM 客户端模块

支持多种后端:
- OpenAI GPT-4 API
- 本地 Qwen2.5-72B (via vLLM)
- 本地 Llama 3 (via Ollama)

统一接口，支持重试逻辑、token 计数和缓存。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import json
import time
from typing import Any, Dict, List, Optional, Callable
import hashlib
import threading


class LLMProvider(Enum):
    """LLM 提供商"""
    OPENAI = "openai"
    VLLM = "vllm"
    OLLAMA = "ollama"
    MOCK = "mock"  # 用于测试


@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: LLMProvider = LLMProvider.MOCK
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: float = 60.0
    retry_count: int = 3
    retry_delay: float = 1.0
    enable_cache: bool = True
    cache_ttl: float = 3600.0  # 缓存有效期 (秒)


@dataclass
class LLMResponse:
    """LLM 响应"""
    content: str
    model: str
    usage: Dict[str, int]
    latency: float
    cached: bool = False
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", 0)


class CacheEntry:
    """缓存条目"""
    def __init__(self, content: str, ttl: float):
        self.content = content
        self.expires_at = time.time() + ttl
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class LLMCache:
    """LLM 响应缓存"""
    
    def __init__(self, ttl: float = 3600.0):
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = ttl
        self._lock = threading.Lock()
    
    def _hash_key(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """生成缓存键"""
        key = f"{system_prompt or ''}|{prompt}"
        return hashlib.sha256(key.encode()).hexdigest()
    
    def get(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """获取缓存"""
        key = self._hash_key(prompt, system_prompt)
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired():
                return entry.content
            elif entry:
                del self._cache[key]
        return None
    
    def set(self, prompt: str, content: str, system_prompt: Optional[str] = None):
        """设置缓存"""
        key = self._hash_key(prompt, system_prompt)
        with self._lock:
            self._cache[key] = CacheEntry(content, self._ttl)
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()


class LLMBackend(ABC):
    """LLM 后端抽象基类"""
    
    @abstractmethod
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """发送聊天请求"""
        pass
    
    @abstractmethod
    def chat_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """发送聊天请求并返回 JSON"""
        pass


class MockBackend(LLMBackend):
    """Mock 后端 (用于测试)"""
    
    def __init__(self):
        self.call_count = 0
        self.last_prompt: Optional[str] = None
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self.call_count += 1
        self.last_prompt = prompt
        
        # 返回一个简单的 JSON 格式响应
        mock_response = """
        [
            {"task_id": 1, "type": "mine", "target": "iron_ore", "quantity": 3},
            {"task_id": 2, "type": "deliver_to_station", "items": ["iron_ore", "iron_ore", "iron_ore"], "station": "smelter"},
            {"task_id": 3, "type": "start_processing", "station": "smelter", "recipe": "smelt_iron"},
            {"task_id": 4, "type": "wait_or_parallel", "description": "等待冶炼完成"},
            {"task_id": 5, "type": "collect", "station": "smelter", "expected_output": "iron_bar", "quantity": 2}
        ]
        """
        
        return LLMResponse(
            content=mock_response.strip(),
            model="mock-model",
            usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            latency=0.1,
        )
    
    def chat_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(prompt, system_prompt, temperature, max_tokens)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": response.content}


class OpenAIBackend(LLMBackend):
    """OpenAI 后端"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                )
            except ImportError:
                raise ImportError("请安装 openai: pip install openai")
        return self._client
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = time.time() - start_time
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            latency=latency,
        )
    
    def chat_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加 JSON 格式要求
        json_prompt = f"{prompt}\n\n请以 JSON 格式返回结果，遵循以下 schema:\n{json.dumps(schema, ensure_ascii=False, indent=2)}"
        messages.append({"role": "user", "content": json_prompt})
        
        start_time = time.time()
        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        latency = time.time() - start_time
        
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": content}


class VLLMBackend(LLMBackend):
    """vLLM 后端 (本地部署)"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                import requests
                self._client = requests
            except ImportError:
                raise ImportError("请安装 requests: pip install requests")
        return self._client
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import requests
        
        base_url = self.config.base_url or "http://localhost:8000"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json={
                "model": self.config.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=self.config.timeout,
        )
        latency = time.time() - start_time
        
        data = response.json()
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.config.model),
            usage=data.get("usage", {"total_tokens": 0}),
            latency=latency,
        )
    
    def chat_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(prompt, system_prompt, temperature, max_tokens)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": response.content}


class OllamaBackend(LLMBackend):
    """Ollama 后端 (本地部署)"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import requests
                self._client = requests
            except ImportError:
                raise ImportError("请安装 requests: pip install requests")
        return self._client
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        import requests
        
        base_url = self.config.base_url or "http://localhost:11434"
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": self.config.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            },
            timeout=self.config.timeout,
        )
        latency = time.time() - start_time
        
        data = response.json()
        return LLMResponse(
            content=data["message"]["content"],
            model=self.config.model,
            usage={"total_tokens": data.get("eval_count", 0) + data.get("prompt_eval_count", 0)},
            latency=latency,
        )
    
    def chat_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        response = self.chat(prompt, system_prompt, temperature, max_tokens)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw": response.content}


class LLMClient:
    """
    LLM 统一客户端
    
    支持多种后端，提供统一的接口。
    支持重试逻辑、token 计数和缓存。
    
    使用示例:
    ```python
    config = LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4")
    client = LLMClient(config)
    
    response = client.chat("你好，请介绍一下自己")
    print(response.content)
    
    # JSON 响应
    schema = {"type": "array", "items": {"type": "string"}}
    result = client.chat_json("列出5种水果", schema)
    print(result)
    ```
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self._backend = self._create_backend()
        self._cache = LLMCache(config.cache_ttl) if config.enable_cache else None
        self._total_tokens = 0
        self._call_count = 0
        self._total_latency = 0.0
    
    def _create_backend(self) -> LLMBackend:
        """创建后端实例"""
        backends = {
            LLMProvider.OPENAI: OpenAIBackend,
            LLMProvider.VLLM: VLLMBackend,
            LLMProvider.OLLAMA: OllamaBackend,
            LLMProvider.MOCK: MockBackend,
        }
        backend_class = backends.get(self.config.provider)
        if backend_class is None:
            raise ValueError(f"不支持的 LLM 提供商: {self.config.provider}")
        # MockBackend 不需要 config 参数
        if self.config.provider == LLMProvider.MOCK:
            return backend_class()
        return backend_class(self.config)
    
    def _retry_with_backoff(
        self,
        func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """带退避的重试"""
        last_error = None
        for attempt in range(self.config.retry_count):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.config.retry_count - 1:
                    delay = self.config.retry_delay * (2 ** attempt)
                    time.sleep(delay)
        raise last_error
    
    def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        发送聊天请求
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示
            temperature: 温度参数 (覆盖配置)
            max_tokens: 最大 token 数 (覆盖配置)
        
        Returns:
            LLMResponse: 响应对象
        """
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        # 检查缓存
        if self._cache:
            cached = self._cache.get(prompt, system_prompt)
            if cached:
                return LLMResponse(
                    content=cached,
                    model=self.config.model,
                    usage={"total_tokens": 0},
                    latency=0.0,
                    cached=True,
                )
        
        # 发送请求
        response = self._retry_with_backoff(
            self._backend.chat,
            prompt,
            system_prompt,
            temperature,
            max_tokens,
        )
        
        # 更新统计
        self._total_tokens += response.total_tokens
        self._call_count += 1
        self._total_latency += response.latency
        
        # 缓存响应
        if self._cache:
            self._cache.set(prompt, response.content, system_prompt)
        
        return response
    
    def chat_json(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回 JSON
        
        Args:
            prompt: 用户输入
            schema: JSON schema
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
        
        Returns:
            Dict: JSON 响应
        """
        temperature = temperature if temperature is not None else self.config.temperature
        max_tokens = max_tokens if max_tokens is not None else self.config.max_tokens
        
        response = self._retry_with_backoff(
            self._backend.chat_json,
            prompt,
            schema,
            system_prompt,
            temperature,
            max_tokens,
        )
        
        return response
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tokens": self._total_tokens,
            "call_count": self._call_count,
            "total_latency": self._total_latency,
            "avg_latency": self._total_latency / self._call_count if self._call_count > 0 else 0,
        }
    
    def clear_cache(self):
        """清空缓存"""
        if self._cache:
            self._cache.clear()
