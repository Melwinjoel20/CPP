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

    params = event.get("queryStringParameters") or {}
    user_id = params.get("user_id")

    if not user_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "user_id is required"})
        }

    # Your UserCart table likely has NO sort key -> use scan
    response = table.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    )

    items = response.get("Items", [])

    # Convert Decimal -> float
    items = clean_decimal(items)

    return {
        "statusCode": 200,
        "body": json.dumps(items)
    }
