"""
Session Service - Centralized session management
Provides a clean interface for session operations used by routes and services

MATRIX WORKFLOW SUPPORT (Phase 1):
- Nested structure: valuations[market][method] for parallel valuations
- Shared context: Steps 1-3 data accessible by all methods
- Backward compatibility: Legacy linear sessions auto-migrated
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import asyncio


class SessionService:
    """
    Service layer for managing user sessions with matrix workflow support.
    
    SESSION STRUCTURE:
    {
        "session_id": str,
        "ticker": str,
        "market": str,
        "created_at": str,
        "updated_at": str,
        "status": str,
        
        # SHARED CONTEXT (Steps 1-3)
        "shared_context": {
            "company_overview": {...},
            "peer_selection": {...},
            "historical_data": {...},
            "market_data": {...}
        },
        
        # MATRIX VALUATIONS (Steps 4-10 per method)
        "valuations": {
            "international": {
                "dcf": {
                    "status": str,
                    "current_step": int,
                    "data": {...},
                    "results": {...}
                },
                "dupont": {...},
                "comps": {...}
            },
            "vietnam": {...}
        }
    }
    """
    
    def __init__(self):
        # In-memory storage (can be replaced with Redis/DB later)
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # Async lock for thread-safe session updates during parallel execution
        self._lock = asyncio.Lock()
    
    def create_session(self, ticker: str, market: str) -> str:
        """
        Create a new session with matrix-compatible structure.
        
        Args:
            ticker: Stock ticker symbol
            market: Market identifier (e.g., 'US', 'IN', 'VN')
            
        Returns:
            Session ID string
        """
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {
            "session_id": session_id,
            "ticker": ticker,
            "market": market,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "active",
            
            # SHARED CONTEXT - Steps 1-3 (common to all valuation methods)
            "shared_context": {
                "company_overview": None,
                "peer_selection": None,
                "historical_data": None,
                "market_data": None,
                "step_completed": 0
            },
            
            # MATRIX VALUATIONS - Separate tracks per market/method
            "valuations": {
                "international": {
                    "dcf": {
                        "status": "not_started",
                        "current_step": 0,
                        "data": {},
                        "results": None,
                        "last_updated": None
                    },
                    "dupont": {
                        "status": "not_started",
                        "current_step": 0,
                        "data": {},
                        "results": None,
                        "last_updated": None
                    },
                    "comps": {
                        "status": "not_started",
                        "current_step": 0,
                        "data": {},
                        "results": None,
                        "last_updated": None
                    }
                },
                "vietnam": {
                    "dcf": {
                        "status": "not_started",
                        "current_step": 0,
                        "data": {},
                        "results": None,
                        "last_updated": None
                    },
                    "dupont": {
                        "status": "not_started",
                        "current_step": 0,
                        "data": {},
                        "results": None,
                        "last_updated": None
                    },
                    "comps": {
                        "status": "not_started",
                        "current_step": 0,
                        "data": {},
                        "results": None,
                        "last_updated": None
                    }
                }
            }
        }
        return session_id
    
    def _migrate_legacy_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate legacy linear session to matrix structure.
        
        Args:
            session: Legacy session data
            
        Returns:
            Migrated session with matrix structure
        """
        if "valuations" in session and "shared_context" in session:
            # Already migrated
            return session
        
        # Add matrix structure
        if "valuations" not in session:
            session["valuations"] = {
                "international": {
                    "dcf": {"status": "not_started", "current_step": 0, "data": {}, "results": None, "last_updated": None},
                    "dupont": {"status": "not_started", "current_step": 0, "data": {}, "results": None, "last_updated": None},
                    "comps": {"status": "not_started", "current_step": 0, "data": {}, "results": None, "last_updated": None}
                },
                "vietnam": {
                    "dcf": {"status": "not_started", "current_step": 0, "data": {}, "results": None, "last_updated": None},
                    "dupont": {"status": "not_started", "current_step": 0, "data": {}, "results": None, "last_updated": None},
                    "comps": {"status": "not_started", "current_step": 0, "data": {}, "results": None, "last_updated": None}
                }
            }
        
        if "shared_context" not in session:
            session["shared_context"] = {
                "company_overview": None,
                "peer_selection": None,
                "historical_data": None,
                "market_data": None,
                "step_completed": 0
            }
            
            # Migrate legacy data fields to shared_context
            legacy_to_shared = {
                "company_info": "company_overview",
                "peer_tickers": "peer_selection",
                "selected_peers": "peer_selection",
                "financial_data": "historical_data",
                "retrieved_assumptions": "market_data"
            }
            
            for legacy_key, shared_key in legacy_to_shared.items():
                if legacy_key in session.get("data", {}):
                    session["shared_context"][shared_key] = session["data"][legacy_key]
        
        # Migrate selected_model data to appropriate valuation track
        if "selected_model" in session["data"]:
            model = session["data"]["selected_model"].upper()
            market = session.get("market", "international").lower()
            if market == "vn" or market == "vietnam":
                market = "vietnam"
            else:
                market = "international"
            
            # Copy legacy data to the correct valuation track
            session["valuations"][market][model.lower()] = {
                "status": session.get("status", "in_progress"),
                "current_step": session.get("current_step", 0),
                "data": session.get("data", {}),
                "results": session.get("data", {}).get("valuation_results"),
                "last_updated": session.get("updated_at")
            }
        
        session["updated_at"] = datetime.utcnow().isoformat()
        return session
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete session data with automatic legacy migration.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session data dict or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            # Auto-migrate legacy sessions
            session = self._migrate_legacy_session(session)
            session["updated_at"] = datetime.utcnow().isoformat()
        return session
    
    def update_session_step(self, session_id: str, step_number: int, 
                           market: str = "international", method: str = "dcf") -> bool:
        """
        Update the current step in a specific valuation track.
        
        Args:
            session_id: The session identifier
            step_number: The step number to set (1-10)
            market: Market ('international' or 'vietnam')
            method: Valuation method ('dcf', 'dupont', 'comps')
            
        Returns:
            True if successful, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        # Migrate if needed
        session = self._migrate_legacy_session(session)
        
        # Update specific valuation track
        if market in session["valuations"] and method.lower() in session["valuations"][market]:
            session["valuations"][market][method.lower()]["current_step"] = step_number
            session["valuations"][market][method.lower()]["last_updated"] = datetime.utcnow().isoformat()
        
        session["updated_at"] = datetime.utcnow().isoformat()
        return True
    
    def update_session_data(self, session_id: str, key: str, value: Any,
                           market: str = None, method: str = None) -> bool:
        """
        Update specific data in the session.
        
        For matrix workflow:
        - If market/method provided: stores in valuations[market][method][data]
        - If no market/method: stores in shared_context (for Steps 1-3)
        
        For backward compatibility:
        - Legacy calls without market/method still work with old structure
        
        Args:
            session_id: The session identifier
            key: Data key to update
            value: Value to store
            market: Optional market for matrix storage
            method: Optional method for matrix storage
            
        Returns:
            True if successful, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        # Migrate if needed
        session = self._migrate_legacy_session(session)
        
        # Matrix-aware storage
        if market and method:
            market = market.lower()
            method = method.lower()
            if market in session["valuations"] and method in session["valuations"][market]:
                session["valuations"][market][method]["data"][key] = value
                session["valuations"][market][method]["last_updated"] = datetime.utcnow().isoformat()
        else:
            # Shared context for Steps 1-3 or backward compatibility
            # Map legacy keys to shared_context
            shared_keys = ["company_overview", "peer_selection", "historical_data", "market_data"]
            if key in shared_keys:
                session["shared_context"][key] = value
            else:
                # Legacy fallback - ensure data dict exists
                if "data" not in session:
                    session["data"] = {}
                session["data"][key] = value
        
        session["updated_at"] = datetime.utcnow().isoformat()
        return True
    
    def get_session_value(self, session_id: str, key: str, default: Any = None,
                         market: str = None, method: str = None) -> Any:
        """
        Get a specific value from session data.
        
        For matrix workflow:
        - If market/method provided: retrieves from valuations[market][method][data]
        - If no market/method: retrieves from shared_context first, then legacy data
        
        Args:
            session_id: The session identifier
            key: Data key to retrieve
            default: Default value if key not found
            market: Optional market for matrix retrieval
            method: Optional method for matrix retrieval
            
        Returns:
            The value or default
        """
        session = self._sessions.get(session_id)
        if not session:
            return default
        
        # Migrate if needed
        session = self._migrate_legacy_session(session)
        
        # Matrix-aware retrieval
        if market and method:
            market = market.lower()
            method = method.lower()
            if market in session["valuations"] and method in session["valuations"][market]:
                return session["valuations"][market][method]["data"].get(key, default)
        
        # Try shared_context first (Steps 1-3 data)
        if key in session["shared_context"]:
            return session["shared_context"][key]
        
        # Legacy fallback
        return session["data"].get(key, default)
    
    def update_shared_context(self, session_id: str, key: str, value: Any) -> bool:
        """
        Update shared context data (Steps 1-3).
        
        Args:
            session_id: The session identifier
            key: Context key (company_overview, peer_selection, historical_data, market_data)
            value: Value to store
            
        Returns:
            True if successful, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session = self._migrate_legacy_session(session)
        
        valid_keys = ["company_overview", "peer_selection", "historical_data", "market_data"]
        if key not in valid_keys:
            return False
        
        session["shared_context"][key] = value
        session["shared_context"]["step_completed"] = max(
            session["shared_context"]["step_completed"],
            valid_keys.index(key) + 1
        )
        session["updated_at"] = datetime.utcnow().isoformat()
        return True
    
    def get_shared_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all shared context data (Steps 1-3).
        
        Args:
            session_id: The session identifier
            
        Returns:
            Shared context dict or None
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        session = self._migrate_legacy_session(session)
        return session["shared_context"]
    
    def update_valuation_status(self, session_id: str, market: str, method: str, 
                               status: str) -> bool:
        """
        Update status of a specific valuation track.
        
        Args:
            session_id: The session identifier
            market: Market ('international' or 'vietnam')
            method: Valuation method ('dcf', 'dupont', 'comps')
            status: Status string ('not_started', 'in_progress', 'completed', 'error')
            
        Returns:
            True if successful, False if session/track not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session = self._migrate_legacy_session(session)
        
        market = market.lower()
        method = method.lower()
        
        if market in session["valuations"] and method in session["valuations"][market]:
            session["valuations"][market][method]["status"] = status
            session["valuations"][market][method]["last_updated"] = datetime.utcnow().isoformat()
            session["updated_at"] = datetime.utcnow().isoformat()
            return True
        
        return False
    
    def get_valuation_track(self, session_id: str, market: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Get complete valuation track data.
        
        Args:
            session_id: The session identifier
            market: Market ('international' or 'vietnam')
            method: Valuation method ('dcf', 'dupont', 'comps')
            
        Returns:
            Valuation track dict or None
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        session = self._migrate_legacy_session(session)
        
        market = market.lower()
        method = method.lower()
        
        if market in session["valuations"] and method in session["valuations"][market]:
            return session["valuations"][market][method]
        
        return None
    
    async def save_valuation_results(self, session_id: str, market: str, method: str, 
                              results: Dict[str, Any]) -> bool:
        """
        Save valuation results to a specific track (async-safe for parallel execution).
        
        Uses asyncio.Lock to prevent race conditions when multiple methods
        save results simultaneously during parallel execution.
        
        Args:
            session_id: The session identifier
            market: Market ('international' or 'vietnam')
            method: Valuation method ('dcf', 'dupont', 'comps')
            results: Valuation results dictionary
            
        Returns:
            True if successful, False if session/track not found
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return False
            
            session = self._migrate_legacy_session(session)
            
            market = market.lower()
            method = method.lower()
            
            if market in session["valuations"] and method in session["valuations"][market]:
                session["valuations"][market][method]["results"] = results
                session["valuations"][market][method]["status"] = "completed"
                session["valuations"][market][method]["last_updated"] = datetime.utcnow().isoformat()
                session["updated_at"] = datetime.utcnow().isoformat()
                return True
            
            return False
    
    def get_all_valuations(self, session_id: str) -> Optional[Dict[str, Dict[str, Dict[str, Any]]]]:
        """
        Get all valuation tracks for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Nested dict: {market: {method: track_data}}
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        session = self._migrate_legacy_session(session)
        return session["valuations"]
    
    def get_completed_valuations(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get all completed valuation results.
        
        Args:
            session_id: The session identifier
            
        Returns:
            List of {market, method, results} dicts
        """
        session = self._sessions.get(session_id)
        if not session:
            return []
        
        session = self._migrate_legacy_session(session)
        
        completed = []
        for market, methods in session["valuations"].items():
            for method, track in methods.items():
                if track["status"] == "completed" and track["results"]:
                    completed.append({
                        "market": market,
                        "method": method,
                        "results": track["results"],
                        "last_updated": track["last_updated"]
                    })
        
        return completed
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists.
        
        Args:
            session_id: The session identifier
            
        Returns:
            True if exists, False otherwise
        """
        return session_id in self._sessions


# Global instance for use across the application
session_service = SessionService()
