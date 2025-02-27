from django.urls import path
from.views import *

urlpatterns = [
    path('login/',LoginView.as_view(), name='login'),
    path('products/', ProductListView.as_view(), name='products'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('invoices/', CreateInvoiceView.as_view(), name='create-invoice'),
    path('invoicesView/', InvoiceView.as_view(), name='invoices-views' ),
    path('usersView/', UserView.as_view(), name='user-list'),
    path('category/',CategoryView.as_view(), name='category-list'),
    path('productCreate/',ProductCreateView.as_view(), name='product-create'),
    path('userCreate/', UserCreateView.as_view(), name='user-create'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    
]
