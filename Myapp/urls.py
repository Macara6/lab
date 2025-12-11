from django.urls import path
from.views import *
from . import views
from django.views.decorators.cache import cache_page

urlpatterns = [
    path('',views.index, name='index'),
    path('login/',LoginView.as_view(), name='login'),
    #route pour le produit pour le stock
    path('products/',(ProductListView.as_view())),
    path('productCreate/',ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/addStock/<int:pk>/', AddStockView.as_view(), name='ajout_stock'),
    path('products/subtractStock/<int:pk>/', SubtractStockView.as_view(), name='sortie_stock'),
    path('stockHistoryViews/', StockHistoryView.as_view(), name="views_history_stock"),
    path('stockHistory/delete/<int:id>/', DeleteStockHistoryView.as_view(), name='delete_history'),

    #route pour le creer le produit pour le depôt 
    path("depotProdut/", DepotProductCreate.as_view(), name="depot_product"),


    path('invoices/', CreateInvoiceView.as_view(), name='create-invoice'),
    path('invoicesView/', InvoiceView.as_view(), name='invoices-views' ),
    path('invoice-chart/', InvoiceChartView.as_view(), name='invoice_fort_chart'),
    path('invoices/delete/<int:id>/', DeleleInvoice.as_view(), name='delete-invoice'),
    path('invoices/history/', UserSalesHistoryView.as_view(), name='user-sales-history'),
    path('invoice/detail/', InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoice/cancel/<int:invoice_id>/', CancelInvoiceView.as_view(), name='cancel_invoice'),
    path('usersView/', UserView.as_view(), name='user-list'),
   
    #route pour la categorie
    path('category/',CategoryView.as_view(), name='category-list'),
    path('category/create/',CreateCategoryView.as_view(), name ='create-category'),
    path('category/delete/<int:id>/', DeleteCategorieView.as_view(), name='delete-categorie'),
    path('category/by-user/<int:user_id>/', CategoryByUserView.as_view(), name='categorie-by-user'),
    #fin  
    
    #route pour l'utilisateur
    path('userCreate/', UserCreateView.as_view(), name='user-create'),
    path('users/created-by-me/', UsersCreatedByMeView.as_view(), name='users-created-by-me'),
    path('users-created-by/',UserCreatedByView.as_view(), name='utilisateur'),
    path('user-for-chart/', UserTreeView.as_view(),name='user-tree' ),
    path('userUpdateView/<int:user__id>/',UpdatUserVieuw.as_view, name='user-update' ),
    path('usersView/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('user/delete/<int:id>/',DeleteUserView.as_view(), name='delete-user'),
    path("users/restore/<int:id>/", RestoreUserView.as_view(), name="restore-user"),
    path("users/delete-permanent/<int:id>/", PermanentDeleteUserView.as_view(), name="delete-user-permanent"),
    path("users/trashed/", TrashedUsersListView.as_view(), name="trashed-users"),
    path('user/update/', UpdateUserApiView.as_view(), name='update-user'),

    #route pour le mot de passe 
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    #route pour le code secret 
    path('secret_key/', SecretAccessKeyCreateUpdateView.as_view(), name='secret_key'),
    path('secret_key/status/', SecretKeyStatusView.as_view(), name='secret-key-status'),
    #route pour la token
    path('refresh-token/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('secret_key/verify/', VerifySecretKeyView.as_view(), name='verify-secret-key'),


    #route pour la subscription 
    path('listSubsription/',ListSubscriptionView.as_view(), name='listeSubsription'),
    path('subscription/update/<int:user__id>/',UpdateSubscriptionView.as_view(), name ='update-subscription'),
    path('createSubscription/', CreateSubsriptionView.as_view(), name='subscriptionView'),
    path('subscription/<int:user__id>/', SubscriptionByUserView.as_view(), name='subscription-by-user'),
    path('subscription/reactivate/<int:user_id>/', ReactivateSubscriptionView.as_view(), name='reactivate-subscription'),
    path('subscription/user/<int:user_id>/',SubscriptionByUserAndChildUserView.as_view(), name='subscription-user'),
    path('subscription/status/',SubsriptionStatusView.as_view(), name="subscription_status"),
    
    #route pour le profile
    path('userProfil/', UserProfilView.as_view(), name='user_profil'),
    path('userProfil/update/', UserProfilUpdateView.as_view(), name='user_profil_update'),
    path('userProfil/create/',CreateProfilView.as_view(), name='create-profile'),

    #route pour la careation, vision et suppression du bon de sortie
    path('cashouts-all-users/',CashoutForAllUserView.as_view(), name='cashout-for-users'),
    path('cashouts/', CashOutView.as_view(), name='cashout-list'),
    path('cashoutDetail/', CashOutDetailView.as_view(), name='cashout-detail'),
    path('cashout/create/', CreateCashOutView.as_view(), name='create-cashout'),
    path('cashout/delete/<int:id>/', DeleteCashOut.as_view(), name='delete-cashout'),
    #fin de routage

    #routage pour la creation du bon d'entré
    path('EntryNotes-all-users/',EntryNoteAllUserView.as_view(), name='entry_note_all_user'),
    path("entryNote/create/",CreateEntryNoteView .as_view(), name="create-entryNote"),
    path('entryNote/',EntryNoteViewList.as_view(),name='Entry_note-list'),
    path('entryNote/detail/', EntryDetailView.as_view(), name= 'entryNote-detail'),
    path('entryNote/delete/<int:id>/', DeleteEntryNote.as_view(),name='entryNode-delete'),
    #fin de routage pour le entry note
    path('test-sentry/', test_sentry),
    
]
