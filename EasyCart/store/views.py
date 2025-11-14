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
    # Always clear previous messages when entering login page
    clear_messages(request)
    
    if request.method == "POST":
        email = request.POST.get("email").strip()
        password = request.POST.get("password").strip()

        client = boto3.client("cognito-idp", region_name=settings.COGNITO["region"])

        try:
            # Attempt authentication
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
            # EVEN IF EMAIL IS NOT VERIFIED — we still fetch name and log in
            messages.warning(request, "Email verification skipped (DEV mode).")
            pass  # continue the flow

        except Exception as e:
            messages.error(request, f"Login failed: {str(e)}")
            return redirect("login")

        # -------------------------------------------------------
        # FETCH USER DETAILS (ALWAYS)
        # -------------------------------------------------------
        user_details = client.admin_get_user(
            UserPoolId=settings.COGNITO["user_pool_id"],
            Username=email
        )

        full_name = email  # fallback
        for attr in user_details["UserAttributes"]:
            if attr["Name"] == "name":
                full_name = attr["Value"]

        # -------------------------------------------------------
        # SAVE SESSION (ALWAYS)
        # -------------------------------------------------------
        request.session["user_email"] = email
        request.session["user_name"] = full_name

        # -------------------------------------------------------
        # EMAIL VERIFICATION CHECK (DISABLED IN DEV LAB)
        # -------------------------------------------------------
        # for attr in user_details["UserAttributes"]:
        #     if attr["Name"] == "email_verified" and attr["Value"] == "false":
        #         messages.error(request, "Please verify your email before logging in.")
        #         return redirect("login")

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
            # Try to sign up user
            response = client.sign_up(
                ClientId=settings.COGNITO["app_client_id"],
                Username=email,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "name", "Value": name},
                ]
            )

            # In Learner Lab email won't come, but this is OK
            messages.success(
                request,
                "Account created! Please check your email for verification. "
            )
            return redirect("login")

        except client.exceptions.UsernameExistsException:
            messages.error(request, "This email is already registered.")
            return render(request, "register.html")

        except client.exceptions.InvalidPasswordException as e:
            messages.error(request,
                "Password must contain uppercase, lowercase, digit, and a symbol."
            )
            return render(request, "register.html")

        except Exception as e:
            # SES email limit will cause error -> show friendly message
            if "ses" in str(e).lower() or "email" in str(e).lower():
                messages.warning(
                    request,
                    "Account created, but verification email could not be delivered. "
                )
                return redirect("login")

            messages.error(request, f"Error: {str(e)}")
            return render(request, "register.html")

    return render(request, "register.html")

