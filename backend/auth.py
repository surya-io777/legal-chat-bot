import boto3
import json
import hmac
import hashlib
import base64
from jose import jwt, JWTError

cognito = boto3.client("cognito-idp", region_name="us-east-1")
USER_POOL_ID = "us-east-1_9sajhw6fR"
CLIENT_ID = "5dtpjt0i38tnm9dtj4scigaras"
CLIENT_SECRET = None  # We'll disable this


def get_secret_hash(username):
    """Generate SECRET_HASH for Cognito"""
    if not CLIENT_SECRET:
        return None
    message = username + CLIENT_ID
    dig = hmac.new(
        CLIENT_SECRET.encode("UTF-8"),
        msg=message.encode("UTF-8"),
        digestmod=hashlib.sha256,
    ).digest()
    return base64.b64encode(dig).decode()


def create_user(email, password, name):
    try:
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name},
            ],
            TemporaryPassword=password,
            MessageAction="SUPPRESS",
        )

        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID, Username=email, Password=password, Permanent=True
        )

        return {"success": True, "message": "User created successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def authenticate_user(email, password):
    try:
        auth_params = {"USERNAME": email, "PASSWORD": password}

        # Add SECRET_HASH if client secret is configured
        secret_hash = get_secret_hash(email)
        if secret_hash:
            auth_params["SECRET_HASH"] = secret_hash

        response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters=auth_params,
        )

        return {
            "success": True,
            "access_token": response["AuthenticationResult"]["AccessToken"],
            "id_token": response["AuthenticationResult"]["IdToken"],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def verify_token(token):
    try:
        payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError:
        return None
