import json
import boto3
import uuid

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserCart")


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Content-Type": "application/json",
    }


def lambda_handler(event, context):
    # Optional: log for debugging
    print("Incoming event:", json.dumps(event))

    # Safely detect HTTP method (HTTP API v2 or REST API)
    method = (
        (event.get("requestContext", {}) or {})
        .get("http", {})
        .get("method")
        or event.get("httpMethod", "")
    ).upper()

    # 0️⃣ Handle CORS preflight
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": _cors_headers(),
            "body": ""
        }

    # 1️⃣ Parse body safely
    body_str = event.get("body") or "{}"
    try:
        body = json.loads(body_str)
    except (TypeError, json.JSONDecodeError):
        body = {}

    # 2️⃣ Validate user_id (only logged in users)
    user_id = body.get("user_id")
    if not user_id:
        return {
            "statusCode": 401,
            "headers": _cors_headers(),
            "body": json.dumps({"message": "Please log in to add items to your cart."})
        }

    # 3️⃣ Proceed with adding to cart
    table.put_item(
        Item={
            "user_id": user_id,
            "item_id": str(uuid.uuid4()),
            "product_id": body.get("product_id"),
            "name": body.get("name"),
            "price": body.get("price"),
            "image": body.get("image"),
            "qty": 1
        }
    )

    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps({"message": "Added to cart"})
    }
