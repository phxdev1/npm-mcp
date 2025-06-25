"""
Zero-configuration plugin discovery for Desktop MCP.

Automatically discovers and loads plugins from:
- Global NPM packages with 'desktop-mcp-' prefix
- Local node_modules with MCP configuration
- Python packages with MCP entry points
"""

import os
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class AutoDiscovery:
    """Automatic plugin discovery with zero configuration."""
    
    def __init__(self):
        self.discovered_plugins: List[Dict] = []
        
    async def discover_all_plugins(self) -> List[Dict]:
        """Discover all available plugins automatically."""
        self.discovered_plugins = []
        
        # Discover NPM plugins
        await self._discover_global_npm_plugins()
        await self._discover_local_npm_plugins()
        
        # Discover Python plugins
        await self._discover_python_entry_points()
        await self._discover_python_packages()
        
        logger.info(f"Auto-discovered {len(self.discovered_plugins)} plugins")
        return self.discovered_plugins
        
    async def _discover_global_npm_plugins(self) -> None:
        """Discover globally installed NPM plugins."""
        try:
            # Get global npm root
            result = await asyncio.create_subprocess_exec(
                'npm', 'root', '-g',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                global_modules = Path(stdout.decode().strip())
                await self._scan_npm_directory(global_modules, "global")
                
        except Exception as e:
            logger.debug(f"Could not discover global NPM plugins: {e}")
            
    async def _discover_local_npm_plugins(self) -> None:
        """Discover locally installed NPM plugins."""
        try:
            # Check for local node_modules
            local_modules = Path.cwd() / 'node_modules'
            if local_modules.exists():
                await self._scan_npm_directory(local_modules, "local")
                
        except Exception as e:
            logger.debug(f"Could not discover local NPM plugins: {e}")
            
    async def _scan_npm_directory(self, modules_dir: Path, source: str) -> None:
        """Scan an NPM modules directory for both MCP plugins and adaptable packages."""
        if not modules_dir.exists():
            return
            
        from .existing_package_adapter import _adapter_loader
            
        for package_dir in modules_dir.iterdir():
            if not package_dir.is_dir():
                continue
                
            package_name = package_dir.name
            package_json = package_dir / 'package.json'
            
            if not package_json.exists():
                continue
                
            # Check for desktop-mcp- prefix or MCP configuration
            if (package_name.startswith('desktop-mcp-') or 
                package_name.startswith('@') and self._check_scoped_package(package_dir)):
                
                plugin_info = await self._analyze_npm_package(package_dir, source)
                if plugin_info:
                    self.discovered_plugins.append(plugin_info)
                    
            # Check if this is an adaptable existing package
            elif _adapter_loader.has_adapter(package_name):
                adapter_config = _adapter_loader.get_adapter(package_name)
                plugin_info = {
                    'type': 'existing_npm',
                    'name': package_name,
                    'path': str(package_dir),
                    'source': source,
                    'adapter_available': True,
                    'description': adapter_config.get('description', ''),
                    'capabilities': adapter_config.get('capabilities', [])
                }
                self.discovered_plugins.append(plugin_info)
                logger.info(f"Found adaptable package: {package_name}")
                        
    def _check_scoped_package(self, scoped_dir: Path) -> bool:
        """Check if a scoped package contains MCP plugins."""
        for package_dir in scoped_dir.iterdir():
            if package_dir.is_dir() and package_dir.name.startswith('desktop-mcp-'):
                return True
        return False
        
    async def _analyze_npm_package(self, package_dir: Path, source: str) -> Optional[Dict]:
        """Analyze an NPM package to see if it's a valid MCP plugin."""
        try:
            package_json_path = package_dir / 'package.json'
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
                
            # Check for MCP configuration
            mcp_config = package_data.get('mcp', {})
            
            # Auto-detect MCP plugins by keywords or name prefix
            keywords = package_data.get('keywords', [])
            is_mcp_plugin = (
                'mcp' in keywords or
                'desktop-mcp' in keywords or
                package_data.get('name', '').startswith('desktop-mcp-') or
                bool(mcp_config)
            )
            
            if is_mcp_plugin:
                return {
                    'type': 'npm',
                    'name': package_data.get('name'),
                    'version': package_data.get('version'),
                    'description': package_data.get('description', ''),
                    'path': str(package_dir),
                    'source': source,
                    'main': package_data.get('main', 'index.js'),
                    'mcp_config': mcp_config,
                    'auto_detected': not bool(mcp_config)  # True if detected by naming convention
                }
                
        except Exception as e:
            logger.debug(f"Error analyzing NPM package {package_dir}: {e}")
            
        return None
        
    async def _discover_python_entry_points(self) -> None:
        """Discover Python plugins via entry points."""
        try:
            import pkg_resources
            
            # Look for desktop_mcp_plugins entry point
            for entry_point in pkg_resources.iter_entry_points('desktop_mcp_plugins'):
                try:
                    plugin_class = entry_point.load()
                    plugin_info = {
                        'type': 'python',
                        'name': entry_point.name,
                        'module': entry_point.module_name,
                        'class': plugin_class.__name__,
                        'source': 'entry_point',
                        'distribution': entry_point.dist.project_name,
                        'version': entry_point.dist.version
                    }
                    self.discovered_plugins.append(plugin_info)
                    
                except Exception as e:
                    logger.debug(f"Error loading entry point {entry_point}: {e}")
                    
        except ImportError:
            logger.debug("pkg_resources not available, skipping entry point discovery")
            
    async def _discover_python_packages(self) -> None:
        """Discover Python packages with JSON adapters."""
        try:
            from .json_adapter_loader import JSONAdapterLoader
            from .python_package_plugin import PythonPackageDiscovery
            
            # Load JSON adapters
            adapter_loader = JSONAdapterLoader()
            discovery = PythonPackageDiscovery(adapter_loader)
            
            # Discover available Python packages
            python_packages = discovery.discover_python_packages()
            
            for package_info in python_packages:
                if package_info.get('available', False):
                    plugin_info = {
                        'type': 'python_package',
                        'name': package_info['name'],
                        'description': package_info['description'],
                        'capabilities': package_info['capabilities'],
                        'source': 'json_adapter',
                        'adapter_config': package_info['adapter_config']
                    }
                    self.discovered_plugins.append(plugin_info)
                    logger.info(f"Added Python package plugin: {package_info['name']}")
                    
        except Exception as e:
            logger.debug(f"Error discovering Python packages: {e}")
            
    async def install_npm_plugin(self, plugin_name: str, global_install: bool = True) -> bool:
        """Install an NPM plugin automatically."""
        try:
            cmd = ['npm', 'install']
            if global_install:
                cmd.append('-g')
            cmd.append(plugin_name)
            
            logger.info(f"Installing NPM plugin: {plugin_name}")
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info(f"Successfully installed {plugin_name}")
                # Re-discover plugins to pick up the new one
                await self.discover_all_plugins()
                return True
            else:
                logger.error(f"Failed to install {plugin_name}: {stderr.decode()}")
                return False
                
        except Exception as e:
            logger.error(f"Error installing NPM plugin {plugin_name}: {e}")
            return False
            
    async def search_npm_plugins(self, query: str = "desktop-mcp") -> List[Dict]:
        """Search for available NPM plugins."""
        try:
            result = await asyncio.create_subprocess_exec(
                'npm', 'search', query, '--json',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                search_results = json.loads(stdout.decode())
                
                # Filter and format results
                plugins = []
                for package in search_results:
                    if (package.get('name', '').startswith('desktop-mcp-') or
                        'desktop-mcp' in package.get('keywords', [])):
                        plugins.append({
                            'name': package.get('name'),
                            'version': package.get('version'),
                            'description': package.get('description'),
                            'author': package.get('author', {}).get('name', 'Unknown'),
                            'keywords': package.get('keywords', []),
                            'npm_url': f"https://www.npmjs.com/package/{package.get('name')}"
                        })
                        
                return plugins
                
        except Exception as e:
            logger.error(f"Error searching NPM plugins: {e}")
            
        return []


class ZeroConfigRegistry:
    """Plugin registry that requires zero configuration."""
    
    def __init__(self):
        self.auto_discovery = AutoDiscovery()
        self.loaded_plugins: Dict[str, any] = {}
        
    async def auto_load_all(self) -> Dict[str, bool]:
        """Automatically discover and load all available plugins."""
        discovered = await self.auto_discovery.discover_all_plugins()
        results = {}
        
        for plugin_info in discovered:
            plugin_name = plugin_info['name']
            try:
                if plugin_info['type'] == 'npm':
                    success = await self._auto_load_npm_plugin(plugin_info)
                elif plugin_info['type'] == 'python':
                    success = await self._auto_load_python_plugin(plugin_info)
                elif plugin_info['type'] == 'python_package':
                    success = await self._auto_load_python_package_plugin(plugin_info)
                else:
                    success = False
                    
                results[plugin_name] = success
                
                if success:
                    logger.info(f"Auto-loaded plugin: {plugin_name}")
                else:
                    logger.warning(f"Failed to auto-load plugin: {plugin_name}")
                    
            except Exception as e:
                logger.error(f"Error auto-loading plugin {plugin_name}: {e}")
                results[plugin_name] = False
                
        return results
        
    async def _auto_load_npm_plugin(self, plugin_info: Dict) -> bool:
        """Auto-load an NPM plugin with zero configuration."""
        try:
            if plugin_info['type'] == 'npm':
                from .npm_plugin_loader import NPMPlugin
                
                # Create plugin with auto-detected configuration
                plugin = NPMPlugin(plugin_info['path'], config={
                    'auto_detected': plugin_info.get('auto_detected', False),
                    'source': plugin_info['source']
                })
                
            elif plugin_info['type'] == 'existing_npm':
                from .existing_package_adapter import ExistingPackagePlugin
                
                # Create adapted plugin for existing package
                plugin = ExistingPackagePlugin(
                    plugin_info['name'], 
                    plugin_info['path']
                )
                
            else:
                return False
            
            # Try to initialize
            if await plugin.initialize():
                self.loaded_plugins[plugin_info['name']] = plugin
                return True
                
        except Exception as e:
            logger.error(f"Error loading NPM plugin {plugin_info['name']}: {e}")
            
        return False
        
    async def _auto_load_python_plugin(self, plugin_info: Dict) -> bool:
        """Auto-load a Python plugin."""
        try:
            # Import and instantiate the plugin class
            module = __import__(plugin_info['module'], fromlist=[plugin_info['class']])
            plugin_class = getattr(module, plugin_info['class'])
            plugin = plugin_class()
            
            # Try to initialize
            if await plugin._safe_initialize():
                self.loaded_plugins[plugin_info['name']] = plugin
                return True
                
        except Exception as e:
            logger.error(f"Error loading Python plugin {plugin_info['name']}: {e}")
            
        return False
        
    async def _auto_load_python_package_plugin(self, plugin_info: Dict) -> bool:
        """Auto-load a Python package plugin with JSON adapter."""
        try:
            from .python_package_plugin import PythonPackagePlugin
            
            # Create plugin with adapter configuration
            plugin = PythonPackagePlugin(
                plugin_info['name'],
                plugin_info['adapter_config']
            )
            
            # Try to initialize
            if await plugin.initialize():
                self.loaded_plugins[plugin_info['name']] = plugin
                return True
                
        except Exception as e:
            logger.error(f"Error loading Python package plugin {plugin_info['name']}: {e}")
            
        return False
        
    async def install_and_load(self, plugin_name: str) -> bool:
        """Install and immediately load a plugin."""
        if await self.auto_discovery.install_npm_plugin(plugin_name):
            # Re-run auto-discovery and loading
            results = await self.auto_load_all()
            return results.get(plugin_name, False)
        return False
        
    def get_loaded_plugins(self) -> List[str]:
        """Get list of successfully loaded plugin names."""
        return list(self.loaded_plugins.keys())
        
    async def search_and_install(self, query: str) -> List[Dict]:
        """Search for plugins and optionally install them."""
        return await self.auto_discovery.search_npm_plugins(query)