import boto3
import json
import os
from botocore.exceptions import ClientError

CONFIG_PATH = "infra/config.json"

def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)
    print("✔ Updated config.json")

def create_cart_table(region):
    dynamodb = boto3.client("dynamodb", region_name=region)
    table_name = "UserCart"

    try:
        dynamodb.describe_table(TableName=table_name)
        print("✔ DynamoDB table already exists:", table_name)
        return table_name
    except ClientError:
        pass

    print("🛠 Creating DynamoDB table: UserCart")

    dynamodb.create_table(
        TableName=table_name,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "item_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "item_id", "KeyType": "RANGE"},
        ],
    )

    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=table_name)

    print("✔ UserCart table created")
    return table_name


def create_lambda(region, fn_name, file_path):
    lambda_client = boto3.client("lambda", region_name=region)

    role_arn = "arn:aws:iam::730335531611:role/LabRole"

    with open(file_path, "rb") as f:
        zip_bytes = f.read()

    # Check if Lambda exists
    try:
        lambda_client.get_function(FunctionName=fn_name)
        print(f"✔ Lambda exists: {fn_name}")

        # ⭐ IMPORTANT: Update existing Lambda code
        lambda_client.update_function_code(
            FunctionName=fn_name,
            ZipFile=zip_bytes,
            Publish=True
        )
        print(f"🔄 Updated Lambda code for {fn_name}")

        return fn_name

    except lambda_client.exceptions.ResourceNotFoundException:
        pass

    # Create Lambda if does not exist
    print(f"🛠 Creating Lambda: {fn_name}")

    lambda_client.create_function(
        FunctionName=fn_name,
        Runtime="python3.9",
        Role=role_arn,
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zip_bytes},
        Timeout=15,
        Publish=True
    )

    print(f"✔ Lambda created: {fn_name}")
    return fn_name


def enable_function_url(fn_name, region):
    client = boto3.client("lambda", region_name=region)

    # Correct CORS
    good_cors = {
        "AllowMethods": ["*"],
        "AllowOrigins": ["*"],
        "AllowHeaders": ["*"]
    }

    # Empty cors to purge corrupted metadata
    empty_cors = {
        "AllowMethods": [],
        "AllowOrigins": [],
        "AllowHeaders": []
    }

    print(f"🔧 Resetting corrupted CORS for {fn_name}...")

    # Step 1 — Delete function URL if exists
    try:
        client.delete_function_url_config(FunctionName=fn_name)
    except client.exceptions.ResourceNotFoundException:
        pass

    # Step 2 — Create a fresh URL with EMPTY CORS (forces AWS to clear old metadata)
    resp = client.create_function_url_config(
        FunctionName=fn_name,
        AuthType="NONE",
        Cors=empty_cors
    )

    # Step 3 — Immediately UPDATE with correct CORS (this will now work)
    resp = client.update_function_url_config(
        FunctionName=fn_name,
        AuthType="NONE",
        Cors=good_cors
    )

    url = resp["FunctionUrl"]

    # Step 4 — Permission (safe)
    try:
        client.add_permission(
            FunctionName=fn_name,
            Action="lambda:InvokeFunctionUrl",
            Principal="*",
            FunctionUrlAuthType="NONE",
            StatementId=f"{fn_name}-public"
        )
    except ClientError as e:
        if "already exists" in str(e):
            pass
        else:
            raise e

    print(f"✔ Function URL Enabled → {url}")
    return url



def main():
    print("\n🚀 Setting up CART SERVICE (DynamoDB + Lambdas + URLs)\n")

    cfg = load_config()
    region = cfg["region"]

    # 1️⃣ Create DynamoDB table
    cart_table = create_cart_table(region)
    cfg["cart_table"] = cart_table

    # 2️⃣ Deploy Lambda functions
    lambdas = {
        "add_to_cart": "infra/lambda/add_to_cart.zip",
        "view_cart": "infra/lambda/view_cart.zip",
        "remove_cart_item": "infra/lambda/remove_cart_item.zip"
    }

    lambda_urls = {}

    for name, path in lambdas.items():
        fn_name = f"EasyCart_{name}"
        create_lambda(region, fn_name, path)
        url = enable_function_url(fn_name, region)
        lambda_urls[name] = url

    cfg["lambda_cart_endpoints"] = lambda_urls
    save_config(cfg)

    print("\n🎉 CART SERVICE READY!")
    print(json.dumps(lambda_urls, indent=4))


if __name__ == "__main__":
    main()
