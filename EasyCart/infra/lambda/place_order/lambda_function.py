import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
orders_table = dynamodb.Table("Orders")
cart_table = dynamodb.Table("UserCart")


def clean_decimal(obj):
    """Convert Decimals from DynamoDB into float for JSON-safe handling."""
    if isinstance(obj, list):
        return [clean_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def to_decimal(obj):
    """Convert floats back to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    return obj


def lambda_handler(event, context):

    body = json.loads(event["body"])
    user_id = body.get("user_id")
    customer = body.get("customer")
    payment_method = body.get("payment_method", "card")

    # 1️⃣ Get cart items
    cart_response = cart_table.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    )

    items = clean_decimal(cart_response.get("Items", []))

    if not items:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Cart is empty"})
        }

    # 2️⃣ Calculate total
    total = sum(i["price"] * i.get("qty", 1) for i in items)

    # 3️⃣ Generate order ID
    order_id = str(uuid.uuid4())

    # 4️⃣ Convert all floats → Decimal for DDB
    items_dynamo = to_decimal(items)
    total_dynamo = Decimal(str(total))

    # 5️⃣ Write order
    orders_table.put_item(
        Item={
            "order_id": order_id,
            "user_id": user_id,
            "items": items_dynamo,
            "total_amount": total_dynamo,
            "payment_method": payment_method,
            "customer_details": customer,
            "status": "Pending",
            "created_at": datetime.utcnow().isoformat()
        }
    )

    # 6️⃣ Clear cart
    for item in items:
        cart_table.delete_item(
            Key={"user_id": user_id, "item_id": item["item_id"]}
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Order placed successfully", "order_id": order_id})
    }
