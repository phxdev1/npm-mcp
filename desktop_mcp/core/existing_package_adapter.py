"""
Adapter system for using existing NPM packages as Desktop MCP plugins.

Automatically wraps popular automation packages like robotjs, puppeteer, 
fs-extra, etc. without requiring custom MCP-specific versions.
"""

import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .npm_plugin_loader import NPMPluginBridge
from .json_adapter_loader import JSONAdapterLoader

logger = logging.getLogger(__name__)

# Global adapter loader instance
_adapter_loader = JSONAdapterLoader()


class PackageAdapter:
    """Adapts existing NPM packages to work as MCP plugins."""
    
    def __init__(self, package_name: str, adapter_config: Dict[str, Any]):
        self.package_name = package_name
        self.adapter_config = adapter_config
        self.bridge: Optional[NPMPluginBridge] = None
        
    async def create_bridge_script(self) -> str:
        """Create a bridge script that adapts the existing package."""
        bridge_content = f'''
const {self.adapter_config['import_name']} = require('{self.package_name}');
const readline = require('readline');

// Setup readline for JSON-RPC communication
const rl = readline.createInterface({{
    input: process.stdin,
    output: process.stdout
}});

// Handle incoming requests
rl.on('line', async (line) => {{
    try {{
        const request = JSON.parse(line);
        const {{ method, params, id }} = request;
        
        let result;
        
        {self._generate_method_handlers()}
        
        const response = {{
            jsonrpc: "2.0",
            result,
            id
        }};
        console.log(JSON.stringify(response));
        
    }} catch (error) {{
        const response = {{
            jsonrpc: "2.0",
            error: {{ code: -32603, message: error.message }},
            id: request?.id || null
        }};
        console.log(JSON.stringify(response));
    }}
}});
'''
        return bridge_content
        
    def _generate_method_handlers(self) -> str:
        """Generate JavaScript method handlers for the adapted package."""
        handlers = []
        
        for method_name, method_config in self.adapter_config['methods'].items():
            if method_config['type'] == 'direct':
                handlers.append(f'''
        if (method === '{method_name}') {{
            result = await {method_config['call']};
        }}''')
            elif method_config['type'] == 'transform':
                handlers.append(f'''
        if (method === '{method_name}') {{
            {method_config['transform']}
            result = await {method_config['call']};
        }}''')
                
        return '\n        '.join(handlers)


# Legacy function - now uses JSON adapters
def get_package_adapters():
    """Get available package adapters from JSON configurations."""
    return _adapter_loader.list_supported_packages()


class ExistingPackagePlugin:
    """Plugin that wraps an existing NPM package."""
    
    def __init__(self, package_name: str, package_path: str):
        self.package_name = package_name
        self.package_path = package_path
        self.adapter_config = _adapter_loader.get_adapter(package_name)
        self.bridge: Optional[NPMPluginBridge] = None
        self._initialized = False
        
    @property
    def metadata(self):
        """Return plugin metadata."""
        from .plugin import PluginMetadata, PluginCapability, PluginPriority
        
        if not self.adapter_config:
            return None
            
        capabilities = []
        for cap_str in self.adapter_config.get('capabilities', []):
            try:
                capabilities.append(PluginCapability(cap_str))
            except ValueError:
                pass
                
        return PluginMetadata(
            name=f"existing-{self.package_name}",
            version="1.0.0",
            description=self.adapter_config['description'],
            author="Auto-adapted from existing package",
            capabilities=capabilities,
            priority=PluginPriority.NORMAL
        )
        
    async def initialize(self) -> bool:
        """Initialize the adapted package."""
        if not self.adapter_config:
            logger.error(f"No adapter available for package {self.package_name}")
            return False
            
        try:
            # Create bridge script using JSON adapter
            bridge_script_path = _adapter_loader.create_bridge_script(self.package_name)
            
            if not bridge_script_path:
                logger.error(f"Failed to create bridge script for {self.package_name}")
                return False
            
            # Create bridge and start
            self.bridge = NPMPluginBridge(bridge_script_path, f"adapted-{self.package_name}")
            
            if await self.bridge.start():
                self._initialized = True
                logger.info(f"Successfully adapted existing package: {self.package_name}")
                return True
            else:
                logger.error(f"Failed to start bridge for {self.package_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing adapted package {self.package_name}: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up the adapted package."""
        if self.bridge:
            await self.bridge.stop()
            self._initialized = False
            
    def get_mcp_functions(self) -> Dict[str, callable]:
        """Return MCP functions for this adapted package."""
        if not self.adapter_config or not self.bridge:
            return {}
            
        functions = {}
        methods = self.adapter_config.get('methods', {})
        for method_name in methods:
            functions[method_name] = self._create_function_wrapper(method_name)
            
        return functions
        
    def _create_function_wrapper(self, method_name: str) -> callable:
        """Create a wrapper function for an adapted method."""
        async def wrapper(**kwargs):
            result = await self.bridge.call_function(method_name, **kwargs)
            if result.success:
                return result.data
            else:
                raise Exception(result.error)
        return wrapper
        
    @property
    def initialized(self) -> bool:
        return self._initialized
        
    @property
    def enabled(self) -> bool:
        return True