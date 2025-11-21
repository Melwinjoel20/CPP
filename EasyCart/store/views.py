import boto3
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages
from easycart_rate_limiter import check_rate_limit

# Home / Base view
def base(request):
    return render(request, 'base.html')

def home(request):
    
    return render(request, 'home.html')


cognito = boto3.client(
    "cognito-idp",
    region_name=settings.COGNITO["region"]
)

def clear_messages(request):
    storage = get_messages(request)
    for _ in storage:
        pass

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email").strip()
        password = request.POST.get("password").strip()
        
        key = f"login:{email}"   # per-user rate limit

        allowed = check_rate_limit(
            key,
            limit=settings.RATE_LIMIT_LOGIN_LIMIT,
            window=settings.RATE_LIMIT_LOGIN_WINDOW
        )

        if not allowed:
            messages.error(
                request,
                "Too many failed login attempts. Try again in 1 minute."
            )
            return redirect("login")


        client = boto3.client("cognito-idp", region_name=settings.COGNITO["region"])

        # Try normal authentication
        try:
            auth_response = client.admin_initiate_auth(
                UserPoolId=settings.COGNITO["user_pool_id"],
                ClientId=settings.COGNITO["app_client_id"],
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password
                }
            )

        except client.exceptions.NotAuthorizedException:
            messages.error(request, "Incorrect email or password.")
            return redirect("login")

        except client.exceptions.UserNotFoundException:
            messages.error(request, "No account found with this email.")
            return redirect("login")

        except client.exceptions.UserNotConfirmedException:
            # ❗ This happens even with correct password in DEV environments
            if settings.DEV_MODE:
                messages.warning(request, "Email verification skipped (DEV mode).")

                # Try AGAIN – if password is wrong, this WILL fail
                try:
                    auth_response = client.admin_initiate_auth(
                        UserPoolId=settings.COGNITO["user_pool_id"],
                        ClientId=settings.COGNITO["app_client_id"],
                        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                        AuthParameters={
                            "USERNAME": email,
                            "PASSWORD": password
                        }
                    )
                except:
                    messages.error(request, "Incorrect email or password.")
                    return redirect("login")

            else:
                messages.error(request, "Please verify your email before logging in.")
                return redirect("login")

        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return redirect("login")

        # 🎉 If we reach here → password is 100% correct

        # Fetch user details
        user = client.admin_get_user(
            UserPoolId=settings.COGNITO["user_pool_id"],
            Username=email
        )

        full_name = None
        for attr in user["UserAttributes"]:
            if attr["Name"] == "name":
                full_name = attr["Value"]

        # Save session
        request.session["user_email"] = email
        request.session["user_name"] = full_name
        request.session["user_id"] = email  


        # PROD MODE ONLY: verify email
        if not settings.DEV_MODE:
            for attr in user["UserAttributes"]:
                if attr["Name"] == "email_verified" and attr["Value"] == "false":
                    messages.error(request, "Please verify your email before logging in.")
                    return redirect("login")

        messages.success(request, f"Welcome, {full_name}!")
        return redirect("home")

    return render(request, "login.html")



def logout_view(request):
    request.session.flush()
    clear_messages(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")
    
def register(request):
    if request.method == "POST":
        name = request.POST.get("name").strip()
        email = request.POST.get("email").strip()
        password = request.POST.get("password")

        client = boto3.client("cognito-idp", region_name=settings.COGNITO["region"])

        try:
            # Sign up
            client.sign_up(
                ClientId=settings.COGNITO["app_client_id"],
                Username=email,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "name", "Value": name},
                ]
            )

            # DEV MODE → AUTO CONFIRM USER
            if settings.DEV_MODE:
                try:
                    client.admin_confirm_sign_up(
                        UserPoolId=settings.COGNITO["user_pool_id"],
                        Username=email
                    )
                    messages.success(request, "Account created (DEV MODE AUTO-CONFIRMED). You can now login.")
                except Exception as e:
                    messages.warning(request, f"Auto-confirm skipped: {e}")
            else:
                messages.success(request, "Account created! Please check your email to verify your account.")

            return redirect("login")

        except client.exceptions.UsernameExistsException:
            messages.error(request, "This email already exists.")
            return redirect("register")

        except client.exceptions.InvalidPasswordException:
            messages.error(request, "Password must contain uppercase, lowercase, number, and symbol.")
            return redirect("register")

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect("register")

    return render(request, "register.html")
    

def get_all_categories():
    return ["Phones", "Laptops", "Accessories"]  # Can be replaced with auto-detection later


def generate_presigned_image(key):
    s3 = boto3.client("s3", region_name=settings.S3_REGION)
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=3600  # 1 hour
    )




def generate_presigned_image_url(key: str):
    s3 = boto3.client("s3", region_name=settings.S3_REGION)

    try:
        return s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": settings.S3_BUCKET, "Key": key},
            ExpiresIn=3600,   # 1 hour
        )
    except Exception as e:
        print("Error generating image URL:", e)
        return None


def products(request, category=None):
    categories = get_all_categories()  
    # Example: ["Accessories", "Laptops", "Phones"]

    # ---------------------------
    # 🔍 SEARCH LOGIC (NEW PART)
    # ---------------------------
    search = request.GET.get("search", "").strip().lower()

    if search:
        keyword_map = {
            "Accessories": ["accessory", "accessories", "earphone", "earphones", "headphones", "charger"],
            "Laptops": ["laptop", "laptops", "notebook", "macbook"],
            "Phones": ["phone", "phones", "mobile", "smartphone"],
        }

        matched_category = None

        for table_name, words in keyword_map.items():
            if any(w in search for w in words):
                matched_category = table_name
                break

        # If search matched → override the category and load that table
        if matched_category:
            category = matched_category
        else:
            category = None   # show ALL products

    # ---------------------------
    # EXISTING CODE CONTINUES
    # ---------------------------

    dynamodb = boto3.resource("dynamodb", region_name=settings.COGNITO["region"])
    items = []

    if category:
        if category not in categories:
            messages.error(request, "Invalid category selected.")
            return redirect("products")

        table = dynamodb.Table(category)
        response = table.scan()
        items = response.get("Items", [])
    else:
        for cat in categories:
            table = dynamodb.Table(cat)
            response = table.scan()
            items.extend(response.get("Items", []))

    for item in items:
        key = item.get("image")
        item["image_url"] = generate_presigned_image_url(key) if key else None

    lambda_cfg = settings.COGNITO["lambda_cart_endpoints"]

    return render(request, "products.html", {
        "products": items,
        "category": category,
        "categories": categories,
        "ADD_TO_CART_URL": lambda_cfg["add_to_cart"],
        "VIEW_CART_URL": lambda_cfg["view_cart"],
        "REMOVE_ITEM_URL": lambda_cfg["remove_cart_item"],
    })

def view_cart(request):
    lambda_cfg = settings.COGNITO["lambda_cart_endpoints"]

    return render(request, "view_cart.html", {
        "VIEW_CART_URL": lambda_cfg["view_cart"],
        "REMOVE_ITEM_URL": lambda_cfg["remove_cart_item"],
    })

def checkout(request):
    lambda_cfg = settings.COGNITO["lambda_cart_endpoints"]

    return render(request, "checkout.html", {
        "VIEW_CART_URL": lambda_cfg["view_cart"],
        "PLACE_ORDER_URL": lambda_cfg["place_order"],
    })

def order_confirmation(request):
    order_id = request.GET.get("id")

    return render(request, "order_confirmation.html", {
        "order_id": order_id
    })


