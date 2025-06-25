"""
NPM-based plugin system for Desktop MCP.

Allows loading and executing Node.js/NPM packages as plugins through
subprocess communication and JSON-RPC interface.
"""

import json
import asyncio
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import logging

from .plugin import BasePlugin, PluginMetadata, PluginPermissions, PluginResult, PluginCapability

logger = logging.getLogger(__name__)


@dataclass
class NPMPackageInfo:
    """Information about an NPM package."""
    name: str
    version: str
    description: str
    main: str
    keywords: List[str] = None
    dependencies: Dict[str, str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.dependencies is None:
            self.dependencies = {}


class NPMPluginBridge:
    """Bridge for communicating with Node.js plugin processes."""
    
    def __init__(self, plugin_path: str, plugin_name: str):
        self.plugin_path = plugin_path
        self.plugin_name = plugin_name
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        
    async def start(self) -> bool:
        """Start the Node.js plugin process."""
        try:
            # Create a bridge script that handles JSON-RPC communication
            bridge_script = self._create_bridge_script()
            
            self.process = await asyncio.create_subprocess_exec(
                'node', bridge_script, self.plugin_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a moment for the process to start
            await asyncio.sleep(0.1)
            
            if self.process.returncode is not None:
                logger.error(f"Plugin process {self.plugin_name} failed to start")
                return False
                
            logger.info(f"Started NPM plugin bridge for {self.plugin_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start NPM plugin {self.plugin_name}: {e}")
            return False
            
    async def stop(self) -> None:
        """Stop the Node.js plugin process."""
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except Exception as e:
                logger.error(f"Error stopping plugin process {self.plugin_name}: {e}")
            finally:
                self.process = None
                
    async def call_function(self, function_name: str, **kwargs) -> PluginResult:
        """Call a function in the Node.js plugin."""
        if not self.process:
            return PluginResult.failure("Plugin process not running")
            
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "method": function_name,
            "params": kwargs,
            "id": self._request_id
        }
        
        try:
            # Send request
            request_data = json.dumps(request) + '\n'
            self.process.stdin.write(request_data.encode())
            await self.process.stdin.drain()
            
            # Read response
            response_line = await self.process.stdout.readline()
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                return PluginResult.failure(response["error"]["message"])
            else:
                return PluginResult.success(response.get("result"))
                
        except Exception as e:
            logger.error(f"Error calling {function_name} on {self.plugin_name}: {e}")
            return PluginResult.failure(str(e))
            
    def _create_bridge_script(self) -> str:
        """Create a Node.js bridge script for JSON-RPC communication."""
        bridge_content = '''
const readline = require('readline');
const path = require('path');

// Get the plugin path from command line arguments
const pluginPath = process.argv[2];
if (!pluginPath) {
    console.error('Plugin path not provided');
    process.exit(1);
}

// Load the plugin
let plugin;
try {
    plugin = require(path.resolve(pluginPath));
} catch (error) {
    console.error('Failed to load plugin:', error.message);
    process.exit(1);
}

// Setup readline interface for JSON-RPC communication
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Handle incoming JSON-RPC requests
rl.on('line', async (line) => {
    try {
        const request = JSON.parse(line);
        const { method, params, id } = request;
        
        if (!plugin[method]) {
            const response = {
                jsonrpc: "2.0",
                error: { code: -32601, message: `Method ${method} not found` },
                id
            };
            console.log(JSON.stringify(response));
            return;
        }
        
        // Call the plugin method
        let result;
        if (typeof plugin[method] === 'function') {
            result = await plugin[method](params || {});
        } else {
            result = plugin[method];
        }
        
        const response = {
            jsonrpc: "2.0",
            result,
            id
        };
        console.log(JSON.stringify(response));
        
    } catch (error) {
        const response = {
            jsonrpc: "2.0",
            error: { code: -32603, message: error.message },
            id: request?.id || null
        };
        console.log(JSON.stringify(response));
    }
});

// Handle process termination
process.on('SIGTERM', () => {
    if (plugin.cleanup && typeof plugin.cleanup === 'function') {
        plugin.cleanup();
    }
    process.exit(0);
});
'''
        
        # Write bridge script to temporary file
        bridge_file = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False)
        bridge_file.write(bridge_content)
        bridge_file.close()
        
        return bridge_file.name


