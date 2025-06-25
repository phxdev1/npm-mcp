"""
Python package adapter for Desktop MCP.

Adapts existing Python packages like pyautogui to work as MCP plugins
using the same JSON configuration system as NPM packages.
"""

import json
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)


class PythonPackageAdapter:
    """Adapts existing Python packages to work as MCP plugins."""
    
    def __init__(self, package_name: str, config_path: str = None):
        self.package_name = package_name
        self.config_path = config_path
        self.config: Optional[Dict] = None
        self.package_module = None
        self._initialized = False
        self.setup_globals = {}
        
    async def initialize(self) -> bool:
        """Initialize the Python package adapter."""
        try:
            # Load configuration
            if not self._load_config():
                return False
                
            # Import the package
            self.package_module = importlib.import_module(self.package_name)
            
            # Run setup code if provided
            setup_code = self.config.get('setup', [])
            if setup_code:
                self.setup_globals = {'__builtins__': __builtins__}
                self.setup_globals[self.package_name] = self.package_module
                
                for line in setup_code:
                    exec(line, self.setup_globals)
                    
            self._initialized = True
            logger.info(f"Initialized Python adapter for {self.package_name}")
            return True
            
        except ImportError as e:
            logger.error(f"Package {self.package_name} not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing Python adapter for {self.package_name}: {e}")
            return False
            
    def _load_config(self) -> bool:
        """Load adapter configuration from JSON file."""
        if self.config_path:
            config_file = Path(self.config_path)
        else:
            # Default to adapters directory
            adapters_dir = Path(__file__).parent.parent / 'adapters'
            config_file = adapters_dir / f'{self.package_name}.json'
            
        if not config_file.exists():
            logger.error(f"Config file not found: {config_file}")
            return False
            
        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            return True
        except Exception as e:
            logger.error(f"Error loading config for {self.package_name}: {e}")
            return False
            
    @property
    def metadata(self):
        """Return plugin metadata."""
        from .plugin import PluginMetadata, PluginCapability, PluginPriority
        
        if not self.config:
            return None
            
        capabilities = []
        for cap_str in self.config.get('capabilities', []):
            try:
                capabilities.append(PluginCapability(cap_str))
            except ValueError:
                pass
                
        return PluginMetadata(
            name=f"python-{self.package_name}",
            version="1.0.0",
            description=self.config.get('description', ''),
            author="Auto-adapted from Python package",
            capabilities=capabilities,
            priority=PluginPriority.NORMAL
        )
        
    def get_mcp_functions(self) -> Dict[str, Callable]:
        """Return MCP functions for this adapted package."""
        if not self.config or not self._initialized:
            return {}
            
        functions = {}
        methods = self.config.get('methods', {})
        
        for method_name, method_config in methods.items():
            functions[method_name] = self._create_function_wrapper(method_name, method_config)
            
        return functions
        
    def _create_function_wrapper(self, method_name: str, method_config: Dict) -> Callable:
        """Create a wrapper function for a Python method."""
        
        async def wrapper(**kwargs):
            try:
                # Create execution environment
                exec_globals = {
                    '__builtins__': __builtins__,
                    self.package_name: self.package_module,
                    'params': kwargs
                }
                
                # Include setup globals (environment variables, etc.)
                exec_globals.update(self.setup_globals)
                
                # Add any additional imports that might be needed
                import_modules = ['base64', 'os', 'io', 'sys', 'shlex', 'platform', 'json', 'time']
                for module_name in import_modules:
                    try:
                        exec_globals[module_name] = importlib.import_module(module_name)
                    except ImportError:
                        pass
                        
                # Execute the method code by wrapping it in a function
                method_code = method_config.get('code', [])
                
                # Create a function wrapper to handle returns properly
                func_code = "def execute_method():\n"
                for line in method_code:
                    func_code += "    " + line + "\n"
                func_code += "\nresult = execute_method()"
                
                exec_locals = {}
                exec(func_code, exec_globals, exec_locals)
                
                return exec_locals.get('result', {"success": True, "message": f"Executed {method_name}"})
                
            except Exception as e:
                logger.error(f"Error executing {method_name}: {e}")
                raise Exception(f"Error in {method_name}: {str(e)}")
                
        # Set function metadata
        wrapper.__name__ = method_name
        wrapper.__doc__ = method_config.get('description', f"Method from {self.package_name}")
        
        return wrapper
        
    async def execute_function(self, method_name: str, **kwargs) -> Any:
        """Execute a specific method with given parameters."""
        if not self.config or not self._initialized:
            raise Exception(f"Adapter not initialized for {self.package_name}")
            
        methods = self.config.get('methods', {})
        if method_name not in methods:
            raise Exception(f"Method {method_name} not found in {self.package_name}")
            
        method_config = methods[method_name]
        wrapper = self._create_function_wrapper(method_name, method_config)
        return await wrapper(**kwargs)
        
    async def cleanup(self) -> None:
        """Clean up the adapter."""
        if self.config and 'cleanup' in self.config:
            cleanup_code = self.config['cleanup']
            cleanup_globals = {
                '__builtins__': __builtins__,
                self.package_name: self.package_module
            }
            
            try:
                for line in cleanup_code:
                    exec(line, cleanup_globals)
            except Exception as e:
                logger.error(f"Error during cleanup of {self.package_name}: {e}")
                
        self._initialized = False
        
    @property
    def initialized(self) -> bool:
        return self._initialized
        
    @property
    def enabled(self) -> bool:
        return True


def check_python_package_available(package_name: str) -> bool:
    """Check if a Python package is available for import."""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False