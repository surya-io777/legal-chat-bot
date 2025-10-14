import boto3
import json
import hmac
import hashlib
import base64
from jose import jwt, JWTError

cognito = boto3.client("cognito-idp", region_name="us-east-1")
USER_POOL_ID = "us-east-1_9sajhw6fR"
CLIENT_ID = "2g81deb4kgrp8tm185hpa25jj"
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
        response = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "name", "Value": name},
            ]
        )

        return {"success": True, "message": "User created successfully. Please check your email for verification."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def authenticate_user(email, password):
    try:
        auth_params = {
            "USERNAME": email,
            "PASSWORD": password
        }

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
        error_msg = str(e)
        if "UserNotConfirmedException" in error_msg:
            return {"success": False, "error": "Please verify your email before signing in. Check your email for the verification code."}
        elif "NotAuthorizedException" in error_msg:
            return {"success": False, "error": "Invalid email or password."}
        else:
            return {"success": False, "error": str(e)}


def verify_email(email, verification_code):
    try:
        response = cognito.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=verification_code
        )
        return {"success": True, "message": "Email verified successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def resend_verification(email):
    try:
        response = cognito.resend_confirmation_code(
            ClientId=CLIENT_ID,
            Username=email
        )
        return {"success": True, "message": "Verification code sent"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def forgot_password(email):
    try:
        response = cognito.forgot_password(
            ClientId=CLIENT_ID,
            Username=email
        )
        return {"success": True, "message": "Password reset code sent to your email"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def reset_password(email, confirmation_code, new_password):
    try:
        response = cognito.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=confirmation_code,
            Password=new_password
        )
        return {"success": True, "message": "Password reset successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def verify_token(token):
    try:
        payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError:
        return None
