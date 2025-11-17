import json
import boto3
import uuid

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("UserCart")

def lambda_handler(event, context):
    body = json.loads(event["body"])

    table.put_item(
        Item={
            "user_id": body["user_id"],
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
        "body": json.dumps({"message": "Added to cart"})
    }
