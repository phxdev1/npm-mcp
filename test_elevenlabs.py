#!/usr/bin/env python3
"""
Test script to load only the ElevenLabs adapter.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the desktop_mcp directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from desktop_mcp.core.python_adapter import PythonPackageAdapter

async def test_elevenlabs():
    """Test loading only the ElevenLabs adapter."""
    print("Testing ElevenLabs adapter...")
    
    # Load the ElevenLabs adapter
    adapter_path = Path(__file__).parent / "desktop_mcp" / "adapters" / "elevenlabs.json"
    
    print(f"Loading adapter from: {adapter_path}")
    
    adapter = PythonPackageAdapter("elevenlabs", str(adapter_path))
    
    # Initialize the adapter
    print("Initializing adapter...")
    success = await adapter.initialize()
    
    if success:
        print("✅ ElevenLabs adapter loaded successfully!")
        
        # Get the functions
        functions = adapter.get_mcp_functions()
        print(f"Available functions: {list(functions.keys())}")
        
        # Test the speak_text function
        print("\nTesting speak_text function...")
        try:
            result = await functions['speak_text'](text="Hello World")
            print(f"speak_text result: {result}")
        except Exception as e:
            print(f"❌ Error calling speak_text: {e}")
            
    else:
        print("❌ Failed to load ElevenLabs adapter")

if __name__ == "__main__":
    asyncio.run(test_elevenlabs())