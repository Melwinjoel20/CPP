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


def lambda_handler(event, context):

    # Get query string params safely
    params = event.get("queryStringParameters") or {}
    user_id = params.get("user_id")

    # ✅ Block if user_id is missing → treat as not logged in
    if not user_id:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Please log in to view your cart."})
        }

    # Only logged-in users reach here
    response = table.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    )

    items = response.get("Items", [])

    # Convert Decimal -> float for JSON
    items = clean_decimal(items)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(items)
    }
