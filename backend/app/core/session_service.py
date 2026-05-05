"""
Session Service - Centralized session management
Provides a clean interface for session operations used by routes and services
"""
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class SessionService:
    """
    Service layer for managing user sessions.
    Acts as a bridge between HTTP routes and business logic services.
    """
    
    def __init__(self):
        # In-memory storage (can be replaced with Redis/DB later)
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, ticker: str, market: str) -> str:
        """
        Create a new session with initial data.
        
        Args:
            ticker: Stock ticker symbol
            market: Market identifier (e.g., 'US', 'IN')
            
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
            "current_step": 1,
            "data": {}  # Container for all step data
        }
        return session_id
    
    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete session data.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Session data dict or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            session["updated_at"] = datetime.utcnow().isoformat()
        return session
    
    def update_session_step(self, session_id: str, step_number: int) -> bool:
        """
        Update the current step in the session.
        
        Args:
            session_id: The session identifier
            step_number: The step number to set
            
        Returns:
            True if successful, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session["current_step"] = step_number
        session["updated_at"] = datetime.utcnow().isoformat()
        return True
    
    def update_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Update specific data in the session.
        
        Args:
            session_id: The session identifier
            key: Data key to update
            value: Value to store
            
        Returns:
            True if successful, False if session not found
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        session["data"][key] = value
        session["updated_at"] = datetime.utcnow().isoformat()
        return True
    
    def get_session_value(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Get a specific value from session data.
        
        Args:
            session_id: The session identifier
            key: Data key to retrieve
            default: Default value if key not found
            
        Returns:
            The value or default
        """
        session = self._sessions.get(session_id)
        if not session:
            return default
        return session["data"].get(key, default)
    
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
