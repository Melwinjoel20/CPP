import boto3
import json
import time

REGION = "us-east-1"
PROJECT_NAME = "EasyCart"

cognito = boto3.client("cognito-idp", region_name=REGION)

def save_config(data):
    """Save Cognito details to config.json"""
    with open("infra/config.json", "w") as f:
        json.dump(data, f, indent=4)
    print("\n[✔] Saved config to infrastructure/config.json")

def create_user_pool():
    print("\n[1] Creating Cognito User Pool...")

    response = cognito.create_user_pool(
        PoolName=f"{PROJECT_NAME}-UserPool",
        AutoVerifiedAttributes=["email"],
        UsernameAttributes=["email"],
        VerificationMessageTemplate={
            "DefaultEmailOption": "CONFIRM_WITH_LINK"
        }
    )

    user_pool_id = response["UserPool"]["Id"]
    print(f"[✔] Created User Pool: {user_pool_id}")
    return user_pool_id

def create_app_client(user_pool_id):
    print("\n[2] Creating App Client...")

    response = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f"{PROJECT_NAME}-AppClient",
        GenerateSecret=False,
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        CallbackURLs=["http://localhost:8000/auth/callback/", "https://example.com/callback"],
        LogoutURLs=["http://localhost:8000/auth/logout/"],
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["email", "openid", "profile"],
        AllowedOAuthFlowsUserPoolClient=True
    )

    client_id = response["UserPoolClient"]["ClientId"]
    print(f"[✔] Created App Client: {client_id}")
    return client_id

def create_domain(user_pool_id):
    print("\n[3] Creating Cognito Hosted UI Domain...")

    domain_prefix = f"{PROJECT_NAME.lower()}-{int(time.time())}"
    
    try:
        cognito.create_user_pool_domain(
            Domain=domain_prefix,
            UserPoolId=user_pool_id,
        )
    except Exception as e:
        print(f"[ERROR] Domain creation failed: {e}")
        return None

    domain_url = f"https://{domain_prefix}.auth.{REGION}.amazoncognito.com"
    print(f"[✔] Created Domain: {domain_url}")
    return domain_url

def main():
    print("\n🚀 Starting Cognito Setup for EasyCart")

    user_pool_id = create_user_pool()
    client_id = create_app_client(user_pool_id)
    domain_url = create_domain(user_pool_id)

    config = {
        "region": REGION,
        "user_pool_id": user_pool_id,
        "app_client_id": client_id,
        "domain_url": domain_url
    }

    save_config(config)

    print("\n🎉 Cognito Setup Completed Successfully!")

if __name__ == "__main__":
    main()
