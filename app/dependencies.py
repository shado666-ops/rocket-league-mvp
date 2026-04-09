import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

# Configuration des identifiants (à changer ou mettre en env var)
USER_ADMIN = os.getenv("ADMIN_USER", "admin")
PASS_ADMIN = os.getenv("ADMIN_PASSWORD", "rltracker")

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USER_ADMIN)
    correct_password = secrets.compare_digest(credentials.password, PASS_ADMIN)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
