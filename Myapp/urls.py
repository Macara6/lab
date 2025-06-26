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
    path('userUpdateView/<int:user__id>/',UpdatUserVieuw.as_view, name='user-update' ),
    path('usersView/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('createSubscription/', CreateSubsriptionView.as_view(), name='subscriptionView'),
    path('listSubsription/',ListSubscriptionView.as_view(), name='listeSubsription'),
    path('subscription/update/<int:user__id>/',UpdateSubscriptionView.as_view(), name ='update-subscription'),
    path('subscription/<int:user__id>/', SubscriptionByUserView.as_view(), name='subscription-by-user'),
    path('subscription/reactivate/<int:user_id>/', ReactivateSubscriptionView.as_view(), name='reactivate-subscription'),
    path('invoices/history/', UserSalesHistoryView.as_view(), name='user-sales-history'),
    path('userProfil/', UserProfilView.as_view(), name='user_profil'),
    path('userProfil/update/', UserProfilUpdateView.as_view(), name='user_profil_update'),

    #route pour la careation, vision et suppression du bon de sortie
    path('cashouts/', CashOutView.as_view(), name='cashout-list'),
    path('cashoutDetail/', CashOutDetailView.as_view(), name='cashout-detail'),
    path('cashout/create/', CreateCashOutView.as_view(), name='create-cashout'),
    path('cashout/delete/<int:id>/', DeleteCashOut.as_view(), name='delete-cashout'),
    #fin de routage

    #routage pour la creation du bon d'entré
    path("entryNote/create/",CreateEntryNoteView .as_view(), name="create-entryNote"),
    path('entryNote/',EntryNoteViewList.as_view(),name='Entry_note-list'),
    path('entryNote/detail/', EntryDetailView.as_view(), name= 'entryNote-detail'),
    path('entryNote/delete/<int:id>/', DeleteEntryNote.as_view(),name='entryNode-delete')
    #fin de routage pour le entry note
    
]
