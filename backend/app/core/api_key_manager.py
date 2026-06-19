"""
Unified API Key Manager - Multi-key storage with automatic fallback and rotation.

Provides a single source of truth for managing multiple API keys per service,
with automatic rotation on rate limits, usage tracking, and debug visibility.

Services supported:
- AlphaVantage (RapidAPI + Direct)
- FRED (Federal Reserve Economic Data)
- FMP (Financial Modeling Prep)
- OpenRouter (AI)
- Groq (AI)
- Gemini (AI)
- Qwen/DashScope (AI)
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class KeyStatus(str, Enum):
    ACTIVE = "active"
    RATE_LIMITED = "rate_limited"
    INVALID = "invalid"
    EXHAUSTED = "exhausted"
    UNKNOWN = "unknown"


@dataclass
class ApiKeyEntry:
    """A single API key with metadata."""
    key: str
    service: str
    source: str  # "env", "session", "header", "hardcoded"
    status: KeyStatus = KeyStatus.ACTIVE
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100
    
    @property
    def masked_key(self) -> str:
        if len(self.key) <= 8:
            return "***"
        return f"{self.key[:4]}...{self.key[-4:]}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "masked_key": self.masked_key,
            "source": self.source,
            "status": self.status.value,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "rate_limit_hits": self.rate_limit_hits,
            "success_rate": f"{self.success_rate:.1f}%",
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
        }


@dataclass
class ServiceKeyPool:
    """Pool of keys for a single service with rotation logic."""
    service_name: str
    keys: List[ApiKeyEntry] = field(default_factory=list)
    current_index: int = 0
    max_retries_per_rotation: int = 2
    
    @property
    def current_key(self) -> Optional[ApiKeyEntry]:
        if not self.keys:
            return None
        return self.keys[self.current_index % len(self.keys)]
    
    @property
    def current_key_value(self) -> Optional[str]:
        ck = self.current_key
        return ck.key if ck else None
    
    def get_next_key(self) -> Optional[ApiKeyEntry]:
        """Rotate to next available key."""
        if len(self.keys) <= 1:
            return None
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.keys)
        new_key = self.keys[self.current_index]
        logger.info(f"[{self.service_name}] Rotated from key #{old_index+1} to #{self.current_index+1} ({new_key.masked_key})")
        return new_key
    
    def record_success(self):
        ck = self.current_key
        if ck:
            ck.total_requests += 1
            ck.successful_requests += 1
            ck.last_used = datetime.now()
            ck.status = KeyStatus.ACTIVE
    
    def record_failure(self, error: str, is_rate_limit: bool = False):
        ck = self.current_key
        if ck:
            ck.total_requests += 1
            ck.failed_requests += 1
            ck.last_used = datetime.now()
            ck.last_error = error
            ck.last_error_time = datetime.now()
            if is_rate_limit:
                ck.rate_limit_hits += 1
                ck.status = KeyStatus.RATE_LIMITED
            else:
                ck.status = KeyStatus.INVALID
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "total_keys": len(self.keys),
            "current_key_index": self.current_index + 1,
            "current_key": self.current_key.to_dict() if self.current_key else None,
            "all_keys": [k.to_dict() for k in self.keys],
        }


class ApiKeyManager:
    """
    Unified API Key Manager - singleton pattern.
    
    Manages multiple keys per service with automatic rotation on rate limits.
    Tracks usage, errors, and provides debug visibility.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._pools: Dict[str, ServiceKeyPool] = {}
        # Ensure .env is loaded before reading env vars
        load_dotenv(Path(__file__).resolve().parent.parent / ".env")
        self._initialize_from_env()
        logger.info("ApiKeyManager initialized")
    
    def _initialize_from_env(self):
        """Load keys from environment variables."""
        # AlphaVantage RapidAPI keys
        av_keys = []
        env_av_keys = os.getenv('RAPIDAPI_AV_KEYS', '')
        if env_av_keys:
            av_keys.extend([k.strip() for k in env_av_keys.split(',') if k.strip()])
        default_av_key = os.getenv('RAPIDAPI_AV_KEY', 'b9d602a26amshc86281b315604e1p1a42ccjsn7529ee98cb60')
        if default_av_key and default_av_key not in av_keys:
            av_keys.insert(0, default_av_key)
        if av_keys:
            self.register_service('alphavantage', av_keys, source='env')
        
        # FRED
        fred_key = os.getenv('FRED_API_KEY')
        if fred_key:
            self.register_service('fred', [fred_key], source='env')
        
        # FMP
        fmp_key = os.getenv('FMP_API_KEY') or os.getenv('FINANCIAL_MODELING_PREP_API_KEY')
        if fmp_key:
            self.register_service('fmp', [fmp_key], source='env')
        
        # AI providers - each can have multiple keys
        for service, env_vars in [
            ('openrouter', ['OPENROUTER_API_KEY']),
            ('groq', ['GROQ_API_KEY']),
            ('gemini', ['GOOGLE_GEMINI_API_KEY', 'GEMINI_API_KEY']),
            ('qwen', ['DASHSCOPE_API_KEY', 'QWEN_API_KEY']),
        ]:
            keys = []
            for env_var in env_vars:
                val = os.getenv(env_var)
                if val:
                    keys.append(val)
            # Also check for plural env var (comma-separated)
            plural_var = os.getenv(f'{env_vars[0]}S', '')  # e.g., OPENROUTER_API_KEYS
            if plural_var:
                keys.extend([k.strip() for k in plural_var.split(',') if k.strip()])
            if keys:
                self.register_service(service, keys, source='env')
    
    def register_service(self, service_name: str, keys: List[str], source: str = 'env'):
        """Register keys for a service."""
        if service_name not in self._pools:
            self._pools[service_name] = ServiceKeyPool(service_name=service_name)
        
        pool = self._pools[service_name]
        existing_key_values = {k.key for k in pool.keys}
        
        for key_value in keys:
            if key_value and key_value not in existing_key_values:
                entry = ApiKeyEntry(key=key_value, service=service_name, source=source)
                pool.keys.append(entry)
                existing_key_values.add(key_value)
        
        logger.info(f"[{service_name}] Registered {len(pool.keys)} key(s)")
    
    def add_key(self, service_name: str, key_value: str, source: str = 'session'):
        """Add a key at runtime (e.g., from session storage)."""
        if service_name not in self._pools:
            self._pools[service_name] = ServiceKeyPool(service_name=service_name)
        
        pool = self._pools[service_name]
        existing_key_values = {k.key for k in pool.keys}
        
        if key_value and key_value not in existing_key_values:
            entry = ApiKeyEntry(key=key_value, service=service_name, source=source)
            pool.keys.append(entry)
            logger.info(f"[{service_name}] Added key from {source}: {entry.masked_key}")
    
    def get_key(self, service_name: str) -> Optional[str]:
        """Get current active key for a service."""
        pool = self._pools.get(service_name)
        if not pool:
            return None
        return pool.current_key_value
    
    def record_success(self, service_name: str):
        """Record successful API call."""
        pool = self._pools.get(service_name)
        if pool:
            pool.record_success()
    
    def record_failure(self, service_name: str, error: str, is_rate_limit: bool = False):
        """Record failed API call and rotate if rate limited."""
        pool = self._pools.get(service_name)
        if pool:
            pool.record_failure(error, is_rate_limit)
            if is_rate_limit:
                pool.get_next_key()
    
    def rotate_key(self, service_name: str) -> Optional[str]:
        """Manually rotate to next key."""
        pool = self._pools.get(service_name)
        if pool:
            new_key = pool.get_next_key()
            return new_key.key if new_key else None
        return None
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all services and keys."""
        return {
            service: pool.get_status()
            for service, pool in self._pools.items()
        }
    
    def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific service."""
        pool = self._pools.get(service_name)
        return pool.get_status() if pool else None
    
    def load_from_session(self, session_id: str):
        """Load keys from session storage."""
        try:
            from app.core.session_service import session_service
            session = session_service.get_session_data(session_id)
            if not session:
                return
            
            api_keys = session.get('data', {}).get('api_keys', session.get('api_keys', {}))
            if not api_keys:
                return
            
            key_mapping = {
                'alpha_vantage': 'alphavantage',
                'fred': 'fred',
                'fmp': 'fmp',
                'openrouter': 'openrouter',
                'groq': 'groq',
                'gemini': 'gemini',
                'qwen': 'qwen',
            }
            
            for session_key, service_name in key_mapping.items():
                key_value = api_keys.get(session_key)
                if key_value:
                    self.add_key(service_name, key_value, source='session')
        except Exception as e:
            logger.warning(f"Failed to load keys from session: {e}")


# Singleton instance
api_key_manager = ApiKeyManager()


def get_key_with_status(service_name: str, request=None, session_id: str = None) -> Optional[str]:
    """
    Get API key with full fallback chain and status tracking.
    
    Priority:
    1. Request header
    2. Session storage
    3. ApiKeyManager (env vars + registered keys)
    """
    # Try request header first
    if request:
        api_keys = getattr(request, 'state', None)
        if api_keys:
            api_keys_dict = getattr(api_keys, 'api_keys', {})
            header_key = api_keys_dict.get(service_name)
            if header_key:
                return header_key
    
    # Try session storage
    if session_id:
        try:
            from app.core.session_service import session_service
            session = session_service.get_session_data(session_id)
            if session:
                api_keys = session.get('data', {}).get('api_keys', session.get('api_keys', {}))
                session_key = api_keys.get(service_name)
                if session_key:
                    return session_key
        except Exception:
            pass
    
    # Fall back to manager
    return api_key_manager.get_key(service_name)
