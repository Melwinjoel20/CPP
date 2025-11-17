import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserCart")

def lambda_handler(event, context):

    body = json.loads(event["body"])

    item_id = body.get("item_id")
    if not item_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "item_id is required"})
        }

    # 1️⃣ Find which user_id this item belongs to
    response = table.scan(
        FilterExpression=Key("item_id").eq(item_id)
    )

    items = response.get("Items", [])

    if not items:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "Item not found"})
        }

    record = items[0]
    user_id = record["user_id"]

    # 2️⃣ Now delete using both keys
    table.delete_item(
        Key={
            "user_id": user_id,
            "item_id": item_id
        }
    )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Item removed"})
    }
