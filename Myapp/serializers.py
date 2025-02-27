from rest_framework import serializers
from  django.contrib.auth.models import User # type: ignore
from .models import *


class UserSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = User
        fields = ['id','username','email','password']
        extra_kwargs = {'password':{'write_only':True}}

    def create(self, validated_data):
       
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

     
        return user  
    
    
class UserViewSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source = 'userprofile.phone_number',read_only = True)
    class Meta:
        model = User
        fields = ['id','username','email', 'date_joined','phone_number']  


class CategoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id','name','user_created']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id','name','price','puchase_price','stock','category','user_created','created_at']
        extra_kwargs = {
            'puchase_price':{'required':True}
        }
class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'name',
            'price',
            'puchase_price',
            'stock',
            'category',
            'user_created',
        ]        

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Invoice
        fields = [
            'client_name',
            'total_amount',
            'change',
            'cashier'
        ]

class InvoicesViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'id',
            'client_name',
            'total_amount',
            'change',
            'cashier',
            'created_at'
        ]
     