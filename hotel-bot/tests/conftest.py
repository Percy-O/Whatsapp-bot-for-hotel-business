"""
Test configuration and fixtures
"""

import os
import sys
from pathlib import Path

# Set test environment
os.environ['ENV'] = 'test'
os.environ['DEBUG'] = 'False'
os.environ['ENVIRONMENT'] = 'test'
os.environ['SPAXCE_API_URL'] = 'http://localhost:9000'
os.environ['SPAXCE_API_TOKEN'] = 'test_token_12345'
os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
os.environ['WHATSAPP_TOKEN'] = 'test_whatsapp_token'
os.environ['WHATSAPP_PHONE_NUMBER_ID'] = 'test_phone_id'
os.environ['VERIFY_TOKEN'] = 'test_verify_token'

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
