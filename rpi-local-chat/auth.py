"""
Authentication module for PIN-based access control
"""
import secrets
import hashlib
import os

PIN_FILE = os.path.join(os.path.dirname(__file__), '.chat_pin')

def generate_pin():
    """Generate a random 6-digit PIN"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])

def hash_pin(pin):
    """Hash a PIN for secure storage"""
    return hashlib.sha256(pin.encode()).hexdigest()

def set_pin(pin=None):
    """Set the access PIN (generates random if not provided)"""
    if pin is None:
        pin = generate_pin()

    pin_hash = hash_pin(pin)

    with open(PIN_FILE, 'w') as f:
        f.write(pin_hash)

    # Set restrictive permissions
    os.chmod(PIN_FILE, 0o600)

    return pin

def verify_pin(pin):
    """Verify a PIN against the stored hash"""
    if not os.path.exists(PIN_FILE):
        return False

    with open(PIN_FILE, 'r') as f:
        stored_hash = f.read().strip()

    return hash_pin(pin) == stored_hash

def pin_exists():
    """Check if a PIN has been set"""
    return os.path.exists(PIN_FILE)

def generate_session_token():
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def initialize_pin():
    """Initialize PIN on first run"""
    if not pin_exists():
        pin = set_pin()
        print("\n" + "="*50)
        print("🔐 CHAT APP ACCESS PIN GENERATED")
        print("="*50)
        print(f"\n  Your PIN is: {pin}\n")
        print("  Share this PIN with users to allow access.")
        print("  Users will be prompted to enter this PIN")
        print("  when they first connect to the chat app.\n")
        print("="*50 + "\n")
        return pin
    return None

if __name__ == '__main__':
    # Test/reset PIN
    pin = set_pin()
    print(f"New PIN: {pin}")
    print(f"Verification: {verify_pin(pin)}")
