from django.shortcuts import render

# Home / Base view
def base(request):
    return render(request, 'base.html')

def home(request):
    return render(request, 'home.html')
