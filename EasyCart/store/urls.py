from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
     path('base/',views.base,name="base"),
     path('home/',views.base,name="home"),
     path("register/", views.register, name="register"),
     path("login/", views.login_view, name="login"),


]