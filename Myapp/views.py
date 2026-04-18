

from django.db.models import Q
import random
from django.shortcuts import get_object_or_404
from .serializers import *
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics, permissions
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated,AllowAny

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.generics import RetrieveDestroyAPIView
from django.template import loader
from django.http import HttpResponse
from django.db.models import F, Sum, ExpressionWrapper, FloatField
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.generics import UpdateAPIView

from .pdf_utils import build_loyalty_card_pdf
from rest_framework.decorators import api_view, permission_classes

from datetime import datetime, timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
User = get_user_model()

from django.conf import settings
import os 
import json
from .models import *
from django.db import IntegrityError, transaction






def test_sentry(request):
    division = 1 / 0  # provoque une erreur
    return HttpResponse("OK")

def index(request):
    template = loader.get_template("base.html")
    return HttpResponse(template.render({}, request))

@api_view(['GET'])
def generate_loyalty_card_pdf(request, customer_id):
    customer = get_object_or_404(Customer, id = customer_id)
    profile = getattr(customer.created_by, 'userprofile', None)

    pdf = build_loyalty_card_pdf(customer,profile)
    response = HttpResponse(
        pdf,
        content_type ='application/pdf'
    )

    response['Content-Disposition'] = f'attachment; filename="carte_fidelite_{customer.id}.pdf"'
    return response



# view pour la mise à jour l'application 
class CheckAppUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        file_path = os.path.join(
            settings.MEDIA_ROOT,
            'app',
            'version.json'
        )
    
        if not os.path.exists(file_path):
            return Response(
                {"detail":"Aucune mise à jour disponible"},
                status=status.HTTP_404_NOT_FOUND
            )
        with open(file_path, 'r', encoding='utf-8') as f :
            data = json.load(f)
        return Response(data, status=status.HTTP_200_OK)
    

# fonction pour le mise à jour de token 
class CustomTokenRefreshView(TokenRefreshView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request,*args, **kwargs):
        serializers = TokenRefreshSerializer(data = request.data)
        serializers.is_valid(raise_exception= True)

        new_token = serializers.validated_data['access']

        return Response({
            'token': new_token
        }, status= status.HTTP_200_OK)
    

 # view pour la connexion    
class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        remember_me = request.data.get('remember_me',False)
       
        
        # Authentification
        user = authenticate(request, username=username, password=password)
        if not user or user.is_deleted:
            return Response(
                {'error': 'Compte non trouvé ou identifiants invalides'},
                status=status.HTTP_401_UNAUTHORIZED
            )
      
        if remember_me:
            token = RefreshToken.for_user(user)
            access_token = token.access_token
            access_token.set_exp(lifetime = timedelta(days=30))
            
        else:
            token = RefreshToken.for_user(user)
            access_token = token.access_token
            access_token.set_exp(lifetime=timedelta(hours=24))
            
       
        # 2️ Superuser → accès direct
        if user.is_superuser:
            token = RefreshToken.for_user(user)
            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'token': str(access_token),
                'is_superuser': True,
                'status': user.status
            }, status=status.HTTP_200_OK)

        #  Remonter la hiérarchie jusqu’à trouver un abonnement actif
        top_parent, subscription = self.get_top_parent_with_subscription(user)

        if not top_parent:
            return Response(
                {'error': "Aucun abonnement actif trouvé dans la hiérarchie."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 5Retourner les infos de l’utilisateur
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'token': str(access_token),
            'is_superuser': user.is_superuser,
            'status': user.status,
            'parent_id': top_parent.id,
            'parent_status': top_parent.status
        }, status=status.HTTP_200_OK)

    def get_top_parent_with_subscription(self, user):
        """
        Remonte la hiérarchie (parent, grand-parent...) jusqu'à trouver
        un abonnement actif.
        Retourne (top_parent_user, subscription) ou (None, None)
        """
        parent = user
        while parent:
            try:
                subscription = Subscription.objects.get(user=parent)
                if not subscription.is_expired():
                    return parent, subscription
            except Subscription.DoesNotExist:
                pass
            parent = parent.created_by
        return None, None
    
#API pour la deconnexion 
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error":"Refresh Token  requis"}, status=400)
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message":"Déconnexion réussie"}, status=200)
        except Exception:
            return Response({"error":"Token invalide"})
    
#API pour register

