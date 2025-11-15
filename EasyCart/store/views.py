import boto3
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.messages import get_messages

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


