from datetime import timedelta
import os
import time
from dotenv import load_dotenv
from jose import ExpiredSignatureError, jwt, JWTError

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))


def generate_token(
    email: str, id: str, role: str, delta: timedelta = timedelta(days=3)
):
    payload = {
        "sub": email,
        "id": id,
        "role": role,
        "exp": time.time() + delta.total_seconds() + (ACCESS_TOKEN_EXPIRE_MINUTES * 60),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def validate_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise ExpiredSignatureError("Token has expired")
    except JWTError:
        raise JWTError("Invalid token")
    except Exception as e:
        raise e


if __name__ == "__main__":
    # Create a token
    email = "example@example.com"
    id = "1"
    role = "Practitioner"
    token = generate_token(email, id, role)
    print(token)
    # Validate the token
    payload = validate_token(token)
    # payload = validate_token("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJleGFtcGxlQGV4YW1wbGUuY29tIiwiaWQiOiIyMzEiLCJyb2xlIjoiYWRtaW4iLCJleHAiOjE3MTQ3NjE2MDEuMjU5MDM3fQ.tNjmsCXK7qbNmZ2tHfNjsVsHE0a-dxjn4BcNzTVyfSs")
    print(payload)
