import json
import boto3
import uuid
import os
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Attr

# Load SNS topic ARN from Environment Variables
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN")

sns = boto3.client("sns")
dynamodb = boto3.resource("dynamodb")

orders_table = dynamodb.Table("Orders")
cart_table = dynamodb.Table("UserCart")


def clean_decimal(obj):
    """Convert Decimals → float for JSON-safe operations."""
    if isinstance(obj, list):
        return [clean_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def to_decimal(obj):
    """Convert floats → Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, list):
        return [to_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: to_decimal(v) for k, v in obj.items()}
    return obj


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Content-Type": "application/json",
    }


def lambda_handler(event, context):
    # Optional: log event for debugging
    print("Incoming event:", json.dumps(event))

    # Safely detect method (HTTP API v2 or REST API)
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

    user_id = body.get("user_id")
    customer = body.get("customer") or {}
    payment_method = body.get("payment_method", "card")

    if not user_id:
        return {
            "statusCode": 400,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "user_id is required"})
        }

    # 2️⃣ Load items from cart
    cart_response = cart_table.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    )

    items = clean_decimal(cart_response.get("Items", []))

    if not items:
        return {
            "statusCode": 400,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "Cart is empty"})
        }

    # 3️⃣ Calculate total
    total = sum(i.get("price", 0) * i.get("qty", 1) for i in items)

    # 4️⃣ Create Order ID
    order_id = str(uuid.uuid4())

    # 5️⃣ Convert for DynamoDB
    items_dynamo = to_decimal(items)
    total_dynamo = Decimal(str(total))

    # 6️⃣ Save order
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

    # 7️⃣ Clear cart after order
    for item in items:
        cart_table.delete_item(
            Key={"user_id": user_id, "item_id": item["item_id"]}
        )

    # 8️⃣ SNS: subscribe or notify customer
    customer_email = customer.get("email")

    if SNS_TOPIC_ARN and customer_email:
        subs = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)
        existing = any(s["Endpoint"] == customer_email
                       for s in subs.get("Subscriptions", []))

        if not existing:
            sns.subscribe(
                TopicArn=SNS_TOPIC_ARN,
                Protocol="email",
                Endpoint=customer_email
            )
        else:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="EasyCart Order Confirmation",
                Message=(
                    f"Your EasyCart order was placed successfully!\n\n"
                    f"Order ID: {order_id}\n"
                    f"Total Amount: €{total:.2f}\n"
                    f"Customer: {customer.get('full_name')}\n\n"
                    f"Thank you for shopping with EasyCart!"
                )
            )

    # 9️⃣ Response to frontend
    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps({
            "message": "Order placed successfully",
            "order_id": order_id
        })
    }
