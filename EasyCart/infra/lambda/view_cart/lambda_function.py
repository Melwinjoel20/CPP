import json
import boto3
from boto3.dynamodb.conditions import Attr
from decimal import Decimal

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserCart")


def clean_decimal(obj):
    """Convert DynamoDB Decimal types to float for JSON serialization."""
    if isinstance(obj, list):
        return [clean_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Content-Type": "application/json",
    }


def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    # Detect method
    method = (
        (event.get("requestContext", {}) or {})
        .get("http", {})
        .get("method")
        or event.get("httpMethod", "")
    ).upper()

    # 0️⃣ Handle preflight
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": _cors_headers(),
            "body": ""
        }

    # ----------------------------------------------------
    # 🔥 NEW — Secure user from JWT (same as Add-to-Cart)
    # ----------------------------------------------------
    auth = event.get("requestContext", {}).get("authorizer", {})

    claims = auth.get("jwt", {}).get("claims", {}) or auth.get("claims", {})

    user_id = claims.get("email") or claims.get("cognito:username")

    if not user_id:
        return {
            "statusCode": 401,
            "headers": _cors_headers(),
            "body": json.dumps({"message": "Unauthorized: Please log in"})
        }
    # ----------------------------------------------------

    # 🔥 REMOVE old user_id from query/body logic
    # You asked not to remove anything, so we LEAVE IT,
    # but override user_id from JWT above.

    # 4️⃣ Only logged-in users reach here
    response = table.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    )

    items = response.get("Items", [])

    # Convert Decimal -> float
    items = clean_decimal(items)

    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps(items)
    }
