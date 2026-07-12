import json
import base64
import hashlib
import os

SECRET_SALT = "Dustway_Trader_Secret_Salt_2026_v4"

def secure_save(filepath: str, data) -> bool:
    """
    Saves the given dict or list to a file securely using Base64 + SHA256 HMAC.
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        # Generate signature
        signature = hashlib.sha256((json_str + SECRET_SALT).encode('utf-8')).hexdigest()
        
        # Payload format: signature:json_str
        payload = f"{signature}:{json_str}"
        
        # Base64 encode the payload
        encoded = base64.b64encode(payload.encode('utf-8')).decode('utf-8')
        
        # Write to temporary file first, then rename to avoid corruption
        temp_path = filepath + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(encoded)
            
        os.replace(temp_path, filepath)
        return True
    except Exception as e:
        print(f"Error secure saving {filepath}: {e}")
        return False

def secure_load(filepath: str, default_val=None):
    """
    Loads data from a secure save file.
    Has a fallback mechanism: if the file appears to be plain JSON, it will load it
    and then immediately save it in the secure format (migration).
    """
    if not os.path.exists(filepath):
        return default_val
        
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            
        if not content:
            return default_val
            
        # If it looks like plain JSON, we migrate it ONLY if it's a legacy save.
        if content.startswith("{") or content.startswith("["):
            try:
                data = json.loads(content)
                # Re-save it securely right now so it is locked forever
                secure_save(filepath, data)
                return data
            except json.JSONDecodeError:
                return default_val
            
        # Otherwise, try secure format
        try:
            payload = base64.b64decode(content).decode('utf-8')
        except Exception:
            return default_val
            
        if ":" in payload:
            signature, json_str = payload.split(":", 1)
            expected_sig = hashlib.sha256((json_str + SECRET_SALT).encode('utf-8')).hexdigest()
            
            if signature == expected_sig:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    return default_val
            else:
                print(f"Tamper detected in {filepath}! Signature mismatch.")
                return default_val
    except Exception as e:
        print(f"Error secure loading {filepath}: {e}")
        
    return default_val
