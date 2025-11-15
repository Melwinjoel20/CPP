import boto3
import json
import time
import os

REGION = "us-east-1"
PROJECT_NAME = "EasyCart"

CONFIG_PATH = "infra/config.json"
cognito = boto3.client("cognito-idp", region_name=REGION)


# -------------------------------------------------------------------
# Load/save config.json
# -------------------------------------------------------------------
def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)
    print("✔ Updated config.json")


# -------------------------------------------------------------------
# Existence checks
# -------------------------------------------------------------------
def pool_exists(pool_id):
    try:
        cognito.describe_user_pool(UserPoolId=pool_id)
        return True
    except:
        return False


def client_exists(pool_id, client_id):
    try:
        cognito.describe_user_pool_client(UserPoolId=pool_id, ClientId=client_id)
        return True
    except:
        return False


def domain_exists(domain_prefix):
    try:
        resp = cognito.describe_user_pool_domain(Domain=domain_prefix)
        return resp["DomainDescription"]["Status"] in ["ACTIVE", "CREATING"]
    except:
        return False


# -------------------------------------------------------------------
# 1️⃣ Create Pool If Missing
# -------------------------------------------------------------------
def create_user_pool_if_needed(config):
    if "user_pool_id" in config and pool_exists(config["user_pool_id"]):
        print(f"✔ User Pool exists: {config['user_pool_id']}")
        return config["user_pool_id"]

    print("\n[1] Creating Cognito User Pool...")

    resp = cognito.create_user_pool(
        PoolName=f"{PROJECT_NAME}-UserPool",
        AutoVerifiedAttributes=["email"],
        UsernameAttributes=["email"],
        VerificationMessageTemplate={
            "DefaultEmailOption": "CONFIRM_WITH_CODE",  # Safe for AWS Lab
            "EmailMessage": "Your EasyCart verification code is {{####}}",
            "EmailSubject": "EasyCart - Verify Your Email"
        }
    )

    pool_id = resp["UserPool"]["Id"]
    print(f"✔ Created User Pool: {pool_id}")
    return pool_id


# -------------------------------------------------------------------
#  Apply simple safe email template (no HTML)
# -------------------------------------------------------------------
def apply_safe_verification_template(user_pool_id):
    print("→ Applying safe verification email template...")

    try:
        cognito.update_user_pool(
            UserPoolId=user_pool_id,
            VerificationMessageTemplate={
                "DefaultEmailOption": "CONFIRM_WITH_CODE",
                "EmailMessage": (
                    "Welcome to EasyCart!\n\n"
                    "Your verification code is: {{####}}\n\n"
                    "If you didn't request this, ignore this email."
                ),
                "EmailSubject": "EasyCart Email Verification",
            },
        )
        print("✔ Verification template applied (simple + safe)")

    except Exception as e:
        print("⚠ Could NOT update email template (expected in AWS Lab):", e)


# -------------------------------------------------------------------
# 2️⃣ Create App Client If Missing
# -------------------------------------------------------------------
def create_app_client_if_needed(config, user_pool_id):
    if "app_client_id" in config and client_exists(user_pool_id, config["app_client_id"]):
        print(f"✔ App Client exists: {config['app_client_id']}")
        return config["app_client_id"]

    print("\n[2] Creating App Client...")

    resp = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=f"{PROJECT_NAME}-AppClient",
        GenerateSecret=False,
        ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH","ALLOW_ADMIN_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        CallbackURLs=["http://localhost:8000/auth/callback/"],  # placeholder
        LogoutURLs=["http://localhost:8000/auth/logout/"],
        AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=["email", "openid", "profile"],
        AllowedOAuthFlowsUserPoolClient=True
    )

    client_id = resp["UserPoolClient"]["ClientId"]
    print(f"✔ Created App Client: {client_id}")
    return client_id


# -------------------------------------------------------------------
# 3️⃣ Create Domain If Missing
# -------------------------------------------------------------------
def create_domain_if_needed(config, user_pool_id):
    if "domain_url" in config:
        prefix = config["domain_url"].split("//")[1].split(".")[0]
        if domain_exists(prefix):
            print(f"✔ Domain exists: {config['domain_url']}")
            return config["domain_url"]

    print("\n[3] Creating Cognito Domain...")

    prefix = f"{PROJECT_NAME.lower()}-{int(time.time())}"

    cognito.create_user_pool_domain(
        Domain=prefix,
        UserPoolId=user_pool_id
    )

    domain = f"https://{prefix}.auth.{REGION}.amazoncognito.com"
    print(f"✔ Created Domain: {domain}")
    return domain

def update_app_client(user_pool_id, client_id):
    print("→ Updating App Client to enable ADMIN_USER_PASSWORD_AUTH...")

    cognito.update_user_pool_client(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        ExplicitAuthFlows=[
            "ALLOW_USER_PASSWORD_AUTH",
            "ALLOW_ADMIN_USER_PASSWORD_AUTH",
            "ALLOW_REFRESH_TOKEN_AUTH"
        ]
    )

    print("✔ App Client updated.")



# -------------------------------------------------------------------
# MAIN DRIVER
# -------------------------------------------------------------------
def main():
    print("🚀 EasyCart Cognito Auto-Setup — SAFE MODE (AWS Lab Compatible)")

    config = load_config()

    user_pool_id = create_user_pool_if_needed(config)
    apply_safe_verification_template(user_pool_id)

    app_client_id = create_app_client_if_needed(config, user_pool_id)
    update_app_client(user_pool_id, app_client_id)
    domain_url = create_domain_if_needed(config, user_pool_id)

    config.update({
        "region": REGION,
        "user_pool_id": user_pool_id,
        "app_client_id": app_client_id,
        "domain_url": domain_url
    })

    save_config(config)

    print("\n🎉 Cognito Ready in AWS Lab (Safe Mode).")
    print("✔ You can run this script anytime — nothing breaks.")


if __name__ == "__main__":
    main()
