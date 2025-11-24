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
    if isinstance(obj, list):
        return [clean_decimal(i) for i in obj]
    if isinstance(obj, dict):
        return {k: clean_decimal(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def to_decimal(obj):
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
    print("Incoming event:", json.dumps(event))

    method = (
        (event.get("requestContext", {}) or {})
        .get("http", {})
        .get("method")
        or event.get("httpMethod", "")
    ).upper()

    # 0️⃣ CORS preflight
    if method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": _cors_headers(),
            "body": ""
        }

    # -------------------------------
    # 🔥 SECURE USER FROM JWT
    # -------------------------------
    auth = event.get("requestContext", {}).get("authorizer", {})
    claims = auth.get("jwt", {}).get("claims", {}) or auth.get("claims", {})

    # ✔ REAL USER ID fetched ONLY from JWT
    user_id = claims.get("email") or claims.get("cognito:username")

    if not user_id:
        return {
            "statusCode": 401,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "Unauthorized: Please log in"})
        }
    # -------------------------------

    # 1️⃣ Parse body
    body_str = event.get("body") or "{}"
    try:
        body = json.loads(body_str)
    except:
        body = {}

    customer = body.get("customer") or {}
    payment_method = body.get("payment_method", "card")

    # 2️⃣ Load cart items
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

    # 4️⃣ Order ID
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

    # 7️⃣ Clear cart
    for item in items:
        cart_table.delete_item(
            Key={"user_id": user_id, "item_id": item["item_id"]}
        )

    # 8️⃣ SNS notify
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

    return {
        "statusCode": 200,
        "headers": _cors_headers(),
        "body": json.dumps({
            "message": "Order placed successfully",
            "order_id": order_id
        })
    }
