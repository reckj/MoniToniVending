"""
Purchase flow integration for customer screen.

Handles purchase validation and completion with external server.
"""

import asyncio
from typing import Optional
from monitoni.core.state_machine import PurchaseStateMachine, State, Event
from monitoni.core.purchase_client import PurchaseServerClient
from monitoni.core.logger import Logger
from monitoni.hardware.manager import HardwareManager


class PurchaseFlowManager:
    """
    Manages purchase flow integration.
    
    Coordinates state machine, purchase server, and hardware.
    """
    
    def __init__(
        self,
        state_machine: PurchaseStateMachine,
        purchase_client: PurchaseServerClient,
        hardware: HardwareManager,
        logger: Logger,
        machine_id: str,
        poll_interval: float = 0.5
    ):
        """
        Initialize purchase flow manager.
        
        Args:
            state_machine: Purchase state machine
            purchase_client: Purchase server client
            hardware: Hardware manager
            logger: Logger instance
            machine_id: Machine identifier
            poll_interval: Purchase polling interval in seconds
        """
        self.state_machine = state_machine
        self.purchase_client = purchase_client
        self.hardware = hardware
        self.logger = logger
        self.machine_id = machine_id
        self.poll_interval = poll_interval
        
        self._poll_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self):
        """Start purchase flow manager."""
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        self.logger.info("Purchase flow manager started")
        
    async def stop(self):
        """Stop purchase flow manager."""
        self._running = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        self.logger.info("Purchase flow manager stopped")
        
    async def _poll_loop(self):
        """Poll purchase server for valid purchases."""
        try:
            while self._running:
                # Only poll when in CHECKING_PURCHASE state
                if self.state_machine.state == State.CHECKING_PURCHASE:
                    await self._check_purchase()
                    
                await asyncio.sleep(self.poll_interval)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.exception(f"Purchase poll loop error: {e}")
            
    async def _check_purchase(self):
        """Check for valid purchase."""
        level = self.state_machine.selected_level
        if not level:
            return
            
        purchase_id = self.state_machine.purchase_id
        
        # Check with purchase server
        result = await self.purchase_client.check_purchase(
            machine_id=self.machine_id,
            level=level
        )
        
        if result and result.get('valid'):
            # Valid purchase
            self.logger.info(
                f"Valid purchase confirmed for level {level}",
                purchase_id=purchase_id
            )
            
            # Update purchase data
            self.state_machine.purchase_data = result
            
            # Trigger state transition
            await self.state_machine.handle_event(Event.PURCHASE_VALID)
            
        # Note: We don't trigger PURCHASE_INVALID here
        # The state machine timeout will handle invalid/timeout cases
        
    async def complete_purchase(self, success: bool = True):
        """
        Complete purchase and notify server.
        
        Args:
            success: Whether purchase was successful
        """
        purchase_id = self.state_machine.purchase_id
        level = self.state_machine.selected_level
        
        if not purchase_id or not level:
            return
            
        # Send completion to server
        await self.purchase_client.complete_purchase(
            purchase_id=purchase_id,
            machine_id=self.machine_id,
            level=level,
            success=success
        )
        
        # Update statistics
        from monitoni.core.database import get_database
        db = await get_database()
        
        if success:
            await db.increment_statistic('completed_purchases')
            self.logger.info(
                "Purchase completed successfully",
                purchase_id=purchase_id
            )
        else:
            await db.increment_statistic('failed_purchases')
            self.logger.warning(
                "Purchase failed",
                purchase_id=purchase_id
            )
            
        # Clear purchase data
        self.state_machine.clear_purchase()
        
        # Return to idle
        await self.state_machine.handle_event(Event.COMPLETE)
