"""
Logging system for MoniToni vending machine.

Provides centralized logging with dual output:
- Console output for development/debugging
- Database storage for telemetry and analysis
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
import asyncio

from monitoni.core.database import DatabaseManager, LogLevel


class DatabaseHandler(logging.Handler):
    """
    Custom logging handler that writes to database.
    
    Runs database operations in async context without blocking.
    Queues logs if event loop isn't ready yet, flushes when loop is set.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize database handler.
        
        Args:
            db_manager: Database manager instance
        """
        super().__init__()
        self.db_manager = db_manager
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._pending_logs = []  # Queue for logs before event loop is ready
        
    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop for async operations and flush pending logs."""
        self._loop = loop
        # Flush pending logs
        for log_data in self._pending_logs:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.db_manager.add_log(**log_data),
                    self._loop
                )
            except Exception:
                pass
        self._pending_logs.clear()
        
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to database.
        
        Args:
            record: Log record to emit
        """
        try:
            # Map logging level to our LogLevel enum
            level_map = {
                logging.DEBUG: LogLevel.DEBUG,
                logging.INFO: LogLevel.INFO,
                logging.WARNING: LogLevel.WARNING,
                logging.ERROR: LogLevel.ERROR,
                logging.CRITICAL: LogLevel.CRITICAL,
            }
            level = level_map.get(record.levelno, LogLevel.INFO)
            
            # Extract purchase_id if present in extra
            purchase_id = getattr(record, 'purchase_id', None)
            
            # Extract additional details
            details = {}
            if hasattr(record, 'details'):
                details = record.details
            elif record.exc_info:
                details['exception'] = self.format(record)
            
            log_data = {
                'level': level,
                'message': record.getMessage(),
                'purchase_id': purchase_id,
                'details': details if details else None
            }
            
            # Queue or write immediately
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.db_manager.add_log(**log_data),
                    self._loop
                )
            else:
                # Queue for later
                self._pending_logs.append(log_data)
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Error writing log to database: {e}", file=sys.stderr)


class Logger:
    """
    Centralized logger for the vending machine system.
    
    Provides structured logging with:
    - Console output (for development)
    - File output (rotating logs)
    - Database output (for telemetry)
    """
    
    def __init__(
        self,
        name: str = "monitoni",
        level: str = "INFO",
        console: bool = True,
        file_path: Optional[str] = None,
        max_file_size_mb: int = 10,
        backup_count: int = 5,
        db_manager: Optional[DatabaseManager] = None
    ):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            console: Enable console output
            file_path: Path to log file (None to disable)
            max_file_size_mb: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            db_manager: Database manager for database logging
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        self.logger.handlers.clear()  # Clear any existing handlers
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
        # File handler with rotation
        if file_path:
            file_path = Path(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        # Database handler
        self.db_handler: Optional[DatabaseHandler] = None
        if db_manager:
            self.db_handler = DatabaseHandler(db_manager)
            self.db_handler.setFormatter(formatter)
            self.logger.addHandler(self.db_handler)
            
    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set event loop for async database operations."""
        if self.db_handler:
            self.db_handler.set_event_loop(loop)
            
    def debug(self, message: str, purchase_id: Optional[str] = None, **kwargs) -> None:
        """Log debug message."""
        self.logger.debug(message, extra={'purchase_id': purchase_id, **kwargs})
        
    def info(self, message: str, purchase_id: Optional[str] = None, **kwargs) -> None:
        """Log info message."""
        self.logger.info(message, extra={'purchase_id': purchase_id, **kwargs})
        
    def warning(self, message: str, purchase_id: Optional[str] = None, **kwargs) -> None:
        """Log warning message."""
        self.logger.warning(message, extra={'purchase_id': purchase_id, **kwargs})
        
    def error(self, message: str, purchase_id: Optional[str] = None, **kwargs) -> None:
        """Log error message."""
        self.logger.error(message, extra={'purchase_id': purchase_id, **kwargs})
        
    def critical(self, message: str, purchase_id: Optional[str] = None, **kwargs) -> None:
        """Log critical message."""
        self.logger.critical(message, extra={'purchase_id': purchase_id, **kwargs})
        
    def exception(self, message: str, purchase_id: Optional[str] = None, **kwargs) -> None:
        """Log exception with traceback."""
        self.logger.exception(message, extra={'purchase_id': purchase_id, **kwargs})


# Global logger instance
_logger: Optional[Logger] = None


async def get_logger() -> Logger:
    """
    Get global logger instance.
    
    Returns:
        Logger instance
    """
    global _logger
    if _logger is None:
        from monitoni.core.config import get_config
        from monitoni.core.database import get_database
        
        config = get_config()
        db = await get_database()
        
        _logger = Logger(
            name="monitoni",
            level=config.logging.level,
            console=config.logging.console,
            file_path=config.logging.file_path if config.logging.file else None,
            max_file_size_mb=config.logging.max_file_size_mb,
            backup_count=config.logging.backup_count,
            db_manager=db
        )
        
    return _logger


def get_sync_logger() -> Logger:
    """
    Get logger synchronously (for use before async initialization).
    
    Returns:
        Logger instance without database handler
    """
    global _logger
    if _logger is None:
        from monitoni.core.config import get_config
        config = get_config()
        
        _logger = Logger(
            name="monitoni",
            level=config.logging.level,
            console=config.logging.console,
            file_path=config.logging.file_path if config.logging.file else None,
            max_file_size_mb=config.logging.max_file_size_mb,
            backup_count=config.logging.backup_count,
            db_manager=None  # No database handler yet
        )
        
    return _logger
