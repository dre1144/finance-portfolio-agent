from cryptography.fernet import Fernet
import base64
import os
from dotenv import load_dotenv

class TokenSecurity:
    def __init__(self):
        load_dotenv()
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        if not self.encryption_key:
            self.encryption_key = Fernet.generate_key().decode()
            print(f"Generated new encryption key: {self.encryption_key}")
        
        self.cipher_suite = Fernet(self.encryption_key.encode())

    def encrypt_token(self, token: str) -> str:
        """Encrypt the Tinkoff API token."""
        return self.cipher_suite.encrypt(token.encode()).decode()

    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt the Tinkoff API token."""
        return self.cipher_suite.decrypt(encrypted_token.encode()).decode()

def generate_new_key():
    """Generate a new encryption key."""
    return Fernet.generate_key().decode()

if __name__ == "__main__":
    # Example usage
    security = TokenSecurity()
    
    # If you need to encrypt a new token
    if input("Do you want to encrypt a new token? (y/n): ").lower() == 'y':
        token = input("Enter your Tinkoff API token: ")
        encrypted = security.encrypt_token(token)
        print(f"\nEncrypted token: {encrypted}")
        print("\nAdd these to your .env file:")
        print(f"TINKOFF_TOKEN_ENCRYPTED={encrypted}")
        if not os.getenv('ENCRYPTION_KEY'):
            print(f"ENCRYPTION_KEY={security.encryption_key}") 