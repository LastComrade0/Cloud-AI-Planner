# app/dependencies/auth.py
from fastapi import Header, HTTPException, Depends, status
from sqlalchemy.orm import Session
from app.models.db_models import User
from app.dependencies.db import get_db
from typing import Optional
import jwt
import requests
from jose import jwk, jwt as jose_jwt
from jose.utils import base64url_decode
import json
import os

# Cognito configuration
COGNITO_REGION = os.getenv('COGNITO_REGION', 'us-west-1')
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
COGNITO_APP_CLIENT_ID = os.getenv('COGNITO_APP_CLIENT_ID')

# Cache for JWKS
_jwks_cache = None

def get_cognito_jwks():
    """Get Cognito JWKS (JSON Web Key Set) for token verification"""
    global _jwks_cache
    
    if _jwks_cache is None:
        jwks_url = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json'
        try:
            response = requests.get(jwks_url, timeout=5)
            response.raise_for_status()
            _jwks_cache = response.json()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to fetch Cognito JWKS: {str(e)}"
            )
    
    return _jwks_cache

def verify_cognito_token(token: str) -> dict:
    """Verify and decode Cognito JWT token"""
    if not COGNITO_USER_POOL_ID or not COGNITO_APP_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cognito configuration missing"
        )
    
    try:
        # Get token header
        headers = jose_jwt.get_unverified_header(token)
        
        # Get JWKS
        jwks = get_cognito_jwks()
        
        # Find the key
        key = None
        for jwk_key in jwks['keys']:
            if jwk_key['kid'] == headers['kid']:
                key = jwk_key
                break
        
        if not key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate key"
            )
        
        # Construct the public key
        public_key = jwk.construct(key)
        
        # Decode and verify token
        message, encoded_signature = str(token).rsplit('.', 1)
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        
        if not public_key.verify(message.encode("utf8"), decoded_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Signature verification failed"
            )
        
        # Decode token claims
        claims = jose_jwt.get_unverified_claims(token)
        
        # Verify token claims
        if claims.get('token_use') not in ['id', 'access']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token use"
            )
        
        # For ID tokens, verify audience
        if claims.get('token_use') == 'id':
            if claims.get('aud') != COGNITO_APP_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token audience doesn't match"
                )
        
        # Verify issuer
        expected_issuer = f'https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}'
        if claims.get('iss') != expected_issuer:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer doesn't match"
            )
        
        return claims
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}"
        )

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from Cognito JWT token.
    Expects Authorization header with format: "Bearer <token>"
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    # Extract token from "Bearer <token>"
    try:
        parts = authorization.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected: Bearer <token>"
            )
        token = parts[1]
    except (IndexError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    # Verify token
    claims = verify_cognito_token(token)
    
    # Get cognito_sub from token (this is the unique user identifier)
    cognito_sub = claims.get('sub')
    email = claims.get('email')
    
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing sub claim"
        )
    
    # Find or create user in database
    user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
    
    if not user:
        # Create new user
        user = User(
            cognito_sub=cognito_sub,
            email=email or f"{cognito_sub}@cognito.local"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif email and user.email != email:
        # Update email if it changed
        user.email = email
        db.commit()
        db.refresh(user)
    
    return user