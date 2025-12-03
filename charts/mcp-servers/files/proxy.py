#!/usr/bin/env python3
"""
FastMCP Proxy Server for Transport Bridging
Bridges stdio-based MCP servers to streamableHttp transport

Usage: python proxy.py --backend-command "uvx mcp-server-time --local-timezone=Europe/Vienna" [options]
"""
import os
import sys
import shlex
import argparse
from fastmcp import FastMCP


def main():
    parser = argparse.ArgumentParser(
        description="FastMCP Proxy Server for Transport Bridging"
    )
    
    parser.add_argument(
        "--backend-command",
        required=True,
        help="Backend MCP server command as shell string (e.g., 'uvx mcp-server-time --local-timezone=Europe/Vienna')"
    )
    
    parser.add_argument(
        "--server-name",
        default="ProxyServer",
        help="Name for the proxy server (default: ProxyServer)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port to listen on (default: 3000)"
    )
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    # Parse backend command using shlex
    try:
        command_args = shlex.split(args.backend_command)
    except ValueError as e:
        print(f"Error: Failed to parse backend command: {e}", file=sys.stderr)
        print(f"Backend command: {args.backend_command}", file=sys.stderr)
        sys.exit(1)
    
    if not command_args:
        print("Error: Backend command resulted in empty command", file=sys.stderr)
        sys.exit(1)
    
    print(f"Starting {args.server_name} proxy on http://{args.host}:{args.port}/mcp", file=sys.stderr)
    print(f"Backend command: {' '.join(command_args)}", file=sys.stderr)
    
    # Create a temporary Python wrapper script that FastMCP can execute
    # FastMCP only supports .py files as script paths
    import tempfile
    import json
    
    # Create Python wrapper that executes the backend command
    script_content = f"""#!/usr/bin/env python3
import subprocess
import sys

# Execute the backend command
cmd = {json.dumps(command_args)}
subprocess.run(cmd, check=False)
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    os.chmod(script_path, 0o755)
    
    try:
        # Pass the script file path to as_proxy
        proxy = FastMCP.as_proxy(
            script_path,
            name=args.server_name
        )
        
        # Run the proxy server with streamable HTTP transport
        # FastMCP uses "http" as the transport name for streamable HTTP
        proxy.run(transport="http", host=args.host, port=args.port)
    finally:
        # Clean up temporary file
        if os.path.exists(script_path):
            os.unlink(script_path)


if __name__ == "__main__":
    main()
