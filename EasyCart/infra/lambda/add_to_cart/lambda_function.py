import json
import boto3
import uuid

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserCart")

def lambda_handler(event, context):
    body = json.loads(event["body"])

    # ✅ STEP 1: Validate user_id
    user_id = body.get("user_id")
    if not user_id:
        return {
            "statusCode": 401,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Please log in to add items to your cart."})
        }

    # STEP 2: Proceed with adding to cart (only logged-in users reach here)
    table.put_item(
        Item={
            "user_id": user_id,
            "item_id": str(uuid.uuid4()),
            "product_id": body["product_id"],
            "name": body["name"],
            "price": body["price"],
            "image": body["image"],
            "qty": 1
        }
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Added to cart"})
    }
