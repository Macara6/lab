from rest_framework import serializers
from  django.contrib.auth.models import User # type: ignore
from .models import *


class UserSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = User
        fields = ['id','username','email','password','date_joined']
        extra_kwargs = {
            'password':{'write_only':True},
            'date_joined': {'read_only': True}
            }

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
            'puchase_price':{'required':True},
            'created_at':{'required':True}
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

class UserProfilViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'user',
            'entrep_name',
            'phone_number',
            'adress',
            'rccm_number',
            'impot_number',
        ]  

class SubsriptionSerialize(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            'user',
            'subscription_type',
            'amount',
            'start_date',
            'end_date',
            'is_active'
        ]
 #afficher les details de du bon de sortie        
class CashOutDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashOutDetail
        fields = ['id','reason', 'amount']


class CashOutSerializer(serializers.ModelSerializer): 
    class Meta:
        model = CashOut
        fields =['id','user','created_at','motif','total_amount']

class CashOutDatailCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashOutDetail
        fields = ['reason', 'amount']

class CashOutDetailReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashOutDetail
        fields = ['id', 'reason', 'amount']

class UserCashOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']        

class CashOutCreateSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), write_only=True, source='user'
    )
    
    details = serializers.SerializerMethodField(read_only=True)
    
    detail_inputs = CashOutDatailCreateSerializer(many=True, write_only=True, source='details')
    
    class Meta:
        model = CashOut
        fields = ['user_id', 'motif', 'total_amount', 'details', 'detail_inputs']
    
    def get_details(self, obj):
        return CashOutDetailReadSerializer(obj.details.all(), many=True).data

    def create(self, validated_data):
        details_data = validated_data.pop('details', [])
        cashout = CashOut.objects.create(**validated_data)
        for detail in details_data:
            CashOutDetail.objects.create(cashout=cashout, **detail)
        return cashout

