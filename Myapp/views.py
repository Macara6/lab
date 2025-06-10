



from .serializers import *
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics, permissions
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.generics import UpdateAPIView

from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

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
            if user.is_superuser:

                token = RefreshToken.for_user(user)
                return Response({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'token': str(token.access_token),
                    'is_superuser': user.is_superuser
                }, status=status.HTTP_200_OK)

            try:
                subsription =  Subscription.objects.get(user=user)

                print(f"Abonnement de {user.username}")
                print(f"Heur de debut d'abonnement {subsription.start_date}")
                print(f"Date de fin d'abonnement {subsription.end_date}")
                print(f"Heur actuel {timezone.now()}")

                if subsription.is_expired():
                    print("L'abonnement est expirer")
                    return Response({'error':'Votre abonnement a expiré. Veuillez renouveler'},status= status.HTTP_401_UNAUTHORIZED)
                else:
                    print("Abonnement toujour actif") 
            except Subscription.DoesNotExist:
                return Response({'error':'aucun abonnement trouver pour cet utilisateur'},status= status.HTTP_400_BAD_REQUEST) 
               
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

class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
@method_decorator(csrf_exempt, name='dispatch')
class UpdatUserVieuw(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'user__id'  # ou 'pk' selon ton usage

    def get_queryset(self):
        if (self.request.user.is_superuser):
           return User.objects.all() 
        return User.objects.filter(id=self.kwargs['user__id'])
    def perform_update(self, serializer):
     serializer.save()# ou self.kwargs['pk']



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
    
#APi pour user profil 
class UserProfilView(generics.ListAPIView):
        serializer_class = UserProfilViewSerializer
        def get_queryset(self):
            querset = UserProfile.objects.all()
            user_id = self.request.query_params.get('user')
            if user_id is not None:
                querset = querset.filter(user= user_id)
                return querset
            
#API pour la modification du profil
class UserProfilUpdateView(generics.UpdateAPIView):
     queryset = UserProfile.objects.all()
     serializer_class = UserProfilViewSerializer
     permission_classes = [IsAuthenticated]

     def get_object(self):
        user_profil = UserProfile.objects.get(user = self.queryset.user)
        return  user_profil

     def perform_update(self, serializer):
        serializer.save(user = self.request.user)
#fin de la fonction            

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

#API  pour l'historique de vente pour l'application  flutter 
class UserSalesHistoryView(generics.ListAPIView):
    serializer_class = InvoicesViewSerializer
    def get_queryset(self):
        queryset = Invoice.objects.all()
        cashier_id = self.request.query_params.get('cashier')
        if cashier_id:
            queryset = queryset.filter(cashier= cashier_id).order_by('-created_at')
            
            return queryset 
        return Invoice.objects.none()
#fin de l'API

class CreateSubsriptionView(generics.CreateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubsriptionSerialize
    permission_classes = [IsAuthenticated]

class SubscriptionByUserView(generics.RetrieveAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubsriptionSerialize
    lookup_field = 'user__id'


class UpdateSubscriptionView(generics.UpdateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubsriptionSerialize
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'user__id'

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Subscription.objects.all()
        return Subscription.objects.filter(user= self.request.user)
    def perform_update(self, serializer):
        subscription = serializer.save()
        
        if subscription.end_date > timezone.now():
            subscription.is_active =True
            subscription.save()

class ReactivateSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            subscription = Subscription.objects.get(user__id =user_id)

            if subscription.end_date < timezone.now():
                subscription.end_date = timezone.now() + timedelta(days=30)
                subscription.is_active = True
                subscription.save()
        
                #envoi sms
                user = subscription.user
                if user.email:
                     message = (
                        f"Bonjour {user.username},\n\n"
                        f"Votre abonnement a été réactivé jusqu'au {subscription.end_date.strftime('%d/%m/%Y')}.\n"
                        f"Type d'abonnement {subscription.subscription_type} de {subscription.amount} $/mois.\n"
                        f"conctatez nous sur bilatech@bilatech.org si il y'a un problème\n"
                        
                        f"Merci pour votre fidélité."
                    )
                    
                     send_mail(
                        subject="Réactivation de votre abonnement Bilatech Solution",
                        message=message,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
    
                serializer = SubsriptionSerialize(subscription)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({"detail": "L'abonnement est encore actif."}, status=status.HTTP_400_BAD_REQUEST)
        except Subscription.DoesNotExist:
            return Response({"detail": "Abonnement introuvable."}, status=status.HTTP_404_NOT_FOUND)


class ListSubscriptionView(generics.ListAPIView):
        queryset = Subscription.objects.all()
        serializer_class = SubsriptionSerialize

class CashOutView(generics.ListAPIView):
        serializer_class = CashOutSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            queryset = CashOut.objects.all().order_by('-created_at')
            user_id = self.request.query_params.get('user')

            if user_id:
                queryset = queryset.filter(user__id =user_id)
            return queryset
        
class CashOutDetailView(generics.ListAPIView):
    serializer_class = CashOutDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        cashout_id = self.request.query_params.get('cashout')

        if cashout_id:
            return CashOutDetail.objects.filter(cashout__id = cashout_id)
        
        return  CashOutDetail.objects.none()

class CreateCashOutView(generics.CreateAPIView):
    queryset = CashOut.objects.all()
    serializer_class = CashOutCreateSerializer
    permission_classes = [IsAuthenticated]
