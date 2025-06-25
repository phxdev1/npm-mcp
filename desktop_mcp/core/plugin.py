"""
Plugin architecture for Desktop MCP.

Provides base classes and interfaces for creating modular, extensible
desktop automation functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PluginCapability(Enum):
    """Defines the types of capabilities a plugin can provide."""
    MOUSE_CONTROL = "mouse_control"
    KEYBOARD_CONTROL = "keyboard_control"
    WINDOW_MANAGEMENT = "window_management"
    FILE_SYSTEM = "file_system"
    SYSTEM_INFO = "system_info"
    APPLICATION_CONTROL = "application_control"
    SCREENSHOT = "screenshot"
    PROCESS_MANAGEMENT = "process_management"
    WEB_AUTOMATION = "web_automation"


class PluginPriority(Enum):
    """Plugin execution priority levels."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class PluginMetadata:
    """Metadata about a plugin."""
    name: str
    version: str
    description: str
    author: str
    capabilities: List[PluginCapability]
    priority: PluginPriority = PluginPriority.NORMAL
    platform_support: List[str] = None
    dependencies: List[str] = None
    min_python_version: str = "3.8"
    
    def __post_init__(self):
        if self.platform_support is None:
            self.platform_support = ["windows", "linux", "darwin"]
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class PluginPermissions:
    """Defines what a plugin is allowed to do."""
    can_modify_files: bool = False
    can_access_network: bool = False
    can_execute_processes: bool = False
    can_access_clipboard: bool = False
    can_control_input: bool = False
    can_take_screenshots: bool = False
    allowed_directories: List[str] = None
    blocked_applications: List[str] = None
    confirmation_required: bool = True
    
    def __post_init__(self):
        if self.allowed_directories is None:
            self.allowed_directories = []
        if self.blocked_applications is None:
            self.blocked_applications = []


class PluginResult:
    """Result of a plugin operation."""
    
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
        
    @classmethod
    def success(cls, data: Any = None) -> 'PluginResult':
        """Create a successful result."""
        return cls(True, data=data)
        
    @classmethod
    def failure(cls, error: str) -> 'PluginResult':
        """Create a failed result."""
        return cls(False, error=error)


class BasePlugin(ABC):
    """Base class for all Desktop MCP plugins."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._enabled = True
        self._initialized = False
        
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
        
    @property
    @abstractmethod
    def permissions(self) -> PluginPermissions:
        """Return required permissions for this plugin."""
        pass
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass
        
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the plugin is healthy and ready to use."""
        pass
        
    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled
        
    @property
    def initialized(self) -> bool:
        """Check if plugin is initialized."""
        return self._initialized
        
    def enable(self) -> None:
        """Enable the plugin."""
        self._enabled = True
        
    def disable(self) -> None:
        """Disable the plugin."""
        self._enabled = False
        
    async def _safe_initialize(self) -> bool:
        """Safely initialize the plugin with error handling."""
        try:
            if await self.initialize():
                self._initialized = True
                logger.info(f"Plugin {self.metadata.name} initialized successfully")
                return True
            else:
                logger.error(f"Plugin {self.metadata.name} failed to initialize")
                return False
        except Exception as e:
            logger.error(f"Plugin {self.metadata.name} initialization error: {e}")
            return False
            
    async def _safe_cleanup(self) -> None:
        """Safely cleanup the plugin with error handling."""
        try:
            await self.cleanup()
            self._initialized = False
            logger.info(f"Plugin {self.metadata.name} cleaned up successfully")
        except Exception as e:
            logger.error(f"Plugin {self.metadata.name} cleanup error: {e}")


class MCPFunctionPlugin(BasePlugin):
    """Base class for plugins that provide MCP functions."""
    
    @abstractmethod
    def get_mcp_functions(self) -> Dict[str, callable]:
        """Return a dictionary of MCP function name -> callable."""
        pass
        
    @abstractmethod 
    def get_function_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Return MCP function schemas for registration."""
        pass


class EventPlugin(BasePlugin):
    """Base class for plugins that handle system events."""
    
    @abstractmethod
    async def handle_event(self, event_type: str, event_data: Dict[str, Any]) -> PluginResult:
        """Handle a system event."""
        pass
        
    @abstractmethod
    def get_supported_events(self) -> List[str]:
        """Return list of event types this plugin can handle."""
        pass


class MiddlewarePlugin(BasePlugin):
    """Base class for plugins that modify requests/responses."""
    
    @abstractmethod
    async def process_request(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Process and potentially modify a function request."""
        pass
        
    @abstractmethod
    async def process_response(self, function_name: str, result: PluginResult) -> PluginResult:
        """Process and potentially modify a function response."""
        pass