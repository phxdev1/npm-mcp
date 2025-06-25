"""
JSON-based adapter loader for existing NPM packages.

Loads adapter configurations from JSON files, making it easy to add
support for new packages without changing Python code.
"""

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class JSONAdapterLoader:
    """Loads and manages JSON-based package adapters."""
    
    def __init__(self, adapters_dir: str = None):
        if adapters_dir is None:
            # Default to adapters directory relative to this file
            self.adapters_dir = Path(__file__).parent.parent / 'adapters'
        else:
            self.adapters_dir = Path(adapters_dir)
            
        self.adapters: Dict[str, Dict] = {}
        self._load_all_adapters()
        
    def _load_all_adapters(self) -> None:
        """Load all JSON adapter configurations."""
        if not self.adapters_dir.exists():
            logger.warning(f"Adapters directory not found: {self.adapters_dir}")
            return
            
        for adapter_file in self.adapters_dir.glob('*.json'):
            try:
                with open(adapter_file, 'r') as f:
                    adapter_config = json.load(f)
                    
                package_name = adapter_config.get('package')
                if package_name:
                    self.adapters[package_name] = adapter_config
                    logger.info(f"Loaded adapter for {package_name}")
                else:
                    logger.warning(f"Invalid adapter config in {adapter_file}: missing package name")
                    
            except Exception as e:
                logger.error(f"Error loading adapter {adapter_file}: {e}")
                
    def get_adapter(self, package_name: str) -> Optional[Dict]:
        """Get adapter configuration for a package."""
        return self.adapters.get(package_name)
        
    def has_adapter(self, package_name: str) -> bool:
        """Check if an adapter exists for a package."""
        return package_name in self.adapters
        
    def list_supported_packages(self) -> List[str]:
        """Get list of packages with available adapters."""
        return list(self.adapters.keys())
        
    def create_bridge_script(self, package_name: str) -> Optional[str]:
        """Create a Node.js bridge script for a package using its JSON config."""
        adapter_config = self.get_adapter(package_name)
        if not adapter_config:
            return None
            
        # Generate the bridge script
        script_parts = []
        
        # Imports
        import_name = adapter_config.get('import_name', package_name)
        script_parts.append(f"const {import_name} = require('{package_name}');")
        script_parts.append("const readline = require('readline');")
        script_parts.append("")
        
        # Setup code
        setup_code = adapter_config.get('setup', [])
        if setup_code:
            script_parts.append("// Setup")
            script_parts.extend(setup_code)
            script_parts.append("")
            
        # Main communication loop
        script_parts.append("""
// Setup readline for JSON-RPC communication
const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
});

// Handle incoming requests
rl.on('line', async (line) => {
    try {
        const request = JSON.parse(line);
        const { method, params, id } = request;
        
        let result;
        """)
        
        # Generate method handlers
        methods = adapter_config.get('methods', {})
        for method_name, method_config in methods.items():
            script_parts.append(f"        if (method === '{method_name}') {{")
            
            # Add the method code
            method_code = method_config.get('code', [])
            for line in method_code:
                script_parts.append(f"            {line}")
                
            script_parts.append("        }")
            
        # Error handling and response
        script_parts.append("""
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
});""")
        
        # Cleanup on exit
        cleanup_code = adapter_config.get('cleanup', [])
        if cleanup_code:
            script_parts.append("""
// Handle cleanup on exit
process.on('SIGTERM', async () => {
    try {""")
            for line in cleanup_code:
                script_parts.append(f"        {line}")
            script_parts.append("""    } catch (error) {
        console.error('Cleanup error:', error);
    }
    process.exit(0);
});""")
        
        # Join all parts
        bridge_script = '\n'.join(script_parts)
        
        # Write to temporary file
        bridge_file = tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False)
        bridge_file.write(bridge_script)
        bridge_file.close()
        
        return bridge_file.name
        
    def get_method_schemas(self, package_name: str) -> Dict[str, Dict]:
        """Get MCP function schemas for a package's methods."""
        adapter_config = self.get_adapter(package_name)
        if not adapter_config:
            return {}
            
        schemas = {}
        methods = adapter_config.get('methods', {})
        
        for method_name, method_config in methods.items():
            # Generate schema from parameters
            parameters = method_config.get('parameters', [])
            properties = {}
            required = []
            
            for param in parameters:
                if '?' in param:
                    # Optional parameter with default
                    param_name = param.split('?')[0]
                    default_value = param.split('=')[1] if '=' in param else None
                    properties[param_name] = {
                        "type": self._infer_type(default_value),
                        "description": f"Optional parameter for {method_name}"
                    }
                    if default_value:
                        properties[param_name]["default"] = self._parse_default(default_value)
                else:
                    # Required parameter
                    param_name = param
                    properties[param_name] = {
                        "type": "string",  # Default to string
                        "description": f"Required parameter for {method_name}"
                    }
                    required.append(param_name)
                    
            schemas[method_name] = {
                "name": method_name,
                "description": method_config.get('description', f"Method from {package_name}"),
                "inputSchema": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            
        return schemas
        
    def _infer_type(self, default_value: str) -> str:
        """Infer JSON schema type from default value string."""
        if default_value is None:
            return "string"
        if default_value.lower() in ['true', 'false']:
            return "boolean"
        if default_value.isdigit():
            return "integer"
        try:
            float(default_value)
            return "number"
        except ValueError:
            return "string"
            
    def _parse_default(self, default_value: str) -> Any:
        """Parse default value string to appropriate type."""
        if default_value.lower() == 'true':
            return True
        elif default_value.lower() == 'false':
            return False
        elif default_value.isdigit():
            return int(default_value)
        else:
            try:
                return float(default_value)
            except ValueError:
                return default_value.strip("'\"")  # Remove quotes if present