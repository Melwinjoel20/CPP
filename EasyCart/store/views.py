from django.shortcuts import render
import boto3
from django.conf import settings

# Home / Base view
def base(request):
    return render(request, 'base.html')

def home(request):
    return render(request, 'home.html')


cognito = boto3.client(
    "cognito-idp",
    region_name=settings.COGNITO["region"]
)

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Authenticate using email as username
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            return redirect("base")
        else:
            messages.error(request, "Invalid email or password. Please try again.")

    return render(request, "login.html")

def register(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        name = request.POST.get("name")

        try:
            response = cognito.sign_up(
                ClientId=settings.COGNITO["app_client_id"],
                Username=email,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "name", "Value": name}
                ],
            )

            messages.success(request, "Account created! Please check your email for verification.")
            return redirect("login")

        except cognito.exceptions.UsernameExistsException:
            messages.error(request, "This email already exists.")
        except Exception as e:
            messages.error(request, str(e))

    return render(request, "register.html")