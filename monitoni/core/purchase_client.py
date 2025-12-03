"""
Purchase server client for validating purchases.

Communicates with external purchase server via REST API.
"""

import asyncio
from typing import Optional, Dict, Any
import httpx
from monitoni.core.logger import Logger


class PurchaseServerClient:
    """
    Client for purchase server communication.
    
    Handles purchase validation and completion notifications.
    """
    
    def __init__(
        self,
        base_url: str,
        check_endpoint: str,
        complete_endpoint: str,
        timeout: float = 5.0,
        retry_attempts: int = 3,
        logger: Optional[Logger] = None
    ):
        """
        Initialize purchase server client.
        
        Args:
            base_url: Base URL of purchase server
            check_endpoint: Endpoint for checking purchases
            complete_endpoint: Endpoint for completing purchases
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts
            logger: Logger instance
        """
        self.base_url = base_url.rstrip('/')
        self.check_endpoint = check_endpoint
        self.complete_endpoint = complete_endpoint
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.logger = logger
        
        self._client: Optional[httpx.AsyncClient] = None
        
    async def connect(self) -> bool:
        """
        Initialize HTTP client.
        
        Returns:
            True if successful
        """
        try:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout
            )
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to initialize purchase client: {e}")
            return False
            
    async def disconnect(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            
    async def check_purchase(self, machine_id: str, level: int) -> Optional[Dict[str, Any]]:
        """
        Check for valid purchase authorization.
        
        Args:
            machine_id: Machine identifier
            level: Product level
            
        Returns:
            Purchase data if valid, None if invalid or error
        """
        if not self._client:
            if self.logger:
                self.logger.error("Purchase client not connected")
            return None
            
        for attempt in range(self.retry_attempts):
            try:
                response = await self._client.post(
                    self.check_endpoint,
                    json={
                        'machine_id': machine_id,
                        'level': level
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get('valid', False):
                        if self.logger:
                            self.logger.info(
                                f"Valid purchase for level {level}",
                                purchase_id=data.get('purchase_id')
                            )
                        return data
                    else:
                        if self.logger:
                            self.logger.warning(f"Invalid purchase for level {level}")
                        return None
                        
                elif response.status_code == 404:
                    # No purchase found
                    return None
                    
                else:
                    if self.logger:
                        self.logger.warning(
                            f"Purchase check failed: HTTP {response.status_code}"
                        )
                        
            except httpx.TimeoutException:
                if self.logger:
                    self.logger.warning(
                        f"Purchase check timeout (attempt {attempt + 1}/{self.retry_attempts})"
                    )
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Purchase check error: {e}")
                    
            # Wait before retry
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                
        return None
        
    async def complete_purchase(
        self,
        purchase_id: str,
        machine_id: str,
        level: int,
        success: bool = True
    ) -> bool:
        """
        Send purchase completion notification.
        
        Args:
            purchase_id: Purchase identifier
            machine_id: Machine identifier
            level: Product level
            success: Whether purchase was successful
            
        Returns:
            True if notification sent successfully
        """
        if not self._client:
            if self.logger:
                self.logger.error("Purchase client not connected")
            return False
            
        for attempt in range(self.retry_attempts):
            try:
                response = await self._client.post(
                    self.complete_endpoint,
                    json={
                        'purchase_id': purchase_id,
                        'machine_id': machine_id,
                        'level': level,
                        'success': success
                    }
                )
                
                if response.status_code == 200:
                    if self.logger:
                        self.logger.info(
                            f"Purchase completion sent",
                            purchase_id=purchase_id
                        )
                    return True
                else:
                    if self.logger:
                        self.logger.warning(
                            f"Purchase completion failed: HTTP {response.status_code}"
                        )
                        
            except httpx.TimeoutException:
                if self.logger:
                    self.logger.warning(
                        f"Purchase completion timeout (attempt {attempt + 1}/{self.retry_attempts})"
                    )
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Purchase completion error: {e}")
                    
            # Wait before retry
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
                
        return False


class MockPurchaseServerClient(PurchaseServerClient):
    """
    Mock purchase server client for testing.
    
    Simulates purchase server responses.
    """
    
    def __init__(self, **kwargs):
        """Initialize mock client."""
        super().__init__(
            base_url="http://mock-server",
            check_endpoint="/check",
            complete_endpoint="/complete",
            **kwargs
        )
        
        # Simulated purchases (level -> valid)
        self._mock_purchases = {}
        
    async def connect(self) -> bool:
        """Mock connection always succeeds."""
        print("[MOCK] Purchase server: Connected")
        return True
        
    async def disconnect(self) -> None:
        """Mock disconnection."""
        print("[MOCK] Purchase server: Disconnected")
        
    async def check_purchase(self, machine_id: str, level: int) -> Optional[Dict[str, Any]]:
        """
        Mock purchase check.
        
        For testing, always returns valid purchase.
        """
        import uuid
        
        # Simulate network delay
        await asyncio.sleep(0.5)
        
        # For mock, always return valid purchase
        purchase_id = str(uuid.uuid4())
        
        print(f"[MOCK] Purchase server: Valid purchase for level {level}")
        
        return {
            'valid': True,
            'purchase_id': purchase_id,
            'level': level,
            'machine_id': machine_id
        }
        
    async def complete_purchase(
        self,
        purchase_id: str,
        machine_id: str,
        level: int,
        success: bool = True
    ) -> bool:
        """Mock purchase completion."""
        # Simulate network delay
        await asyncio.sleep(0.2)
        
        print(f"[MOCK] Purchase server: Completion received for {purchase_id}")
        
        return True
        
    def set_mock_purchase(self, level: int, valid: bool = True):
        """
        Set mock purchase validity for testing.
        
        Args:
            level: Product level
            valid: Whether purchase should be valid
        """
        self._mock_purchases[level] = valid
