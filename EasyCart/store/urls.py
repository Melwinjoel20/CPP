from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
     path('base/',views.base,name="base"),
     path('home/',views.home,name="home"),
     path("register/", views.register, name="register"),
     path("login/", views.login_view, name="login"),
     path("logout/", views.logout_view, name="logout"),
     path("products/", views.products, name="products"),
     path("products/<str:category>/", views.products, name="products"),
     path("cart/", views.view_cart, name="view_cart"),
     path("checkout/", views.checkout, name="checkout")




]