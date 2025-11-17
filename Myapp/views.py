


import random
from django.shortcuts import get_object_or_404
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
from rest_framework.generics import RetrieveDestroyAPIView
from django.template import loader
from django.http import HttpResponse
from django.db.models import F, Sum, ExpressionWrapper, FloatField

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.generics import UpdateAPIView

from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
User = get_user_model()

from .models import *


def test_sentry(request):
    division = 1 / 0  # provoque une erreur
    return HttpResponse("OK")

def index(request):
    template = loader.get_template("base.html")
    return HttpResponse(template.render({}, request))

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
        password = request.data.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is  None:
             return Response({'error': 'Compte non trouvé ou identifiants invalides'}, status=status.HTTP_401_UNAUTHORIZED)
        
        #Superutilisateur : accès directe
        if user.is_superuser:
            token = RefreshToken.for_user(user)
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'token': str(token.access_token),
                'is_superuser': user.is_superuser
            }, status=status.HTTP_200_OK)
            
         #utilisateur creer par un simple utilisateur: verification de l'abonnement du parent 
        if user.created_by and not user.created_by.is_superuser:
            try:
                parent_subscription = Subscription.objects.get(user=user.created_by)
                if parent_subscription.is_expired():
                    return Response({'error': "L'abonnement de votre administrateur a expiré."}, status=status.HTTP_401_UNAUTHORIZED)
            except Subscription.DoesNotExist:
                    return Response({'error': "Votre administrateur n'a pas d'abonnement actif."}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Utilisateur créé par superuser → vérifier abonnement personnel
        elif user.created_by and user.created_by.is_superuser:   
            try:
                subscription = Subscription.objects.get(user = user)
                
                if subscription.is_expired():
                     return Response({'error': 'Votre abonnement a expiré. Veuillez renouveler.'}, status=status.HTTP_401_UNAUTHORIZED)
            except Subscription.DoesNotExist:
                return Response({'error': 'Aucun abonnement trouvé pour cet utilisateur.'}, status=status.HTTP_400_BAD_REQUEST)
   
               
        token = RefreshToken.for_user(user)

        return Response ({
            'id':user.id,
            'username':user.username,
            'email':user.email,
            'token':str(token.access_token  ) 
        }, status = status.HTTP_200_OK)
        



class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request,*args, **kwargs):
        current_user =request.user

        if not current_user.is_superuser:
            try:
                parent_subscription = Subscription.objects.get(user=current_user)
                if parent_subscription.is_expired():
                     return Response({'detail': "Votre abonnement a expiré."}, status=status.HTTP_403_FORBIDDEN)
            except Subscription.DoesNotExist:
                return Response({'detail': 'Aucun abonnement trouvé.'}, status=status.HTTP_403_FORBIDDEN)
        #pour le sur utilisateur 
        if current_user.is_superuser:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                user.created_by = current_user
                user.save()
                return Response({
                    'id':user.id,
                    'username': user.username,
                    'email': user.email,
                    'message':'User created successfully'
                }, status = status.HTTP_201_CREATED )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        try:
            subscription =Subscription.objects.get(user = current_user)
        except Subscription.DoesNotExist:
            return Response({'detail': 'Aucun abonnement trouvé.'}, status=status.HTTP_400_BAD_REQUEST)
        
        subscription_limits ={

            'PREMIUM': 3,
            'MEDIUM': 2,
            'BASIC': 0
        }

        limit = subscription_limits.get(subscription.subscription_type.upper(),0)
        created_users_count = User.objects.filter(created_by = current_user).count()

        if created_users_count >= limit:
            return Response({
                'detail': f"Limite atteinte. Votre abonnement {subscription.subscription_type} permet de créer {limit} utilisateur(s)."
            }, status=status.HTTP_403_FORBIDDEN)
        
        #creation de l'utilisateur 
        serializer = self.get_serializer(data = request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.created_by = current_user
            user.is_active=True
            user.save()

            return Response({
                'id':user.id,
                'username': user.username,
                'email': user.email,
                'message': 'Utilisateur créé avec succès'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UsersCreatedByMeView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(created_by=self.request.user)


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

 #fonction pour supprimer l'utilisateur     
class DeleteUserView(RetrieveDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field ='id'

#fonction pour changer le mot de passe 
class ChangePasswordView(generics.UpdateAPIView):
     serializer_class = ChangePasswordSerialize
     model = User
     permission_classes = [IsAuthenticated]

     def get_object(self, queryset=None):
         return self.request.user
     
     def update(self, request, *args, **kwargs):
         user = self.get_object()
         serializer = self.get_serializer(data=request.data, context={'request': request})

         if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'detail': 'Mot de passe modifié avec succès'}, status=status.HTTP_200_OK)
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
     
#fonction pour modifier l'utilisateur     
class UpdateUserApiView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Retourne l'utilisateur connecté
        return self.request.user
#fonction pour definir le mot de passe secret de l'utilisateur 
class SecretAccessKeyCreateUpdateView(generics.CreateAPIView, generics.UpdateAPIView):
    serializer_class = SecretAccessKeySerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        return SecretAccessKey.objects.filter(user= self.request.user).first()
    
    def post(self, request, *args, **kwargs):
        existing = self.get_object()
        if existing:
            serializer = self.get_serializer(existing, data = request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response({'detail': 'Clé mise à jour avec succès'}, status=status.HTTP_200_OK)
        else:
            serializer = self.get_serializer(data = request.data)
            serializer.is_valid(raise_exception = True)
            self.perform_create(serializer)
            return Response({'detail': 'Clé créée avec succès'}, status=status.HTTP_201_CREATED)

class SecretKeyStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        has_key = SecretAccessKey.objects.filter(user=request.user).exists()
        return Response({'has_key': has_key}) 
    
class VerifySecretKeyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        key = request.data.get("key")
        secret = SecretAccessKey.objects.filter(user=request.user).first()
        if secret and secret.check_key(key):
            return Response({"valid": True})
        return Response({"valid": False})   


class UserView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserViewSerializer
      
class CategoryView(generics.ListAPIView):
    queryset= Category.objects.all()
    serializer_class = CategoryViewSerializer    

class CreateCategoryView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CreateCategorySerializer
    permission_classes = [IsAuthenticated]

class DeleteCategorieView(generics.DestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryViewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

class CategoryByUserView(generics.ListAPIView):
    serializer_class = CategoryViewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return Category.objects.filter(user_created__id=user_id)

#api pour creer le produit
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class =  ProductCreateSerializer
    permission_classes = [IsAuthenticated]

#api pour creer un produit du depôt 
class DepotProductCreate(generics.CreateAPIView):
    queryset = DepotProduct.objects.all()
    serializer_class = DepotProductCreateSerializer
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
        return UserProfile.objects.get(user=self.request.user)

     def perform_update(self, serializer):
        serializer.save(user=self.request.user)
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


class DeleleInvoice(RetrieveDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'



class InvoiceView(generics.ListAPIView):        
    serializer_class = InvoicesViewSerializer   
    permission_classes = [IsAuthenticated]
   
    def get_queryset(self):
        user = self.request.user
        User = get_user_model()
        # Récupérer l'utilisateur et ses enfants
        child_users = User.objects.filter(created_by=user).values_list('id', flat=True)
        only_children = self.request.query_params.get('only_children') == 'true'
        all_user_ids = list(child_users) if only_children else list(child_users) + [user.id]

        queryset = Invoice.objects.filter(cashier__in=all_user_ids).select_related(
            'cashier', 'cashier__userprofile'
        ).prefetch_related('items');

        queryset = queryset.annotate(
            profit_amount = Sum(
              ExpressionWrapper(
                (F('items__price') - F('items__purchase_price')) * F('items__quantity'),
                output_field=FloatField()
              )
            )
        )

        cashier_id = self.request.query_params.get('cashier')

        if cashier_id:
            queryset = queryset.filter(cashier=cashier_id)

        date_str = self.request.query_params.get('created_at')
 
        if date_str:
            try:
                date = timezone.make_aware(datetime.strptime(date_str, '%Y-%m-%d'))
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(created_at__range=(start_of_day, end_of_day))
            except ValueError:
                print('Invalid date format provided', date_str)
        return queryset

class InvoiceDetailView(generics.ListAPIView):
    serializer_class =  InvoiceItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            return InvoiceItem.objects.filter(invoice__id = invoice_id)
        return InvoiceItem.objects.none()

class CancelInvoiceView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, invoice_id):
        invoice = get_object_or_404(Invoice, id = invoice_id)

        if invoice.status == 'ANNULER':
            return Response(
                {"error": "Cette facture est déjà annulée."},
                status=status.HTTP_400_BAD_REQUEST
            )
        invoice.cancel()

        return Response(
            {"message": "Facture annulée et stock restauré."},
            status=status.HTTP_200_OK
        )
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
class CreateProfilView(generics.CreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfilViewSerializer
    permission_classes = [IsAuthenticated]

class CreateSubsriptionView(generics.CreateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerialize
    permission_classes = [IsAuthenticated]

class SubscriptionByUserView(generics.RetrieveAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerialize
    lookup_field = 'user__id'

class SubscriptionByUserAndChildUserView(generics.RetrieveAPIView):

    serializer_class = SubscriptionSerialize
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user_id = self.kwargs['user_id']
        user = get_object_or_404(CustomUser, id=user_id)

        parent_user = getattr(user, 'created_by', None)
        if parent_user and not parent_user.is_superuser:
            subscription_user = parent_user
        else:
            subscription_user = user
        subscription = get_object_or_404(Subscription, user=subscription_user)
        return subscription



class UpdateSubscriptionView(generics.UpdateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerialize
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
                serializer = SubscriptionSerialize(subscription)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response({"detail": "L'abonnement est encore actif."}, status=status.HTTP_400_BAD_REQUEST)
        except Subscription.DoesNotExist:
            return Response({"detail": "Abonnement introuvable."}, status=status.HTTP_404_NOT_FOUND)


class PasswordResetRequestView(APIView):
    permission_classes = []
    def post(self, request):
        serializers = PasswordResetRequestSerializer(data=request.data)
        serializers.is_valid(raise_exception=True)

        email = serializers.validated_data['email']
        user = User.objects.filter(email=email).first()
        
        if not user:
            return Response({"detail": "Un email de réinitialisation a été envoyé si ce compte existe."}, status=status.HTTP_200_OK)
        
        code = str(random.randint(100000,999999))

        PasswordResetToken.objects.filter(user=user).delete()

        token_obj = PasswordResetToken.objects.create(user=user, token=code)

        reset_message = (
            f"Bonjour {user.username},\n\n"
            "Vous avez demandé une réinitialisation de mot de passe.\n"
            "Veuillez utiliser ce code de réinitialisation dans l'application mobile :\n\n"
            f"🔐 Code de réinitialisation : {code}\n\n"
            "Ce code expire dans 1 heure.\n\n"
            "Si vous n'avez pas demandé cette réinitialisation, ignorez ce message."
        )
        send_mail(
            subject="Réinitialisation de votre mot de passe",
            message=reset_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return Response({"detail": "Un email de réinitialisation a été envoyé si ce compte existe."}, status=status.HTTP_200_OK)
    
class PasswordResetConfirmView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            token_obj= PasswordResetToken.objects.get(token = token)
        except PasswordResetToken.DoesNotExist:
             return Response({"detail": "Token invalide."}, status=status.HTTP_400_BAD_REQUEST)
        
        expiration_time = token_obj.created_at + timezone.timedelta(hours=1)

        if timezone.now() > expiration_time:
            return Response({"detail": "Le token a expiré."}, status=status.HTTP_400_BAD_REQUEST)
        user = token_obj.user
        user.password = make_password(new_password)
        user.save()
        token_obj.delete()

        return Response({"detail": "Mot de passe réinitialisé avec succès."}, status=status.HTTP_200_OK)


class ListSubscriptionView(generics.ListAPIView):
        queryset = Subscription.objects.all()
        serializer_class = SubscriptionSerialize

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

class DeleteCashOut(RetrieveDestroyAPIView):
    queryset = CashOut.objects.all()
    serializer_class = CashOutCreateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

#fonction pour creer un bon d'entré
class CreateEntryNoteView(generics.CreateAPIView):
    queryset = EntryNote.objects.all()
    serializer_class = EnteryNoteCreateSerializer
    permission_classes = [IsAuthenticated]  

class EntryNoteViewList(generics.ListAPIView):
    serializer_class = EntryNoteSerialize
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = EntryNote.objects.all().order_by('-created_at')
        user_id = self.request.query_params.get('user')

        if user_id:
            queryset = queryset.filter(user__id=user_id)
        return queryset
        
class EntryDetailView(generics.ListAPIView):
    serializer_class = EnteryNoteDetailReadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entrynote_id = self.request.query_params.get('entrynote')
        if entrynote_id:
            return EntryNoteDetail.objects.filter(entrynote__id= entrynote_id)
        
        return EntryNoteDetail.objects.none()
    
class DeleteEntryNote(RetrieveDestroyAPIView):
    queryset = EntryNote.objects.all()
    serializer_class = EnteryNoteCreateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field ='id'  

   

    