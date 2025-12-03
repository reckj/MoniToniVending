"""
State machine for vending machine purchase flow.

Manages the complete purchase lifecycle from idle to completion.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Callable, Dict, Any
import uuid


class State(str, Enum):
    """Purchase flow states."""
    IDLE = "idle"
    SLEEP = "sleep"
    CHECKING_PURCHASE = "checking_purchase"
    DOOR_UNLOCKED = "door_unlocked"
    DOOR_OPENED = "door_opened"
    DOOR_ALARM = "door_alarm"
    COMPLETING = "completing"


class Event(str, Enum):
    """State machine events."""
    # User interactions
    TOUCH_INPUT = "touch_input"
    PURCHASE_SELECTED = "purchase_selected"
    
    # Purchase server responses
    PURCHASE_VALID = "purchase_valid"
    PURCHASE_INVALID = "purchase_invalid"
    
    # Hardware events
    DOOR_OPENED = "door_opened"
    DOOR_CLOSED = "door_closed"
    
    # Timeouts
    TIMEOUT_SLEEP = "timeout_sleep"
    TIMEOUT_PURCHASE = "timeout_purchase"
    TIMEOUT_DOOR_ALARM = "timeout_door_alarm"
    TIMEOUT_DOOR_UNLOCK = "timeout_door_unlock"
    
    # System events
    RESET = "reset"
    COMPLETE = "complete"


class PurchaseStateMachine:
    """
    State machine for managing purchase flow.
    
    States:
    - IDLE: Waiting for user interaction
    - SLEEP: Low power mode with dimmed display
    - CHECKING_PURCHASE: Validating purchase with server
    - DOOR_UNLOCKED: Door unlocked, waiting for customer
    - DOOR_OPENED: Door has been opened, waiting for close
    - DOOR_ALARM: Door left open too long
    - COMPLETING: Sending completion to server
    
    The state machine handles all transitions and timeout management.
    """
    
    def __init__(
        self,
        sleep_timeout: float = 60.0,
        purchase_timeout: float = 120.0,
        door_alarm_delay: float = 10.0,
        door_unlock_duration: float = 30.0
    ):
        """
        Initialize state machine.
        
        Args:
            sleep_timeout: Seconds of inactivity before sleep
            purchase_timeout: Seconds before purchase times out
            door_alarm_delay: Seconds before door alarm triggers
            door_unlock_duration: Seconds before door auto-locks
        """
        self.state = State.IDLE
        self.previous_state: Optional[State] = None
        
        # Timeouts
        self.sleep_timeout = sleep_timeout
        self.purchase_timeout = purchase_timeout
        self.door_alarm_delay = door_alarm_delay
        self.door_unlock_duration = door_unlock_duration
        
        # Current purchase tracking
        self.purchase_id: Optional[str] = None
        self.selected_level: Optional[int] = None
        self.purchase_data: Dict[str, Any] = {}
        
        # Timeout tracking
        self._last_activity: datetime = datetime.now()
        self._timeout_task: Optional[asyncio.Task] = None
        
        # State change callbacks
        self._state_callbacks: Dict[State, list] = {state: [] for state in State}
        self._transition_callbacks: list = []
        
    def on_state_enter(self, state: State, callback: Callable) -> None:
        """
        Register callback for when a state is entered.
        
        Args:
            state: State to watch
            callback: Callback function (can be async)
        """
        self._state_callbacks[state].append(callback)
        
    def on_transition(self, callback: Callable) -> None:
        """
        Register callback for any state transition.
        
        Args:
            callback: Callback function(from_state, to_state, event)
        """
        self._transition_callbacks.append(callback)
        
    async def handle_event(self, event: Event, **kwargs) -> bool:
        """
        Handle an event and potentially transition state.
        
        Args:
            event: Event to handle
            **kwargs: Additional event data
            
        Returns:
            True if state changed, False otherwise
        """
        old_state = self.state
        new_state = await self._get_next_state(event, **kwargs)
        
        if new_state and new_state != old_state:
            await self._transition_to(new_state, event)
            return True
            
        # Update activity timestamp for relevant events
        if event in [Event.TOUCH_INPUT, Event.PURCHASE_SELECTED]:
            self._last_activity = datetime.now()
            
        return False
        
    async def _get_next_state(self, event: Event, **kwargs) -> Optional[State]:
        """
        Determine next state based on current state and event.
        
        Args:
            event: Event that occurred
            **kwargs: Event data
            
        Returns:
            Next state or None if no transition
        """
        # Reset always goes to IDLE
        if event == Event.RESET:
            return State.IDLE
            
        # State-specific transitions
        if self.state == State.IDLE:
            if event == Event.TIMEOUT_SLEEP:
                return State.SLEEP
            elif event == Event.PURCHASE_SELECTED:
                return State.CHECKING_PURCHASE
                
        elif self.state == State.SLEEP:
            if event == Event.TOUCH_INPUT:
                return State.IDLE
                
        elif self.state == State.CHECKING_PURCHASE:
            if event == Event.PURCHASE_VALID:
                return State.DOOR_UNLOCKED
            elif event == Event.PURCHASE_INVALID:
                return State.IDLE
            elif event == Event.TIMEOUT_PURCHASE:
                return State.IDLE
                
        elif self.state == State.DOOR_UNLOCKED:
            if event == Event.DOOR_OPENED:
                return State.DOOR_OPENED
            elif event == Event.TIMEOUT_DOOR_UNLOCK:
                return State.IDLE  # Auto-lock timeout
                
        elif self.state == State.DOOR_OPENED:
            if event == Event.DOOR_CLOSED:
                return State.COMPLETING
            elif event == Event.TIMEOUT_DOOR_ALARM:
                return State.DOOR_ALARM
                
        elif self.state == State.DOOR_ALARM:
            if event == Event.DOOR_CLOSED:
                return State.COMPLETING
                
        elif self.state == State.COMPLETING:
            if event == Event.COMPLETE:
                return State.IDLE
                
        return None
        
    async def _transition_to(self, new_state: State, event: Event) -> None:
        """
        Transition to a new state.
        
        Args:
            new_state: State to transition to
            event: Event that caused transition
        """
        old_state = self.state
        self.previous_state = old_state
        self.state = new_state
        
        # Cancel any pending timeout
        if self._timeout_task and not self._timeout_task.done():
            self._timeout_task.cancel()
            
        # Start new timeout if needed
        if new_state == State.IDLE:
            self._timeout_task = asyncio.create_task(
                self._schedule_timeout(self.sleep_timeout, Event.TIMEOUT_SLEEP)
            )
        elif new_state == State.CHECKING_PURCHASE:
            self._timeout_task = asyncio.create_task(
                self._schedule_timeout(self.purchase_timeout, Event.TIMEOUT_PURCHASE)
            )
        elif new_state == State.DOOR_UNLOCKED:
            self._timeout_task = asyncio.create_task(
                self._schedule_timeout(self.door_unlock_duration, Event.TIMEOUT_DOOR_UNLOCK)
            )
        elif new_state == State.DOOR_OPENED:
            self._timeout_task = asyncio.create_task(
                self._schedule_timeout(self.door_alarm_delay, Event.TIMEOUT_DOOR_ALARM)
            )
            
        # Call transition callbacks
        for callback in self._transition_callbacks:
            if asyncio.iscoroutinefunction(callback):
                await callback(old_state, new_state, event)
            else:
                callback(old_state, new_state, event)
                
        # Call state entry callbacks
        for callback in self._state_callbacks[new_state]:
            if asyncio.iscoroutinefunction(callback):
                await callback()
            else:
                callback()
                
    async def _schedule_timeout(self, delay: float, event: Event) -> None:
        """
        Schedule a timeout event.
        
        Args:
            delay: Delay in seconds
            event: Event to trigger on timeout
        """
        try:
            await asyncio.sleep(delay)
            await self.handle_event(event)
        except asyncio.CancelledError:
            pass  # Timeout was cancelled
            
    def start_purchase(self, level: int, purchase_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new purchase.
        
        Args:
            level: Product level (1-10)
            purchase_data: Additional purchase data
            
        Returns:
            Purchase ID
        """
        self.purchase_id = str(uuid.uuid4())
        self.selected_level = level
        self.purchase_data = purchase_data or {}
        return self.purchase_id
        
    def clear_purchase(self) -> None:
        """Clear current purchase data."""
        self.purchase_id = None
        self.selected_level = None
        self.purchase_data = {}
        
    def get_purchase_info(self) -> Dict[str, Any]:
        """
        Get current purchase information.
        
        Returns:
            Dictionary with purchase info
        """
        return {
            'purchase_id': self.purchase_id,
            'level': self.selected_level,
            'state': self.state.value,
            'data': self.purchase_data
        }
        
    def is_idle(self) -> bool:
        """Check if state machine is idle."""
        return self.state in [State.IDLE, State.SLEEP]
        
    def is_active_purchase(self) -> bool:
        """Check if there's an active purchase."""
        return self.state in [
            State.CHECKING_PURCHASE,
            State.DOOR_UNLOCKED,
            State.DOOR_OPENED,
            State.DOOR_ALARM,
            State.COMPLETING
        ]
