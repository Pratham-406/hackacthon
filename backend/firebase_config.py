"""
Firebase Admin SDK Configuration and Initialization for SmartPool FastAPI Gateway.
Module: backend/firebase_config.py
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger("smartpool.firebase")
logger.setLevel(logging.INFO)

# Lazy-loaded singleton references
_firebase_app = None
_firestore_client = None
_is_firebase_admin_initialized = False


def initialize_firebase_admin():
    """
    Initializes the Firebase Admin SDK safely.
    Checks in order:
    1. FIREBASE_SERVICE_ACCOUNT_JSON (raw JSON environment variable)
    2. FIREBASE_SERVICE_ACCOUNT_KEY (file path environment variable)
    3. GOOGLE_APPLICATION_CREDENTIALS (standard GCP file path environment variable)
    4. Default application credentials with FIREBASE_PROJECT_ID
    5. Local emulator / development fallback
    """
    global _firebase_app, _firestore_client, _is_firebase_admin_initialized

    if _is_firebase_admin_initialized:
        return _firestore_client

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Check existing apps
        if firebase_admin._apps:
            _firebase_app = firebase_admin.get_app()
            _firestore_client = firestore.client()
            _is_firebase_admin_initialized = True
            logger.info("Firebase Admin already initialized.")
            return _firestore_client

        # 1. Raw JSON string in environment variable
        sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            try:
                sa_dict = json.loads(sa_json)
                cred = credentials.Certificate(sa_dict)
                _firebase_app = firebase_admin.initialize_app(cred)
                _firestore_client = firestore.client()
                _is_firebase_admin_initialized = True
                logger.info("Firebase Admin initialized via FIREBASE_SERVICE_ACCOUNT_JSON.")
                return _firestore_client
            except Exception as e:
                logger.error(f"Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

        # 2. File path in FIREBASE_SERVICE_ACCOUNT_KEY or GOOGLE_APPLICATION_CREDENTIALS
        sa_key_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_KEY") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if sa_key_path and os.path.isfile(sa_key_path):
            try:
                cred = credentials.Certificate(sa_key_path)
                _firebase_app = firebase_admin.initialize_app(cred)
                _firestore_client = firestore.client()
                _is_firebase_admin_initialized = True
                logger.info(f"Firebase Admin initialized via service account file: {sa_key_path}")
                return _firestore_client
            except Exception as e:
                logger.error(f"Failed to load service account file {sa_key_path}: {e}")

        # 3. Check for default credentials with project ID or emulator
        project_id = os.environ.get("FIREBASE_PROJECT_ID")
        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")

        if emulator_host or project_id:
            try:
                options = {"projectId": project_id} if project_id else {}
                _firebase_app = firebase_admin.initialize_app(options=options)
                _firestore_client = firestore.client()
                _is_firebase_admin_initialized = True
                logger.info(f"Firebase Admin initialized with projectId: {project_id}")
                return _firestore_client
            except Exception as e:
                logger.warning(f"Could not initialize with default credentials/projectId: {e}")

        # If none succeeded
        logger.warning(
            "[SmartPool] Firebase service account credentials not found. "
            "Backend will run with local persistent fallback database. "
            "To connect real Firestore, set FIREBASE_SERVICE_ACCOUNT_KEY or FIREBASE_SERVICE_ACCOUNT_JSON."
        )
        _is_firebase_admin_initialized = False
        return None

    except ImportError:
        logger.warning("firebase-admin package not installed. Running in local fallback mode.")
        _is_firebase_admin_initialized = False
        return None
    except Exception as e:
        logger.error(f"Unexpected error during Firebase Admin initialization: {e}")
        _is_firebase_admin_initialized = False
        return None


def get_firestore_client():
    """Returns the Firestore client instance, or None if not initialized."""
    if not _is_firebase_admin_initialized:
        initialize_firebase_admin()
    return _firestore_client


def is_firebase_connected() -> bool:
    """Returns True if real Firebase Admin SDK is connected."""
    return _is_firebase_admin_initialized and (_firestore_client is not None)


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Firebase ID token.
    Returns decoded token dictionary containing 'uid', 'email', etc., or None if invalid.
    """
    if not is_firebase_connected():
        # In unconfigured / test mode, allow decoding a simulated test token if present
        if id_token and id_token.startswith("test-token-"):
            uid = id_token.replace("test-token-", "")
            return {"uid": uid, "email": f"{uid}@smartpool.local", "name": uid.capitalize()}
        return None

    try:
        from firebase_admin import auth
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        return None
