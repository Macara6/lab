from rest_framework import serializers
from django.contrib.auth import get_user_model
User = get_user_model() 
from .models import *


class UserSerializer(serializers.ModelSerializer):
   
    class Meta:
        model = User
        fields = ['id','username','first_name','last_name','email','password','date_joined','is_superuser']
        extra_kwargs = {
            'password':{'write_only':True},
            'date_joined': {'read_only': True}
            }
       
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user  
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id','username','first_name','last_name','email','date_joined']
        read_only_fields = ['id','username']

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()   

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=5)

class UserViewSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source = 'userprofile.phone_number',read_only = True)
    class Meta:
        model = User
        fields = ['id','username','email', 'date_joined','phone_number']  


class CategoryViewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id','name','user_created']


class CreateCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['name','user_created']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id','name','price','purchase_price','stock','category','user_created','created_at']
        extra_kwargs = {
            'puchase_price':{'required':True},
            'created_at':{'required':True}
        }

class ProductCreateSerializer(serializers.ModelSerializer):
    barcode = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    class Meta:
        model = Product
        fields = [
            'name',
            'price',
            'purchase_price',
            'stock',
            'category',
            'user_created',
            'barcode', 
        ]  


class InvoiceItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = InvoiceItem
        fields = ['product','product_name','quantity', 'price','purchase_price']             


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True)
    profit_amount = serializers.SerializerMethodField()
    cashier_name = serializers.CharField(source='user.username', read_only=True)
    cashier_currency = serializers.SerializerMethodField()
    class Meta:
        model =  Invoice
        fields = [
            'client_name',
            'total_amount',
            'amount_paid',
            'change',
            'cashier',
            'cashier_name',
            'cashier_currency', 
            'items',
            'profit_amount'
        ]
    
    def get_profit_amount(self,obj):
        profit =0
        for item in obj.items.all():
            
            profit += (item.price - item.purchase_price) * item.quantity
        return profit
    
    def get_cashier_currency(self, obje):
        try:
            return obje.cashier.userprofil.currency_preference
        except:
            return None

    def create(self,validated_data):
        
        items_data = validated_data.pop('items')
        invoice = Invoice.objects.create(**validated_data)

        for item_data in items_data:
            product = item_data['product']
            quantity = item_data['quantity']

            if product.stock < quantity:
                raise serializers.ValidationError(
                    f"Stock insuffisant pour le produit '{product.name}' (stock: {product.stock}, demandé: {quantity})"
                )
            InvoiceItem.objects.create(invoice=invoice, **item_data)
            product.stock -= quantity
            product.save()
        return invoice

class InvoicesViewSerializer(serializers.ModelSerializer):
    profit_amount = serializers.SerializerMethodField()
    items = InvoiceItemSerializer(many=True, read_only=True)
    cashier_currency = serializers.SerializerMethodField() # Optionnel si tu veux afficher les items
    class Meta:
        model = Invoice
        fields = [
            'id',
            'client_name',
            'total_amount',
            'amount_paid',
            'change',
            'cashier',
            'cashier_currency', 
            'created_at',
            'profit_amount',
            'items',  # Optionnel, à inclure si nécessaire pour l'interface
        ]
    def get_profit_amount(self, obj):
        profit = 0
        for item in obj.items.all():
            profit += (item.price - item.purchase_price) * item.quantity
        return profit
    
    def get_cashier_currency(self, obj):
     try:
        return obj.cashier.userprofile.currency_preference
     except AttributeError:
        return None
     except UserProfile.DoesNotExist:
        return None
#fonction pour le profile
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
            'currency_preference'
        ]  

class SubscriptionSerialize(serializers.ModelSerializer):
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


#les serializer pour le note d'entrée
class EntryNoteSerialize(serializers.ModelSerializer):

    class Meta:
        model = EntryNote
        fields =['id','user','supplier_name','created_at','total_amount']

class EnteryNoteDetailCreateSerializer(serializers.ModelSerializer):

        class Meta:
            model = EntryNoteDetail
            fields = ['reason','amount']

class EnteryNoteDetailReadSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = EntryNoteDetail
            fields = ['id','reason','amount']

class EnteryNoteCreateSerializer(serializers.ModelSerializer):
        user_id = serializers.PrimaryKeyRelatedField(
            queryset = User.objects.all(), write_only=True, source='user'
        )
        details = serializers.SerializerMethodField(read_only=True)
        detail_inputs = EnteryNoteDetailCreateSerializer(many=True, write_only=True, source='details')

        class Meta:
            model = EntryNote
            fields = ['user_id','supplier_name','created_at','total_amount','details','detail_inputs']

        def get_details(self, obj):
                return EnteryNoteDetailReadSerializer(obj.details.all(),many=True).data
            
        def create(self, validated_data):
            details_data = validated_data.pop('details',[])
            entery_note = EntryNote.objects.create(**validated_data)

            for detail in details_data:
                EntryNoteDetail.objects.create(entrynote=entery_note,**detail)
            return entery_note

#fonction pour changer le mot de passe
class ChangePasswordSerialize(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required= True)

    def validate_old_password(self, value):
        user = self.context['request'].user

        if not user.check_password(value):
            raise serializers.ValidationError("l'ancien mot de passe est incorrect.")
        return value
    
    def validate_new_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("Le nouveau mot de passe doit contenir au moins 8 caractères.")
        return value;
#serializer pour definir le code secret de l'utilisateur 

class SecretAccessKeySerializer(serializers.Serializer):
    old_key = serializers.CharField(write_only=True, required=False)
    new_key = serializers.CharField(write_only=True, required = True)

    class Meta:
        model = SecretAccessKey
        fields = ['old_key', 'new_key']

    def update(self, instance,validated_date):
        old_key = validated_date.get('old_key')
        new_key = validated_date.get('new_key')

        if not old_key:
             raise serializers.ValidationError({"old_key": "Ancien code requis pour la mise à jour"})
        if not check_password(old_key,instance.hashed_key):
             raise serializers.ValidationError({"old_key": "Ancien code incorrect"})
        instance.hashed_key =make_password(new_key)
        instance.save()
        return instance

    def create(self, validated_data):
        new_key = validated_data.get('new_key')
        user = self.context['request'].user
       
        return SecretAccessKey.objects.create(
            user = user,
            hashed_key = make_password(new_key)
        )
    
