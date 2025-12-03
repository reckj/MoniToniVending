"""
KivyMD application for MoniToni vending machine.

Main application with screen management for customer and debug interfaces.
"""

import asyncio
from typing import Optional
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout

from monitoni.core.config import Config
from monitoni.core.logger import Logger
from monitoni.core.state_machine import PurchaseStateMachine, State, Event
from monitoni.hardware.manager import HardwareManager


class VendingApp(MDApp):
    """
    Main KivyMD application for vending machine.
    
    Manages screens, hardware integration, and purchase flow.
    """
    
    def __init__(
        self,
        config: Config,
        hardware: HardwareManager,
        logger: Logger,
        **kwargs
    ):
        """
        Initialize vending app.
        
        Args:
            config: System configuration
            hardware: Hardware manager
            logger: Logger instance
        """
        super().__init__(**kwargs)
        
        self.config = config
        self.hardware = hardware
        self.logger = logger
        
        # State machine
        self.state_machine = PurchaseStateMachine(
            sleep_timeout=config.vending.timings.sleep_timeout_s,
            purchase_timeout=config.vending.timings.purchase_timeout_s,
            door_alarm_delay=config.vending.timings.door_alarm_delay_s,
            door_unlock_duration=config.vending.door_lock.unlock_duration_s
        )
        
        # Screen manager
        self.screen_manager: Optional[ScreenManager] = None
        
        # Async task for state machine
        self._state_task: Optional[asyncio.Task] = None
        
    def build(self):
        """Build the application UI."""
        # Set theme
        self.theme_cls.theme_style = self.config.ui.theme
        self.theme_cls.primary_palette = self.config.ui.primary_palette
        
        # Configure window
        if self.config.ui.fullscreen:
            Window.fullscreen = 'auto'
        else:
            Window.size = (self.config.ui.screen_width, self.config.ui.screen_height)
            
        # Create screen manager
        self.screen_manager = ScreenManager(transition=FadeTransition())
        
        # Add screens
        from monitoni.ui.customer_screen import CustomerScreen
        from monitoni.ui.debug_screen import DebugScreen
        
        self.screen_manager.add_widget(CustomerScreen(
            name='customer',
            app=self,
            config=self.config,
            hardware=self.hardware,
            state_machine=self.state_machine,
            logger=self.logger
        ))
        
        self.screen_manager.add_widget(DebugScreen(
            name='debug',
            app=self,
            config=self.config,
            hardware=self.hardware,
            logger=self.logger
        ))
        
        # Start on customer screen
        self.screen_manager.current = 'customer'
        
        # Set up state machine callbacks
        self._setup_state_callbacks()
        
        # Set up hardware callbacks
        self._setup_hardware_callbacks()
        
        self.logger.info("UI initialized")
        
        return self.screen_manager
        
    def _setup_state_callbacks(self):
        """Set up state machine callbacks."""
        # Register callbacks for state transitions
        self.state_machine.on_transition(self._on_state_transition)
        
        # Register callbacks for specific states
        self.state_machine.on_state_enter(State.IDLE, self._on_idle)
        self.state_machine.on_state_enter(State.SLEEP, self._on_sleep)
        self.state_machine.on_state_enter(State.DOOR_UNLOCKED, self._on_door_unlocked)
        self.state_machine.on_state_enter(State.DOOR_ALARM, self._on_door_alarm)
        
    def _setup_hardware_callbacks(self):
        """Set up hardware event callbacks."""
        if self.hardware.sensor:
            self.hardware.sensor.set_door_callback(self._on_door_state_changed)
            
    async def _on_state_transition(self, from_state: State, to_state: State, event: Event):
        """Handle state transitions."""
        self.logger.info(
            f"State transition: {from_state.value} -> {to_state.value} (event: {event.value})"
        )
        
    async def _on_idle(self):
        """Handle entering idle state."""
        # Reset LED to idle animation
        if self.hardware.led:
            await self.hardware.led.play_animation('idle')
            
    async def _on_sleep(self):
        """Handle entering sleep state."""
        # Dim LEDs
        if self.hardware.led:
            await self.hardware.led.play_animation('sleep')
            
    async def _on_door_unlocked(self):
        """Handle door unlock."""
        # Play success animation
        if self.hardware.led:
            await self.hardware.led.play_animation('valid_purchase')
        if self.hardware.audio:
            await self.hardware.audio.play_sound('valid_purchase')
            
        # Unlock door for selected level
        level = self.state_machine.selected_level
        if level and self.hardware.relay:
            await self.hardware.unlock_door(level)
            
    async def _on_door_alarm(self):
        """Handle door alarm."""
        # Play alarm
        if self.hardware.led:
            await self.hardware.led.play_animation('door_alarm')
        if self.hardware.audio:
            await self.hardware.audio.play_sound('door_alarm')
            
    async def _on_door_state_changed(self, is_open: bool):
        """
        Handle door sensor state change.
        
        Args:
            is_open: True if door opened, False if closed
        """
        if is_open:
            await self.state_machine.handle_event(Event.DOOR_OPENED)
        else:
            await self.state_machine.handle_event(Event.DOOR_CLOSED)
            
    def switch_to_debug(self):
        """Switch to debug screen."""
        self.screen_manager.current = 'debug'
        
    def switch_to_customer(self):
        """Switch to customer screen."""
        self.screen_manager.current = 'customer'
        
    def on_start(self):
        """Called when application starts."""
        self.logger.info("Application started")
        
    def on_stop(self):
        """Called when application stops."""
        self.logger.info("Application stopping")
        
        # Cancel state machine task
        if self._state_task and not self._state_task.done():
            self._state_task.cancel()