class NPMPlugin(BasePlugin):
    """Plugin that wraps an NPM package."""
    
    def __init__(self, package_path: str, config: Dict[str, Any] = None):
        super().__init__(config)
        self.package_path = Path(package_path)
        self.package_info: Optional[NPMPackageInfo] = None
        self.bridge: Optional[NPMPluginBridge] = None
        self._metadata: Optional[PluginMetadata] = None
        self._permissions: Optional[PluginPermissions] = None
        self._mcp_functions: Dict[str, callable] = {}
        
    @property
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata from package.json."""
        if self._metadata is None:
            self._load_package_info()
        return self._metadata
        
    @property
    def permissions(self) -> PluginPermissions:
        """Return plugin permissions."""
        if self._permissions is None:
            self._load_permissions()
        return self._permissions
        
    async def initialize(self) -> bool:
        """Initialize the NPM plugin."""
        try:
            # Load package information
            if not self._load_package_info():
                return False
                
            # Create and start the bridge
            self.bridge = NPMPluginBridge(
                str(self.package_path), 
                self.package_info.name
            )
            
            if not await self.bridge.start():
                return False
                
            # Initialize the plugin
            result = await self.bridge.call_function('initialize', config=self.config)
            if not result.success:
                logger.error(f"NPM plugin {self.package_info.name} initialization failed: {result.error}")
                return False
                
            # Load MCP functions
            await self._load_mcp_functions()
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing NPM plugin: {e}")
            return False
            
    async def cleanup(self) -> None:
        """Clean up the NPM plugin."""
        if self.bridge:
            await self.bridge.call_function('cleanup')
            await self.bridge.stop()
            
    async def health_check(self) -> bool:
        """Check if the NPM plugin is healthy."""
        if not self.bridge:
            return False
            
        result = await self.bridge.call_function('health_check')
        return result.success and result.data
        
    def _load_package_info(self) -> bool:
        """Load package.json information."""
        package_json_path = self.package_path / 'package.json'
        
        if not package_json_path.exists():
            logger.error(f"package.json not found in {self.package_path}")
            return False
            
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                
            self.package_info = NPMPackageInfo(
                name=package_data.get('name', 'unknown'),
                version=package_data.get('version', '0.0.0'),
                description=package_data.get('description', ''),
                main=package_data.get('main', 'index.js'),
                keywords=package_data.get('keywords', []),
                dependencies=package_data.get('dependencies', {})
            )
            
            # Extract MCP metadata from package.json
            mcp_config = package_data.get('mcp', {})
            capabilities = []
            
            for cap_str in mcp_config.get('capabilities', []):
                try:
                    capabilities.append(PluginCapability(cap_str))
                except ValueError:
                    logger.warning(f"Unknown capability: {cap_str}")
                    
            self._metadata = PluginMetadata(
                name=self.package_info.name,
                version=self.package_info.version,
                description=self.package_info.description,
                author=package_data.get('author', 'Unknown'),
                capabilities=capabilities,
                platform_support=mcp_config.get('platforms', ['windows', 'linux', 'darwin']),
                dependencies=list(self.package_info.dependencies.keys())
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading package.json: {e}")
            return False
            
    def _load_permissions(self) -> None:
        """Load plugin permissions from package.json."""
        if not self.package_info:
            self._permissions = PluginPermissions()
            return
            
        # Load permissions from package.json mcp config
        package_json_path = self.package_path / 'package.json'
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                
            mcp_config = package_data.get('mcp', {})
            perms_config = mcp_config.get('permissions', {})
            
            self._permissions = PluginPermissions(
                can_modify_files=perms_config.get('can_modify_files', False),
                can_access_network=perms_config.get('can_access_network', False),
                can_execute_processes=perms_config.get('can_execute_processes', False),
                can_access_clipboard=perms_config.get('can_access_clipboard', False),
                can_control_input=perms_config.get('can_control_input', False),
                can_take_screenshots=perms_config.get('can_take_screenshots', False),
                allowed_directories=perms_config.get('allowed_directories', []),
                blocked_applications=perms_config.get('blocked_applications', []),
                confirmation_required=perms_config.get('confirmation_required', True)
            )
            
        except Exception as e:
            logger.error(f"Error loading permissions: {e}")
            self._permissions = PluginPermissions()
            
    async def _load_mcp_functions(self) -> None:
        """Load MCP functions from the NPM plugin."""
        try:
            result = await self.bridge.call_function('get_mcp_functions')
            if result.success and result.data:
                function_names = result.data
                
                # Create wrapper functions for each MCP function
                for func_name in function_names:
                    self._mcp_functions[func_name] = self._create_function_wrapper(func_name)
                    
        except Exception as e:
            logger.error(f"Error loading MCP functions: {e}")
            
    def _create_function_wrapper(self, function_name: str) -> callable:
        """Create a wrapper function for an NPM plugin function."""
        async def wrapper(**kwargs):
            result = await self.bridge.call_function(function_name, **kwargs)
            if result.success:
                return result.data
            else:
                raise Exception(result.error)
        return wrapper
        
    def get_mcp_functions(self) -> Dict[str, callable]:
        """Return MCP functions provided by this plugin."""
        return self._mcp_functions