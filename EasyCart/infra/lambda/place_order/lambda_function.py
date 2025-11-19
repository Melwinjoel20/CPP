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


def lambda_handler(event, context):

    body = json.loads(event["body"])
    user_id = body.get("user_id")
    customer = body.get("customer")
    payment_method = body.get("payment_method", "card")

    # ⬅ 1. Load items from cart
    cart_response = cart_table.scan(
        FilterExpression=Attr("user_id").eq(user_id)
    )

    items = clean_decimal(cart_response.get("Items", []))

    if not items:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Cart is empty"})
        }

    # ⬅ 2. Calculate total
    total = sum(i["price"] * i.get("qty", 1) for i in items)

    # ⬅ 3. Create Order ID
    order_id = str(uuid.uuid4())

    # ⬅ 4. Convert for DynamoDB
    items_dynamo = to_decimal(items)
    total_dynamo = Decimal(str(total))

    # ⬅ 5. Save order
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

    # ⬅ 6. Clear cart after order
    for item in items:
        cart_table.delete_item(
            Key={"user_id": user_id, "item_id": item["item_id"]}
        )

    # ⬅ 7. SNS subscribe customer email if not already subscribed
    customer_email = customer.get("email")

    if SNS_TOPIC_ARN and customer_email:

        # 1. Get all subscriptions for the topic
        subs = sns.list_subscriptions_by_topic(TopicArn=SNS_TOPIC_ARN)

        # 2. Check if the email is already subscribed
        existing = False
        for s in subs.get("Subscriptions", []):
            if s["Endpoint"] == customer_email:
                existing = True
                break

        # 3. If NOT subscribed → subscribe automatically
        if not existing:
            sns.subscribe(
                TopicArn=SNS_TOPIC_ARN,
                Protocol="email",
                Endpoint=customer_email
            )

        # 4. If already subscribed → send order email
        if existing:
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


    # ⬅ 8. Return response to frontend
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Order placed successfully",
            "order_id": order_id
        })
    }
