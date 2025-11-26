from decimal import Decimal
import boto3
import uuid
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from .views import admin_required


# ------------------------------------------------------------
# ADMIN DASHBOARD
# ------------------------------------------------------------
@admin_required
def admin_dashboard(request):
    return render(request, "admin/admin_dashboard.html")


# ------------------------------------------------------------
# HELPER: UPLOAD TO S3  (NOT A VIEW → NO DECORATOR)
# ------------------------------------------------------------
def upload_product_image_to_s3(file_obj):
    """
    Uploads an uploaded file object to S3 and returns the S3 key.
    """
    s3 = boto3.client("s3", region_name=settings.S3_REGION)

    ext = file_obj.name.split(".")[-1]
    unique_name = f"product-images/{uuid.uuid4()}.{ext}"

    try:
        s3.upload_fileobj(
            file_obj,
            settings.S3_BUCKET,
            unique_name,
            ExtraArgs={"ContentType": file_obj.content_type}
        )
        return unique_name
    except Exception as e:
        print("Upload error:", e)
        return None


# ------------------------------------------------------------
# ADD PRODUCT
# ------------------------------------------------------------
@admin_required
@admin_required
def admin_add_product(request):
    if request.method == "POST":
        category = request.POST.get("category")
        name = request.POST.get("name")
        description = request.POST.get("description")
        price = Decimal(request.POST.get("price"))

        # MUST MATCH EXACT HTML FIELD NAME
        image_file = request.FILES.get("image_file")

        if not image_file:
            messages.error(request, "Please upload an image.")
            return redirect("admin_add_product")

        # Upload image to S3
        s3_key = upload_product_image_to_s3(image_file)
        if not s3_key:
            messages.error(request, "Failed to upload image to S3.")
            return redirect("admin_add_product")

        # Save product in DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name=settings.S3_REGION)
        table = dynamodb.Table(category)

        pid = str(uuid.uuid4())

        table.put_item(
            Item={
                "product_id": pid,
                "name": name,
                "description": description,
                "price": price,
                "image": s3_key
            }
        )

        messages.success(request, "Product added successfully!")
        return redirect("admin_dashboard")

    return render(request, "admin/add_product.html")

@admin_required
def admin_manage_products(request):
    dynamodb = boto3.resource("dynamodb", region_name=settings.S3_REGION)
    categories = ["Phones", "Laptops", "Accessories"]

    products = []

    for cat in categories:
        table = dynamodb.Table(cat)
        res = table.scan().get("Items", [])

        for item in res:
            item["category"] = cat  # keep track
            products.append(item)

    return render(request, "admin/manage_products.html", {"products": products})
    
@admin_required
def admin_delete_product(request, category, product_id):
    dynamodb = boto3.resource("dynamodb", region_name=settings.S3_REGION)
    table = dynamodb.Table(category)

    # 1️⃣ First fetch the product so we know the S3 key
    try:
        res = table.get_item(Key={"product_id": product_id})
        item = res.get("Item")
        
        if not item:
            messages.error(request, "Product not found.")
            return redirect("admin_manage_products")

        image_key = item.get("image")

    except Exception as e:
        print("Error fetching item:", e)
        messages.error(request, "Failed to fetch product.")
        return redirect("admin_manage_products")

    # 2️⃣ Delete image from S3
    if image_key:
        try:
            s3 = boto3.client("s3", region_name=settings.S3_REGION)
            s3.delete_object(Bucket=settings.S3_BUCKET, Key=image_key)
            print(f"✔ Deleted S3 Image: {image_key}")
        except Exception as e:
            print("S3 delete failed:", e)
            messages.warning(request, "Product deleted, but image could not be removed.")

    # 3️⃣ Delete product from DynamoDB
    try:
        table.delete_item(Key={"product_id": product_id})
        messages.success(request, "Product removed successfully!")
    except Exception as e:
        print("Dynamo delete failed:", e)
        messages.error(request, "Failed to delete product from database.")

    return redirect("admin_manage_products")

