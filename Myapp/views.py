

from .serializers import *
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from datetime import datetime
from django.utils import timezone
from .models import *


class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request,*args, **kwargs):
        serializers = TokenRefreshSerializer(data = request.data)
        serializers.is_valid(raise_exception= True)

        new_token = serializers.validated_data['access']

        return Response({
            'token': new_token
        }, status= status.HTTP_200_OK)

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        passward = request.data.get('password')
        user = authenticate(request, username=username, password=passward)
        
        if user is not None:
            token = RefreshToken.for_user(user)

            return Response ({
            'id':user.id,
            'username':user.username,
            'email':user.email,
            'token':str(token.access_token  ) 
        }, status = status.HTTP_200_OK)
        
        else:
            return Response({'error':'Compte non trouvé ou identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request,*args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            return Response({
                'id':user.id,
                'username': user.username,
                'email': user.email,
                
                'message':'User created successfully'
            }, status = status.HTTP_201_CREATED )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class UserView(generics.ListAPIView):
     queryset =  User.objects.all()
     serializer_class = UserViewSerializer
      
class CategoryView(generics.ListAPIView):
    queryset= Category.objects.all()
    serializer_class = CategoryViewSerializer    

class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class =  ProductCreateSerializer
    permission_classes = [IsAuthenticated]

class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
       queryset = Product.objects.all()
       user_id =  self.request.query_params.get('user_created', None)

       if user_id is not None:
           queryset = queryset.filter(user_created = user_id)
           return queryset


class ProductDetailView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        partial = True
        return self.update(request, *args, **kwargs)
    
    def delete( self, request, *args, **kwargs):
        instance =self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreateInvoiceView(generics.CreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

class InvoiceView(generics.ListAPIView):
    
    serializer_class = InvoicesViewSerializer   

    def get_queryset(self):
        queryset = Invoice.objects.all()
        cashier_id = self.request.query_params.get('cashier')

        if cashier_id is not None :
            queryset = queryset.filter(cashier=cashier_id)

        date_str = self.request.query_params.get('created_at')

        if date_str is not None:
            try:
                date = timezone.make_aware(datetime.strptime(date_str,'%Y-%m-%d'))
                stard_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(created_at__range=(stard_of_day, end_of_day))

            except ValueError:
                print('Invalid date format provided', date_str)
        return queryset
    