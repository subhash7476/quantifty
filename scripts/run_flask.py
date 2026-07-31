"""
Run the Flask development server.
"""
import sys
import os
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from flask_app import create_app
from core.logging import setup_logger

logger = setup_logger("flask_app")

if __name__ == '__main__':
    app = create_app()
    
    # Development server configuration
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    
    logger.info(f"Starting Flask server on http://{host}:{port}")
    logger.info(f"Debug mode: {debug}")
    logger.info("\nAvailable routes:")
    logger.info(f"  - http://{host}:{port}/         (redirects to login)")
    logger.info(f"  - http://{host}:{port}/login    (authentication)")
    logger.info(f"  - http://{host}:{port}/health   (health check)")
    logger.info(f"  - http://{host}:{port}/dashboard/ (requires login)")
    
    app.run(host=host, port=port, debug=debug)