class RegisterAccountView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data

        PLAN_PRICES = {
        'BASIC' : 10,
        'MEDIUM': 19,
        'PREMIUM': 30,
        'PLATINUM': 40,
        'DIAMOND': 50,
         }


        if data.get("password") != data.get("confirmPassword"):
            return Response(
               {"detail": "Les mots de passe ne correspondent pas"},
               status=status.HTTP_400_BAD_REQUEST
            )
        
        plan = data.get("plan", "BASIC").upper()

        if plan not in dict(Subscription.SUBSCRIPTION_TYPES):
            return Response(
                {"detail":"Type d'adonnement invalide"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(username = data.get("username")).exists():
            return Response(
                {"detail":"Ce nom d'utilisateur existe déjà"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(email = data.get("email")).exists():
            return Response(
                {"detail":"Cet email est déjà utilisé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if UserProfile.objects.filter(phone_number = data.get("store_phone")).exists():
            return Response(
                {"detail":"Ce numéro de téléphone est déjà utilisé"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create(
                username = data.get('username'),
                email = data.get('email'),
                first_name = data.get('first_name'),
                last_name = data.get('last_name'),
                password = make_password(data.get('password')),
                status = "ADMIN",
                is_register = True
            )

        userProfil = UserProfile.objects.create(
                entrep_name = data.get("store_name"),
                adress = data.get("store_adress"),
                phone_number = data.get("store_phone"),
                currency_preference = data.get("currency"),
                type_of_activity = data.get("business_type"),
                user = user
            )
        
        start_date = timezone.now()
        end_date = start_date + timedelta(days=10)

        subscription = Subscription.objects.create(
                user= user,
                subscription_type = plan,
                amount = PLAN_PRICES[plan],
                start_date = start_date,
                end_date = end_date,
                is_free_frial = True
            )


        return Response({
                "message": "Compte créer avec succèss",
                "triale_ends_at": end_date,
                "subscription": subscription.subscription_type
            }, status=status.HTTP_201_CREATED)
    
        
class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    PERENT_LIMITS = {
            'BASIC':   {'ADMIN': 0, 'CAISSIER':0 , 'GESTIONNAIRE_STOCK':0},
            'MEDIUM':  {'ADMIN':0 , 'CAISSIER':0, 'GESTIONNAIRE_STOCK':0},
            'PREMIUM': {'ADMIN':0, 'CAISSIER':2, 'GESTIONNAIRE_STOCK':1},
            'PLATINUM': {'ADMIN':1, 'CAISSIER':3, 'GESTIONNAIRE_STOCK':3},
            'DIAMOND':  {'ADMIN':4, 'CAISSIER':6, 'GESTIONNAIRE_STOCK':6},
        }
    
    CHILD_ADMIN_LIMITS = {
        'ADMIN': {'ADMIN': 0, 'CAISSIER': 3, 'GESTIONNAIRE_STOCK': 3},
    }


    def post(self, request,*args, **kwargs):
        current_user =request.user

        if current_user.is_superuser:
            return self._create_user(request,current_user)

        if Subscription.objects.filter(user=current_user).exists():
            subscription = Subscription.objects.get(user=current_user)

            if subscription.is_expired():
                return Response({
                    'detail':"Votre abonnement a expiré"
                },status=status.HTTP_403_FORBIDDEN)
            
            limits = self.PERENT_LIMITS[subscription.subscription_type.upper()]
            if current_user.status !='ADMIN':
                return Response({'detaitl':"Vous n'avez pas l'autorisation de créer des utilisateurs"},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            parent = current_user.created_by
            if not parent:
                return Response({'detail':"Vous n'avez pas d'abonnement ni de parent actif?"},
                                status=status.HTTP_403_FORBIDDEN)
            if not parent.is_superuser:
                try:
                    parent_sub =Subscription.objects.get(user=parent)
                    if parent_sub.is_expired():
                        return Response({'detail':"L'abonnement de votre créateur a expiré."},
                                        status=status.HTTP_403_FORBIDDEN)
            
                except Subscription.DoesNotExist:
                    return Response({'detail':"Votre créateur n'a pas d'abonnement actif."},
                             status=status.HTTP_403_FORBIDDEN)
            
            limits =self.CHILD_ADMIN_LIMITS[current_user.status]

            if current_user.status != 'ADMIN':
                return Response({'detail':"Vous n'avez pas l'autorisation de créer des utilisateurs"},
                     status=status.HTTP_403_FORBIDDEN)
        
        requested_role = request.data.get('status',None)
        if requested_role not in ['ADMIN','CAISSIER','GESTIONNAIRE_STOCK']:
            return Response({'detail':"Rôle invalide"}, status=status.HTTP_400_BAD_REQUEST)
        
        is_allowed,max_allowed =self.check_role_limit(current_user,requested_role, )

  

        if not is_allowed:
            return Response({
                'detail':(
                    f"Limite atteinte pour le rôle {requested_role}. "
                    f"Vous pouvez créer {max_allowed} utilisateur(s) de ce type."
               )
            },status=status.HTTP_403_FORBIDDEN)
        
        return self._create_user(request, current_user)

        #creation de l'utilisateur 
    def _create_user(self, request, creator):

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.created_by = creator
            user.is_active = True
            user.save()

            return Response({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'status': user.status,
                'message': "Utilisateur créé avec succès"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def check_role_limit(self, parent_user, requested_role):

        if parent_user.is_superuser:
            max_allowed = None  
        else:
            if Subscription.objects.filter(user=parent_user).exists():
                subscription = Subscription.objects.get(user=parent_user)
                limits = self.PERENT_LIMITS[subscription.subscription_type.upper()]
            else:
                limits = self.CHILD_ADMIN_LIMITS[parent_user.status]

            max_allowed = limits.get(requested_role, 0)
            
        current_count = User.objects.filter(
            created_by=parent_user,
            status=requested_role,
            is_deleted=False
        ).count()

        if max_allowed is not None and current_count >= max_allowed:
            return False, max_allowed

        return True, max_allowed

class UsersCreatedByMeView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.filter(
              Q(created_by = user) | Q(is_register = True),
              is_deleted = False
            )
        return User.objects.filter(created_by=self.request.user, is_deleted = False)
    
class UserCreatedByView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')

        if not user_id:
            return User.objects.none()

        user_id = int(user_id)

        # Enfants directs
        direct_children = User.objects.filter(created_by=user_id, is_deleted=False)

        return list(direct_children) 
    
#API pour recuper les utilisateur 
class UserCretedIdView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')

        if not user_id:
            return User.objects.none()

        try:
            user_id = int(user_id)
        except ValueError:
            return User.objects.none()

        return User.objects.filter(created_by=user_id, is_deleted=False)


    
       
class UserTreeView(APIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        base_user_id = request.query_params.get('base_user_id')

        if not base_user_id:
            return Response({"error": "base_user_id required"}, status=400)

        try:
            base_user_id = int(base_user_id)
        except:
            return Response({"error": "invalid base_user_id"}, status=400)

        ids = self.get_all_user_ids_for_chart(base_user_id)

        return Response({"user_ids": ids})
    
    def get_all_user_ids_for_chart(self,base_user_id):
            
            User = get_user_model()
            descendant_ids = []
            queue = [base_user_id]

            while queue:
                parent_id = queue.pop(0)
                children = list(User.objects.filter(created_by=parent_id, is_deleted=False)
                                .values_list('id', flat=True))
                descendant_ids.extend(children)
                queue.extend(children)

            return [base_user_id] + descendant_ids

class TrashedUsersListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(created_by= self.request.user, is_deleted =True)


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

 #fonction pour supprimer  mettre l'utilisateur dans la corbeille l'utilisateur     
class DeleteUserView(RetrieveDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    lookup_field ='id'

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        if user.is_deleted:
            return Response({"message": "Cet utilisateur est déjà dans la corbeille."}, status=200)
        user.is_deleted =True
        user.deleted_at = now()
        user.permanent_delete_at = now() + timedelta(days=30) 
        user.save()

        return Response({"message": "Utilisateur envoyé dans la corbeille."}, status=200)
    
# fonction pour restaure l'utilisateur 
class RestoreUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            user = User.objects.get(id=id, is_deleted = True)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable dans la corbeille."}, status=404)
        
        parent_user= user.created_by
        requested_role = user.status

        checker = UserCreateView()
        is_allowed, max_allowed =checker.check_role_limit(parent_user,requested_role)

        if not is_allowed:
            return Response({
                "detail": (
                    f"Impossible de restaurer cet utilisateur : "
                    f"la limite pour le rôle {requested_role} est déjà atteinte "
                    f"({max_allowed} maximum)."
                )
            }, status=status.HTTP_403_FORBIDDEN)
        
        user.is_deleted = False
        user.deleted_at = None
        user.save()

        return Response({"message":"utilisateur restaurée avec succès"})

#supprimer directe
class PermanentDeleteUserView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        try:
            user = User.objects.get(id=id, is_deleted = True)
        except User.DoesNotExist:
             return Response({"error": "Utilisateur non trouvé dans la corbeille."}, status=404)
        
        user.delete()
        return Response({"message": "Utilisateur supprimé définitivement."}, status=200)


#object pour crée un nouveau client

class CreateCustomer(generics.CreateAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
#supprimer le client
class DeleteCustomer(RetrieveDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    lookup_field ='id'

# afficher les clients 
class CustomerView(generics.ListAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Customer.objects.none()
        user_created_param = self.request.query_params.get('created_by',None)

        querey_filter = Q()
        
        if user_created_param and user_created_param.isdigit():
            target_user_id = int(user_created_param)
            target_user = User.objects.filter(pk=target_user_id).only('id','status','created_by').first()

            if target_user:
                if target_user.status == User.ADMIN:
                    querey_filter = Q(created_by_id=target_user.id)
                elif target_user.status in [User.CAISSIER, User.GESTIONNAIRE_STOCK] and target_user.created_by_id:
                    querey_filter = Q(created_by_id = target_user.created_by)
                else:
                    return Customer.objects.none()
            else:
                return Customer.objects.none()
        else:
            if user.status == User.ADMIN:
                querey_filter = Q(created_by_id = user.id)
            elif user.status in [User.CAISSIER, User.GESTIONNAIRE_STOCK] and user.created_by:
                querey_filter = Q(created_by = user.created_by_id)
            else:
                return Customer.objects.none()
        return Customer.objects.filter(querey_filter).select_related("created_by").order_by('-created_at')

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
    

    def delete(self, request, *args, **kwargs):
        existing = self.get_object()
        if not existing:
            return Response(
                {'detail':'Aucune clé secrète trouvée.'},
                status=status.HTTP_404_NOT_FOUND
            )
        old_key= request.data.get('old_key')

        if not old_key:
            return Response(
                {'detail':"Veuillez fournir l'acienne  clé secrète."},
                status=status.HTTP_400_BAD_REQUEST
            )

        secrete = SecretAccessKey.objects.filter(user=request.user).first()
        if secrete and secrete.check_key(old_key):
            secrete.delete()

            return Response(
                    {"detail":"Clé supprimer avec succeès"},
                    status=status.HTTP_200_OK
                )
       
        else:
             return Response(
                {"detail":"code incorecte"},
                status=status.HTTP_400_BAD_REQUEST
            )

#API pour verifier l'existance de l'abonnement
class SubsriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        has_sub = Subscription.objects.filter(user = request.user).exists()
        return Response({'has_sub':has_sub})


        
# API pour verifier le status du code secret
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

    def perform_create(self, serializer):
        user = self.request.user
        if user.status =='ADMIN':
            serializer.save(user_created=user)
        elif user.status == 'GESTIONNAIRE_STOCK':
            creator_user = getattr(user, 'created_by',None)
            if creator_user:
                serializer.save(user_created=creator_user)
            else:
                serializer.save(user_created=user)
        else:
            serializer.save(user_created=user)

class DeleteCategorieView(generics.DestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryViewSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

class CategoryByUserView(generics.ListAPIView):
    serializer_class = CategoryViewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_id = self.kwargs.get('user_id')

        if not user or not user.is_authenticated:
            return Category.objects.none()
    
        querey_filter = Q()

        if user_id :
            target_user_id = int(user_id)
            target_user = User.objects.filter(pk=target_user_id).only('id','status','created_by').first()

            if target_user:
                if target_user.status == User.ADMIN:
                    querey_filter = Q(user_created_id=target_user.id)
                elif target_user.status in [User.CAISSIER, User.GESTIONNAIRE_STOCK] and user.created_by_id:
                    querey_filter = Q(user_created_id=user.created_by_id)
                else:
                    return Category.objects.none()
            else:
                return Category.objects.none()
        else:
            if user.status == User.ADMIN:
                querey_filter = Q(user_created_id=user.id)

            elif user.status in [User.CAISSIER, User.GESTIONNAIRE_STOCK] and user.created_by_id:
                 querey_filter = Q(user_created_id = user.created_by_id)
            else:
                return Category.objects.none()
        
        return Category.objects.filter(querey_filter).select_related('user_created')
        



#api pour creer un produit du depôt 
class DepotProductCreate(generics.CreateAPIView):
    queryset = DepotProduct.objects.all()
    serializer_class = DepotProductCreateSerializer
    permission_classes = [IsAuthenticated]  


    
#APi pour user profil 
class UserProfilView(generics.ListAPIView):
        serializer_class = UserProfilViewSerializer
        permission_classes = [IsAuthenticated]

        def get_queryset(self):
            request_user = self.request.user

            if not request_user or not request_user.is_authenticated:
                return UserProfile.objects.none()
            
            user_created_parma = self.request.query_params.get('user')

            if user_created_parma:
                try:
                    target_user = User.objects.get(pk=int(user_created_parma))
                except (User.DoesNotExist, ValueError):
                    return UserProfile.objects.none()
            else:
                target_user = request_user
            if target_user.status == User.ADMIN:
                return UserProfile.objects.filter(user=target_user)
            if target_user.status == User.CAISSIER or target_user.status == User.GESTIONNAIRE_STOCK:

                if target_user.created_by:
                    return UserProfile.objects.filter(user=target_user.created_by)
                return UserProfile.objects.none()
            
            return UserProfile.objects.none()
            
            
            
#API pour la modification du profil
class UserProfilUpdateView(generics.UpdateAPIView):
     queryset = UserProfile.objects.all()
     serializer_class = UserProfilViewSerializer
     permission_classes = [IsAuthenticated]

     def get_object(self):
        user_id = self.request.data.get("user")
        return UserProfile.objects.get(user__id=user_id)

     def perform_update(self, serializer):
       
        serializer.save()
#fin de la fonction            

#api pour creer le produit
class ProductCreateView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class =  ProductCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user

        if user.status == 'ADMIN':
            serializer.save(user_created=user)

        elif user.status =='GESTIONNAIRE_STOCK':
            creator_user = getattr(user, 'created_by', None)
            if creator_user:
                serializer.save(user_created=creator_user)
            else:
                serializer.save(user_created=user)
        else:
            serializer.save(user_created=user)



class ProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]   # Empeche AnonymousUser

    def get_queryset(self):
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return Product.objects.none()

        user_created_param = self.request.query_params.get('user_created', None)

        querey_filter = Q()

        if user_created_param and user_created_param.isdigit():
            target_user_id = int(user_created_param)
            
            target_user = User.objects.filter(pk=target_user_id).only('id','status', 'created_by').first()

            if target_user:
                if target_user.status == User.ADMIN:
                    querey_filter = Q(user_created_id=target_user.id)
                elif target_user.status in [User.CAISSIER , User.GESTIONNAIRE_STOCK] and target_user.created_by_id:
                    querey_filter = Q(user_created_id = target_user.created_by)
                else:
                    return Product.objects.none()
            else:
                return Product.objects.none()
        else:

            if user.status == User.DAMIN:
                querey_filter = Q(user_creted_id=user.id)
            elif user.status in [User.CAISSIER, User.GESTIONNAIRE_STOCK] and user.created_by_id:
                querey_filter = Q(user_created_id=user.created_by_id)
            else:
                return Product.objects.none()
            
        # Par défaut : rien
        return Product.objects.filter(querey_filter).select_related('user_created').order_by('-created_at')
       
    

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
    
# views pour ajout stock
class AddStockView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error" :"Produit introuvable"}, status=status.HTTP_404_NOT_FOUND)
        quantity = request.data.get("quantity",None)
        motif = request.data.get("motif", None)
        
        if quantity  is None:
             return Response({"error": "Le champ 'quantity' est requis."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = int(quantity)
        except:
            return Response({"error": "La quantité doit être un nombre."}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({"error": "La quantité doit être positive."}, status=status.HTTP_400_BAD_REQUEST)
        product.add_stock(quantity, motif,request.user)
        
        return Response({
            "message": "Stock ajouté avec succès",
            "product_id": product.id,
            "quantity_added": quantity,
            "stock_before": product.stock - quantity,
            "stock_after": product.stock
        }, status=status.HTTP_200_OK)


class SubtractStockView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return Response({"error":"Produit introuvable"}, status=status.HTTP_400_BAD_REQUEST)
        
        quantity = request.data.get("quantity",None)
        motif = request.data.get("motif", None)

        if quantity is None:
            return Response({"error":"Le champ 'quantity' est requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            quantity = int(quantity)
        except:
            return Response({"error":"la quantity doit être un nombre"}, status=status.HTTP_400_BAD_REQUEST)
        if quantity <= 0:
            return Response({"error":"la quantité doit être positive"},status=status.HTTP_400_BAD_REQUEST)
        
        stock_before = product.stock
        product.subtract_stock(quantity,motif, request.user)

        product.refresh_from_db()
        stock_after = product.stock
        return Response({
            "message":"Stock retirer avec succès",
            "product_id":product.id,
            "quantity_added":quantity,
            "stock_before": stock_before,
            "stock_after":stock_after
        }, status=status.HTTP_200_OK)


class StockHistoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = StockHistorySerialize
    
    def get_queryset(self):
       queryset = StockHistory.objects.all()
       user_id = self.request.query_params.get('added_by', None)

       if user_id is not None:
         queryset = queryset.filter(added_by = user_id).order_by('-created_at')
         return queryset      
     
class DeleteStockHistoryView(RetrieveDestroyAPIView):
    queryset = StockHistory.objects.all()
    serializer_class= StockHistorySerialize
    permission_classes=[IsAuthenticated]
    lookup_field ='id'

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
        only_children = self.request.query_params.get('only_children') == 'true'

        if only_children:
            all_user_ids = list(User.objects.filter(created_by=user, is_deleted=False).values_list('id', flat=True))
        else:
            # admin + tous ses descendants
            all_user_ids = [user.id] + self.get_all_descendants_ids(user)

        queryset = Invoice.objects.filter(cashier__in=all_user_ids).select_related(
            'cashier', 'cashier__userprofile', 'cashier__created_by', 'cashier__created_by__userprofile'
        ).prefetch_related('items')

        # filtrer par cashier spécifique
        cashier_id = self.request.query_params.get('cashier')
        if cashier_id:
            queryset = queryset.filter(cashier=cashier_id)

        # filtrer par date
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
    def get_all_descendants_ids(self,user):
        """
        Retourne une liste de tous les descendants (enfants, petits-enfants, etc.) de l'utilisateur
        """
        User = get_user_model()

        all_users = User.objects.filter(is_deleted=False).values('id','created_by')
        children_map = {}
        for u in all_users:
            parent_id = u['created_by']
            children_map.setdefault(parent_id, []).append(u['id'])

        descendants = []
        queue = [user.id]

        while queue:
            parent_id = queue.pop(0)
            children = children_map.get(parent_id,[])
            descendants.extend(children)
            queue.extend(children)

        return descendants
    

class InvoiceChartView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InvoicesViewSerializer   
    def get(self, request):
        base_user_id = request.query_params.get("base_user_id")
        date_str = request.query_params.get("date")  # optionnel

        if not base_user_id:
            return Response({"error": "base_user_id required"}, status=400)

        try:
            base_user_id = int(base_user_id)
        except ValueError:
            return Response({"error": "invalid base_user_id"}, status=400)

        # Récupérer tous les IDs descendants
        user_ids = self.get_all_descendants_ids(base_user_id)

        # Filtrer les factures
        invoices = Invoice.objects.filter(cashier__in=user_ids, status="VALIDE")
        if date_str:
            try:
                date = timezone.make_aware(datetime.strptime(date_str, "%Y-%m-%d"))
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                invoices = invoices.filter(created_at__range=(start_of_day, end_of_day))
            except ValueError:
                pass

        # Optionnel : calculer total par caissier
        totals = {}
        for inv in invoices:
            cashier_id = inv.cashier.id
            totals[cashier_id] = totals.get(cashier_id, 0) + float(inv.total_amount)

        return Response({"totals_by_cashier": totals})
    

    def get_all_descendants_ids(self, base_user_id):
        User = get_user_model()
        descendant_ids = []
        queue = [base_user_id]

        while queue:
            parent_id = queue.pop(0)
            children = list(User.objects.filter(created_by=parent_id, is_deleted=False).values_list("id", flat=True))
            descendant_ids.extend(children)
            queue.extend(children)

        return [base_user_id] + descendant_ids


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
    
class SalesOffsetPagination(LimitOffsetPagination):
    default_limit = 50
    max_limit = 100
#API  pour l'historique de vente pour l'application  flutter 
class UserSalesHistoryView(generics.ListAPIView):
    serializer_class = InvoicesViewSerializer
    pagination_class = SalesOffsetPagination
    def get_queryset(self):
        cashier_id = self.request.query_params.get('cashier')
        if not cashier_id:
            return Invoice.objects.none()
    
        return (
            Invoice.objects
            .filter(cashier=cashier_id)
            .select_related('cashier')
            .prefetch_related('items')
            .order_by('-created_at')
        )
    
    
    
#fin de l'API
class CreateProfilView(generics.CreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfilViewSerializer
    permission_classes = [IsAuthenticated]


#active la gestion des points 
class TogglePoints(APIView):

    def post(self, request, pk):
        profil = get_object_or_404(UserProfile, pk=pk)
        with transaction.atomic():
            profil.point_is_activate = not profil.point_is_activate
            profil.save()
        
        return Response({
            "id": profil.id,
            "point_is_activate":profil.point_is_activate
        })



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

#API pour la reactivation de l'abonnement 
class ReactivateSubscriptionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        try:
            subscription = Subscription.objects.get(user__id =user_id)

            if subscription.end_date < timezone.now():
                subscription.end_date = timezone.now() + timedelta(days=30)
                subscription.start_date = timezone.now()
                subscription.is_active = True
                subscription.is_free_frial = False
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
    
class SubscriptionByEmailView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
            subscription = Subscription.objects.get(user=user)

            return Response({
                "subscription_type": subscription.subscription_type,
                "amount": subscription.amount,
                "end_date": subscription.end_date
            })
        
        except User.DoesNotExist:
            return Response(
                {"error": "Utilisateur non trouvé"},
                status=404
            )

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


class CashoutForAllUserView(generics.ListAPIView):
  serializer_class = CashOutSerializer
  permission_classes = [IsAuthenticated]

  def get_queryset(self):
      user = self.request.user
      only_children = self.request.query_params.get('only_children') == 'true'
      
      if only_children:
          all_user_ids = list(User.objects.filter(created_by=user, is_deleted=False).values_list('id', flat=True))
      else:
          all_user_ids = [user.id] + self.get_all_descendants_ids(user)
      
      queryset = CashOut.objects.filter(user__in=all_user_ids).select_related(
          'user','user__userprofile', 'user__created_by', 'user__created_by__userprofile'
      ).prefetch_related()

      user_id = self.request.query_params.get('user')
      if user_id:
          queryset = queryset.filter(user=user_id)

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
  
  def get_all_descendants_ids(self, user):
      
      User = get_user_model()
      descendants = []
      queue = [user.id]
      
      while queue:
          parent_id = queue.pop(0)
          children = list(User.objects.filter(created_by= parent_id, is_deleted=False).values_list('id', flat=True))
          descendants.extend(children)
          queue.extend(children)
      return descendants
     

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


class EntryNoteAllUserView(generics.ListAPIView):
    serializer_class = EntryNoteSerialize
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        only_chidren = self.request.query_params.get('only_children') == 'true'
        if only_chidren:
            all_user_ids = list(User.objects.filter(created_by=user, is_deleted=False).values_list('id', flat=True))
        else:
            all_user_ids = [user.id] + self.get_all_descendants_ids(user)
        
        queryset = EntryNote.objects.filter(user__in=all_user_ids).select_related(
            'user','user__userprofile','user__created_by','user__created_by__userprofile'
        ).prefetch_related()

        user_id = self.request.query_params.get('user')

        if user_id:
            queryset = queryset.filter(user=user_id)

        date_str = self.request.query_params.get('created_at')

        if date_str :
            try:
                date = timezone.make_aware(datetime.strptime(date_str, '%Y-%m-%d'))
                start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = date.replace(hour=23, minute=59, second=59, microsecond=999999)
                queryset = queryset.filter(created_at__range=(start_of_day, end_of_day))  
            except ValueError:
                print('Invalid date format provided', date_str)
        return queryset
    
    def get_all_descendants_ids(self, user):
        User = get_user_model()
        descendants = []
        queue = [user.id]
        
        while queue:
            parent_id = queue.pop(0)
            children = list(User.objects.filter(created_by = parent_id, is_deleted=False).values_list('id', flat=True))
            descendants.extend(children)
            queue.extend(children)
        return descendants
       


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

#API pour voir les payment
class PayementView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerialize

    def get_queryset(self):
        queryset = Payment.objects.all().order_by('-created_at')
        return queryset


# maishaPay
import requests

class MaishaPayPayment(APIView):

    def post(self, request):
        phone = request.data.get("phone")
        amount = request.data.get("amount")
        provider = request.data.get("provider")   # visa, mpesa, airtel…
        email = request.data.get("email")

        card_number = request.data.get('cardNumber')
        card_name = request.data.get('cardName')
        card_expiry = request.data.get('cardExpiry')
        card_cvv = request.data.get('cardCvv')
        

        expiry_month =None
        expir_year = None
        
        if card_expiry:
            try:
                expiry_month, expir_year = card_expiry.split("/")
            except:
                pass
        reference = str(uuid.uuid4())

        try:
            client = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable"}, status=404)

        try:
            subscription = Subscription.objects.get(user=client)
        except Subscription.DoesNotExist:
            return Response({"error": "Abonnement introuvable"}, status=404)
        
        maisha_data = {
            "transactionReference": reference,
            "gatewayMode": 0,
            "publicApiKey": settings.MAISHAPAY_PUBLIC_KEY,
            "secretApiKey": settings.MAISHAPAY_SECRET_KEY,

            "order": {
                "amount": amount,
                "currency": "USD",
                "customerFullName": f"{client.username} {client.first_name}",
                "customerEmailAdress": email
            },
        }

        # 🔹 Paiement par carte VISA / MasterCard
        if provider.lower() in ["visa", "mastercard"]:
            maisha_data["paymentChannel"] = {

                "channel": "CARD",
                "provider": "VISA",  # VISA / MASTERCARD
                "callbackUrl": "https://pos.bilatech.org/maishapay/webhook/",

            }
            url = "https://marchand.maishapay.online/api/collect/v3/store/card"

        else:

            maisha_data["paymentChannel"] = {
                "channel": "MOBILEMONEY",
                "provider": provider.upper(),
                "walletID": phone,
                "callbackUrl": "https://pos.bilatech.org/maishapay/webhook/"
            }

            url = "https://marchand.maishapay.online/api/collect/v2/store/mobileMoney"

        # Requête API
        response = requests.post(url, json=maisha_data, headers={"Content-Type": "application/json"})

        try:
            data = response.json()
        except:
            return Response({"error": "Réponse API invalide", "raw": response.text})

        print("data:", data)

        # Vérification du succès
        if data.get("status_code") == 200 and  data.get("transactionStatus") =='SUCCESS':
            Payment.objects.create(
                user=client,
                transaction_reference=reference,
                amount=amount,
                provider=provider,
                phone=phone,
                transaction_type="PAYMENT",
                status="SUCCESS"
            )

            subscription.end_date = timezone.now() + timedelta(days=30)
            subscription.start_date =timezone.now()
            subscription.is_active=True
            subscription.save()


        if data.get("status_code") == 202 and data.get("transactionStatus") =='PENDING':
            Payment.objects.create(
                user = client,
                transaction_reference=reference,
                amount=amount,
                provider=provider,
                phone=card_number,
                transaction_type="PAYEMENT",
                status="PANDING"
            )
        
        if client.email:
            message = (
                f"Bonjour {client.username},\n\n"
                f"Votre paiement Bila-Sol a été effectué avec succès le {timezone.now().strftime('%d/%m/%Y à %H:%M')}.\n\n"
                f" Montant : {amount} USD\n"
                f" Motif   : Renouvellement d’abonnement\n"
                f" Référence : {reference}\n\n"
                f"Opérateur : {provider}\n\n"
                f"Votre abonnement à été réactiver jusqu'au {subscription.end_date.strftime('%d/%m/%Y à %H:%M')}.\n\n"

                f"Merci pour votre confiance !\n"

                f"L'équipe Bila-Sol"
            )

            send_mail(
              subject="Paiement de votre abonnement",
                message=message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[client.email],
                fail_silently=False
            )



        return Response({
            'data':data,
            'status':200
        })
    
class MaishaPayCallback(APIView):

    authentication_classes = []
    permission_classes = []

    def get(self, request):

        status = request.GET.get("status")
        transaction_ref = request.GET.get("transactionRefId")
        try:
            payment = Payment.objects.get(transaction_reference=transaction_ref)
            if status =="200":
                payment.status ="SUCCESS"
            else:
                payment.status ="FAILED"
            
            payment.save()
        except Payment.DoesNotExist:
            pass

        return Response({"message":"transaction mise à jour"})
