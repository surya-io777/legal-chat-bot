import boto3
import json
from jose import jwt, JWTError

cognito = boto3.client('cognito-idp', region_name='us-east-1')
USER_POOL_ID = 'us-east-1_9sajhw6fR'
CLIENT_ID = '2g81deb4kgrp8tm185hpa25jj'

def create_user(email, password, name):
    try:
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'name', 'Value': name}
            ],
            TemporaryPassword=password,
            MessageAction='SUPPRESS'
        )
        
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=email,
            Password=password,
            Permanent=True
        )
        
        return {'success': True, 'message': 'User created successfully'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def authenticate_user(email, password):
    try:
        response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        return {
            'success': True,
            'access_token': response['AuthenticationResult']['AccessToken'],
            'id_token': response['AuthenticationResult']['IdToken']
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def verify_token(token):
    try:
        payload = jwt.get_unverified_claims(token)
        return payload
    except JWTError:
        return None