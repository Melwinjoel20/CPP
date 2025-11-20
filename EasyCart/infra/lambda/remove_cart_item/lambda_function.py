import json
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserCart")


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Content-Type": "application/json",
    }


def lambda_handler(event, context):
    print("Incoming event:", json.dumps(event))

    # Detect method (v2 - API GW HTTP API or v1)
    method = (
        event.get("requestContext", {})
             .get("http", {})
             .get("method")
        or event.get("httpMethod", "")
    ).upper()

    # 0️⃣ OPTIONS preflight
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
    except:
        body = {}

    item_id = body.get("item_id")

    if not item_id:
        return {
            "statusCode": 400,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "item_id is required"})
        }

    # 2️⃣ Scan because item_id is NOT the partition key
    response = table.scan(
        FilterExpression=Attr("item_id").eq(item_id)
