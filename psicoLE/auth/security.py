"""Security utilities for the authentication system."""

import hashlib
import hmac
import os
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import current_app, request, abort, jsonify, session
from flask_login import current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Cache for IP blocking
ip_attempts = {}

def is_ip_blocked(ip_address):
    """Check if an IP address is temporarily blocked due to too many failed attempts."""
    if ip_address not in ip_attempts:
        return False
    
    attempts, first_attempt = ip_attempts[ip_address]
    if attempts >= current_app.config.get('MAX_LOGIN_ATTEMPTS', 5):
        # Check if the block period has passed
        block_duration = current_app.config.get('ACCOUNT_LOCKOUT_MINUTES', 30)
        if (datetime.utcnow() - first_attempt) < timedelta(minutes=block_duration):
            return True
        else:
            # Reset attempts if block period has passed
            del ip_attempts[ip_address]
    return False

def record_failed_attempt(ip_address):
    """Record a failed login attempt for an IP address."""
    if ip_address not in ip_attempts:
        ip_attempts[ip_address] = [1, datetime.utcnow()]
    else:
        ip_attempts[ip_address][0] += 1

def generate_token():
    """Generate a secure random token."""
    return hashlib.sha256(os.urandom(32)).hexdigest()

def generate_secure_hash(data, secret_key=None):
    """Generate a secure hash of the given data."""
    if secret_key is None:
        secret_key = current_app.secret_key
    return hmac.new(
        secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_secure_hash(data, hash_value, secret_key=None):
    """Verify a secure hash."""
    return hmac.compare_digest(
        generate_secure_hash(data, secret_key),
        hash_value
    )

def hash_password(password):
    """Hash a password for storing."""
    return generate_password_hash(
        password,
        method='pbkdf2:sha256',
        salt_length=16
    )

def check_password(hashed_password, password):
    """Check a password against a hash."""
    return check_password_hash(hashed_password, password)
