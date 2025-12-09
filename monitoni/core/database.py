"""
Database management for MoniToni vending machine system.

Provides SQLite database operations for logging and statistics.
Uses async operations to prevent UI blocking.
"""

import asyncio
import aiosqlite
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseManager:
    """
    Manages SQLite database operations for the vending machine.
    
    Handles:
    - Event and error logging
    - System statistics
    - Purchase tracking
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
        
    async def initialize(self) -> None:
        """Initialize database and create tables if needed."""
        self._connection = await aiosqlite.connect(str(self.db_path))
        await self._create_tables()
        
    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            
    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        async with self._connection.cursor() as cursor:
            # Logs table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    purchase_id TEXT,
                    level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on timestamp for faster queries
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp 
                ON logs(timestamp)
            """)
            
            # Create index on purchase_id
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_purchase_id 
                ON logs(purchase_id)
            """)
            
            # Statistics table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS statistics (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    completed_purchases INTEGER DEFAULT 0,
                    failed_purchases INTEGER DEFAULT 0,
                    network_incidents INTEGER DEFAULT 0,
                    server_incidents INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Initialize statistics if empty
            await cursor.execute("""
                INSERT OR IGNORE INTO statistics (id) VALUES (1)
            """)
            
            await self._connection.commit()
            
    async def add_log(
        self,
        level: LogLevel,
        message: str,
        purchase_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Add a log entry to the database.
        
        Args:
            level: Log level
            message: Log message
            purchase_id: Optional purchase ID for tracking
            details: Optional additional details as dictionary
        """
        timestamp = datetime.now().isoformat()
        details_json = json.dumps(details) if details else None
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO logs (timestamp, purchase_id, level, message, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (timestamp, purchase_id, level.value, message, details_json)
            )
            await self._connection.commit()
            
    async def get_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        level: Optional[LogLevel] = None,
        purchase_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs from database with optional filtering.
        
        Args:
            limit: Maximum number of logs to return
            offset: Number of logs to skip (for pagination)
            level: Filter by log level
            purchase_id: Filter by purchase ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            
        Returns:
            List of log entries as dictionaries
        """
        query = "SELECT * FROM logs WHERE 1=1"
        params = []
        
        if level:
            query += " AND level = ?"
            params.append(level.value)
            
        if purchase_id:
            query += " AND purchase_id = ?"
            params.append(purchase_id)
            
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
            
        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(query, params)
            rows = await cursor.fetchall()
            
            # Convert to dictionaries
            columns = [desc[0] for desc in cursor.description]
            logs = []
            for row in rows:
                log = dict(zip(columns, row))
                # Parse JSON details if present
                if log.get('details'):
                    try:
                        log['details'] = json.loads(log['details'])
                    except json.JSONDecodeError:
                        pass
                logs.append(log)
                
            return logs
    
    async def export_logs_json(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> str:
        """
        Export logs as JSON string for API.
        
        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            JSON string of logs
        """
        logs = await self.get_logs(
            limit=10000,
            start_date=start_date,
            end_date=end_date
        )
        return json.dumps(logs)
            
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get system statistics.
        
        Returns:
            Dictionary with statistics
        """
        async with self._connection.cursor() as cursor:
            await cursor.execute("SELECT * FROM statistics WHERE id = 1")
            row = await cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            else:
                return {
                    'completed_purchases': 0,
                    'failed_purchases': 0,
                    'network_incidents': 0,
                    'server_incidents': 0
                }
                
    async def increment_statistic(self, field: str, amount: int = 1) -> None:
        """
        Increment a statistic counter.
        
        Args:
            field: Field name (completed_purchases, failed_purchases, etc.)
            amount: Amount to increment by
        """
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                f"""
                UPDATE statistics 
                SET {field} = {field} + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
                """,
                (amount,)
            )
            await self._connection.commit()
            
    async def clear_old_logs(self, days: int = 30) -> int:
        """
        Delete logs older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of deleted logs
        """
        cutoff_date = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
        cutoff_str = cutoff_date.isoformat()
        
        async with self._connection.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM logs WHERE timestamp < ?",
                (cutoff_str,)
            )
            deleted = cursor.rowcount
            await self._connection.commit()
            
        return deleted
        
    async def export_logs_to_json(
        self,
        output_path: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> None:
        """
        Export logs to JSON file.
        
        Args:
            output_path: Path to output JSON file
            start_date: Optional start date filter
            end_date: Optional end date filter
        """
        logs = await self.get_logs(
            limit=999999,  # Get all matching logs
            start_date=start_date,
            end_date=end_date
        )
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(logs, f, indent=2)


# Global database instance
_db_manager: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """
    Get global database manager instance.
    
    Returns:
        DatabaseManager instance
    """
    global _db_manager
    if _db_manager is None:
        from monitoni.core.config import get_config
        config = get_config()
        _db_manager = DatabaseManager(config.database.path)
        await _db_manager.initialize()
    return _db_manager


async def close_database() -> None:
    """Close global database connection."""
    global _db_manager
    if _db_manager:
        await _db_manager.close()
        _db_manager = None
