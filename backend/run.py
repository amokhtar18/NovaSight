#!/usr/bin/env python
"""
NovaSight Backend Runner
========================

Application entry point for development.

Usage:
    python run.py              # Run with default settings
    python run.py --debug      # Run in debug mode
    python run.py --port 5001  # Run on specific port
"""

import os
import sys
import argparse

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run NovaSight Backend")
    parser.add_argument(
        "--host",
        default=os.getenv("FLASK_HOST", "0.0.0.0"),
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("FLASK_PORT", 5000)),
        help="Port to bind to (default: 5000)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.getenv("FLASK_DEBUG", "").lower() == "true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--env",
        default=os.getenv("FLASK_ENV", "development"),
        choices=["development", "testing", "production"],
        help="Environment (default: development)"
    )
    return parser.parse_args()


def main():
    """Run the Flask application."""
    args = parse_args()
    
    # Set environment
    os.environ["FLASK_ENV"] = args.env
    
    # Create app
    app = create_app(args.env)
    
    # Print startup info
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║                 NovaSight Backend API                      ║
╠═══════════════════════════════════════════════════════════╣
║  Environment: {args.env:<43} ║
║  Host:        {args.host:<43} ║
║  Port:        {args.port:<43} ║
║  Debug:       {str(args.debug):<43} ║
╠═══════════════════════════════════════════════════════════╣
║  API:         http://{args.host}:{args.port}/api/v1           ║
║  Health:      http://{args.host}:{args.port}/api/v1/health    ║
║  Docs:        http://{args.host}:{args.port}/api/docs         ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # Run application
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug
    )


if __name__ == "__main__":
    main()
