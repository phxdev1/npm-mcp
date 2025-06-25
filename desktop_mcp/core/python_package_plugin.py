"""
Python package plugin that uses JSON adapters for existing Python packages.

Wraps existing Python packages like elevenlabs, sqlite3, requests, etc.
using JSON adapter configurations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from .plugin import BasePlugin, PluginMetadata, PluginCapability, PluginPriority
from .python_adapter import PythonPackageAdapter

logger = logging.getLogger(__name__)


class PythonPackagePlugin(BasePlugin):
    """Plugin that wraps an existing Python package using JSON adapter."""
    
    def __init__(self, package_name: str, adapter_config: Dict[str, Any]):
        self.package_name = package_name
        self.adapter_config = adapter_config
        # Use import_name for the actual Python import
        import_name = adapter_config.get('import_name', package_name)
        self.python_adapter = PythonPackageAdapter(import_name)
        self._initialized = False
        self._functions: Dict[str, callable] = {}
        
    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        capabilities = []
        for cap_str in self.adapter_config.get('capabilities', []):
            try:
                capabilities.append(PluginCapability(cap_str))
            except ValueError:
                # Skip invalid capabilities
                pass
                
        return PluginMetadata(
            name=f"python-{self.package_name}",
            version="1.0.0",
            description=self.adapter_config.get('description', f"Python adapter for {self.package_name}"),
            author="Auto-adapted Python package",
            capabilities=capabilities,
            priority=PluginPriority.NORMAL
        )
        
    async def initialize(self) -> bool:
        """Initialize the Python package adapter."""
        try:
            # Store the adapter config for the python adapter
            self.python_adapter.config = self.adapter_config
            
            # Initialize the adapter
            success = await self.python_adapter.initialize()
            
            if success:
                # Create wrapper functions for all methods
                methods = self.adapter_config.get('methods', {})
                for method_name, method_config in methods.items():
                    self._functions[method_name] = self._create_function_wrapper(method_name, method_config)
                
                self._initialized = True
                logger.info(f"Successfully initialized Python package: {self.package_name}")
                return True
            else:
                logger.error(f"Failed to setup Python adapter for {self.package_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Python package {self.package_name}: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up the Python package adapter."""
        if self.python_adapter:
            await self.python_adapter.cleanup()
        self._initialized = False
        self._functions.clear()
        
    def get_mcp_functions(self) -> Dict[str, callable]:
        """Return MCP functions for this Python package."""
        return self._functions.copy()
        
    def _create_function_wrapper(self, method_name: str, method_config: Dict[str, Any]) -> callable:
        """Create a wrapper function for a Python package method."""
        
        # Extract parameter info for better documentation
        parameters = method_config.get('parameters', [])
        description = method_config.get('description', f"{method_name} from {self.package_name}")
        
        async def wrapper(**kwargs):
            """Dynamically created wrapper function."""
            try:
                # Use the python adapter's execute_function method
                result = await self.python_adapter.execute_function(method_name, **kwargs)
                return result
            except Exception as e:
                logger.error(f"Error executing {self.package_name}.{method_name}: {e}")
                raise
                
        # Add documentation to the wrapper
        wrapper.__name__ = f"{self.package_name}_{method_name}"
        wrapper.__doc__ = f"{description}\n\nParameters: {', '.join(parameters)}"
        
        return wrapper
        
    @property
    def initialized(self) -> bool:
        return self._initialized
        
    @property
    def enabled(self) -> bool:
        return True
        
    async def health_check(self) -> bool:
        """Check if the plugin is healthy."""
        return self._initialized
        
    @property 
    def permissions(self) -> List[str]:
        """Return required permissions."""
        return []


class PythonPackageDiscovery:
    """Discovers available Python packages with JSON adapters."""
    
    def __init__(self, json_adapter_loader):
        self.json_adapter_loader = json_adapter_loader
        
    def discover_python_packages(self) -> List[Dict[str, Any]]:
        """Discover all Python packages that have JSON adapters."""
        discovered = []
        
        for package_name, adapter_config in self.json_adapter_loader.adapters.items():
            # Check if this is a Python package adapter
            if adapter_config.get('import_type') == 'python':
                available = False
                import_name = adapter_config.get('import_name', package_name)
                try:
                    # Try to import the package to see if it's available
                    __import__(import_name)
                    available = True
                    logger.info(f"Discovered available Python package: {package_name} (import: {import_name})")
                    
                except (ImportError, Exception) as e:
                    # Package not installed or import error
                    logger.debug(f"Python package not available: {package_name} (import: {import_name}) - {str(e)[:100]}")
                    
                package_info = {
                    'type': 'python_adapter',
                    'name': package_name,
                    'description': adapter_config.get('description', ''),
                    'capabilities': adapter_config.get('capabilities', []),
                    'adapter_config': adapter_config,
                    'available': available
                }
                discovered.append(package_info)
                    
        return discovered
        
    def create_plugin(self, package_info: Dict[str, Any]) -> Optional[PythonPackagePlugin]:
        """Create a plugin instance for a discovered Python package."""
        if not package_info.get('available', False):
            return None
            
        try:
            return PythonPackagePlugin(
                package_info['name'],
                package_info['adapter_config']
            )
        except Exception as e:
            logger.error(f"Error creating Python package plugin for {package_info['name']}: {e}")
            return None