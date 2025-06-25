"""
Plugin registry and management system for Desktop MCP.

Handles discovery, loading, lifecycle management, and execution of both
Python and NPM-based plugins.
"""

import os
import json
import importlib
import importlib.util
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Union, Set
from dataclasses import dataclass
import logging

from .plugin import (
    BasePlugin, MCPFunctionPlugin, EventPlugin, MiddlewarePlugin,
    PluginMetadata, PluginPermissions, PluginResult, PluginCapability
)
from .npm_plugin_loader import NPMPlugin

logger = logging.getLogger(__name__)


@dataclass
class PluginRegistryConfig:
    """Configuration for the plugin registry."""
    plugin_directories: List[str]
    npm_plugin_directories: List[str]
    auto_discover: bool = True
    load_on_startup: bool = True
    enable_npm_plugins: bool = True
    npm_command: str = "npm"
    node_command: str = "node"
    
    def __post_init__(self):
        # Convert to Path objects and ensure they exist
        self.plugin_directories = [Path(d) for d in self.plugin_directories]
        self.npm_plugin_directories = [Path(d) for d in self.npm_plugin_directories]


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""
    pass


class PluginRegistry:
    """Registry for managing Desktop MCP plugins."""
    
    def __init__(self, config: PluginRegistryConfig):
        self.config = config
        self.plugins: Dict[str, BasePlugin] = {}
        self.mcp_functions: Dict[str, callable] = {}
        self.function_schemas: Dict[str, Dict[str, Any]] = {}
        self.event_handlers: Dict[str, List[EventPlugin]] = {}
        self.middleware_plugins: List[MiddlewarePlugin] = []
        self._initialized = False
        
    async def initialize(self) -> bool:
        """Initialize the plugin registry."""
        try:
            if self.config.auto_discover:
                await self.discover_plugins()
                
            if self.config.load_on_startup:
                await self.load_all_plugins()
                
            self._initialized = True
            logger.info("Plugin registry initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize plugin registry: {e}")
            return False
            
    async def discover_plugins(self) -> None:
        """Discover available plugins in configured directories."""
        logger.info("Discovering plugins...")
        
        # Discover Python plugins
        for plugin_dir in self.config.plugin_directories:
            if plugin_dir.exists():
                await self._discover_python_plugins(plugin_dir)
                
        # Discover NPM plugins
        if self.config.enable_npm_plugins:
            for npm_dir in self.config.npm_plugin_directories:
                if npm_dir.exists():
                    await self._discover_npm_plugins(npm_dir)
                    
    async def _discover_python_plugins(self, plugin_dir: Path) -> None:
        """Discover Python plugins in a directory."""
        for item in plugin_dir.iterdir():
            if item.is_file() and item.suffix == '.py' and not item.name.startswith('_'):
                await self._load_python_plugin_file(item)
            elif item.is_dir() and not item.name.startswith('.'):
                plugin_file = item / '__init__.py'
                if plugin_file.exists():
                    await self._load_python_plugin_file(plugin_file)
                    
    async def _discover_npm_plugins(self, npm_dir: Path) -> None:
        """Discover NPM plugins in a directory."""
        for item in npm_dir.iterdir():
            if item.is_dir():
                package_json = item / 'package.json'
                if package_json.exists():
                    await self._check_npm_plugin(item)
                    
    async def _load_python_plugin_file(self, plugin_file: Path) -> None:
        """Load a Python plugin from a file."""
        try:
            module_name = plugin_file.stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for plugin classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BasePlugin) and 
                    attr != BasePlugin):
                    
                    plugin_instance = attr()
                    await self._register_plugin(plugin_instance)
                    
        except Exception as e:
            logger.error(f"Error loading Python plugin {plugin_file}: {e}")
            
    async def _check_npm_plugin(self, package_dir: Path) -> None:
        """Check if an NPM package is a valid MCP plugin."""
        try:
            with open(package_dir / 'package.json', 'r') as f:
                package_data = json.load(f)
                
            # Check if it has MCP configuration
            if 'mcp' in package_data:
                npm_plugin = NPMPlugin(str(package_dir))
                await self._register_plugin(npm_plugin)
                
        except Exception as e:
            logger.error(f"Error checking NPM plugin {package_dir}: {e}")
            
    async def _register_plugin(self, plugin: BasePlugin) -> None:
        """Register a plugin with the registry."""
        try:
            plugin_name = plugin.metadata.name
            
            if plugin_name in self.plugins:
                logger.warning(f"Plugin {plugin_name} already registered, skipping")
                return
                
            self.plugins[plugin_name] = plugin
            logger.info(f"Registered plugin: {plugin_name}")
            
        except Exception as e:
            logger.error(f"Error registering plugin: {e}")
            
    async def load_plugin(self, plugin_name: str) -> bool:
        """Load and initialize a specific plugin."""
        if plugin_name not in self.plugins:
            logger.error(f"Plugin {plugin_name} not found")
            return False
            
        plugin = self.plugins[plugin_name]
        
        if plugin.initialized:
            logger.info(f"Plugin {plugin_name} already loaded")
            return True
            
        try:
            # Check Node.js availability for NPM plugins
            if isinstance(plugin, NPMPlugin) and not await self._check_node_availability():
                logger.error("Node.js not available, cannot load NPM plugins")
                return False
                
            # Initialize the plugin
            if await plugin._safe_initialize():
                await self._register_plugin_functions(plugin)
                logger.info(f"Loaded plugin: {plugin_name}")
                return True
            else:
                logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {e}")
            return False
            
    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name not in self.plugins:
            return False
            
        plugin = self.plugins[plugin_name]
        
        try:
            await plugin._safe_cleanup()
            self._unregister_plugin_functions(plugin)
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False
            
    async def load_all_plugins(self) -> None:
        """Load all discovered plugins."""
        for plugin_name in self.plugins:
            await self.load_plugin(plugin_name)
            
    async def unload_all_plugins(self) -> None:
        """Unload all plugins."""
        for plugin_name in list(self.plugins.keys()):
            await self.unload_plugin(plugin_name)
            
    async def _register_plugin_functions(self, plugin: BasePlugin) -> None:
        """Register MCP functions from a plugin."""
        if isinstance(plugin, MCPFunctionPlugin):
            functions = plugin.get_mcp_functions()
            schemas = plugin.get_function_schemas()
            
            for func_name, func in functions.items():
                self.mcp_functions[func_name] = func
                if func_name in schemas:
                    self.function_schemas[func_name] = schemas[func_name]
                    
        if isinstance(plugin, EventPlugin):
            for event_type in plugin.get_supported_events():
                if event_type not in self.event_handlers:
                    self.event_handlers[event_type] = []
                self.event_handlers[event_type].append(plugin)
                
        if isinstance(plugin, MiddlewarePlugin):
            self.middleware_plugins.append(plugin)
            
    def _unregister_plugin_functions(self, plugin: BasePlugin) -> None:
        """Unregister MCP functions from a plugin."""
        if isinstance(plugin, MCPFunctionPlugin):
            functions = plugin.get_mcp_functions()
            for func_name in functions:
                self.mcp_functions.pop(func_name, None)
                self.function_schemas.pop(func_name, None)
                
        if isinstance(plugin, EventPlugin):
            for event_type in plugin.get_supported_events():
                if event_type in self.event_handlers:
                    try:
                        self.event_handlers[event_type].remove(plugin)
                    except ValueError:
                        pass
                        
        if isinstance(plugin, MiddlewarePlugin):
            try:
                self.middleware_plugins.remove(plugin)
            except ValueError:
                pass
                
    async def call_function(self, function_name: str, **kwargs) -> Any:
        """Call an MCP function through the plugin system."""
        if function_name not in self.mcp_functions:
            raise ValueError(f"Function {function_name} not found")
            
        # Process through middleware
        processed_kwargs = kwargs
        for middleware in self.middleware_plugins:
            if middleware.enabled and middleware.initialized:
                processed_kwargs = await middleware.process_request(function_name, processed_kwargs)
                
        # Call the function
        try:
            func = self.mcp_functions[function_name]
            result = await func(**processed_kwargs)
            
            # Wrap result
            plugin_result = PluginResult.success(result)
            
        except Exception as e:
            plugin_result = PluginResult.failure(str(e))
            
        # Process response through middleware
        for middleware in reversed(self.middleware_plugins):
            if middleware.enabled and middleware.initialized:
                plugin_result = await middleware.process_response(function_name, plugin_result)
                
        if plugin_result.success:
            return plugin_result.data
        else:
            raise Exception(plugin_result.error)
            
    async def emit_event(self, event_type: str, event_data: Dict[str, Any]) -> List[PluginResult]:
        """Emit an event to all registered handlers."""
        results = []
        
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                if handler.enabled and handler.initialized:
                    try:
                        result = await handler.handle_event(event_type, event_data)
                        results.append(result)
                    except Exception as e:
                        results.append(PluginResult.failure(str(e)))
                        
        return results
        
    def get_plugin_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered plugins."""
        info = {}
        for name, plugin in self.plugins.items():
            info[name] = {
                'metadata': {
                    'name': plugin.metadata.name,
                    'version': plugin.metadata.version,
                    'description': plugin.metadata.description,
                    'author': plugin.metadata.author,
                    'capabilities': [cap.value for cap in plugin.metadata.capabilities],
                },
                'status': {
                    'enabled': plugin.enabled,
                    'initialized': plugin.initialized,
                },
                'type': type(plugin).__name__
            }
        return info
        
    def get_available_functions(self) -> List[str]:
        """Get list of available MCP functions."""
        return list(self.mcp_functions.keys())
        
    def get_function_schema(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific function."""
        return self.function_schemas.get(function_name)
        
    async def _check_node_availability(self) -> bool:
        """Check if Node.js is available."""
        try:
            result = await asyncio.create_subprocess_exec(
                self.config.node_command, '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.wait()
            return result.returncode == 0
        except:
            return False