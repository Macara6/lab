
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User , AbstractUser# type: ignore


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    entrep_name = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    adress= models.CharField(max_length=40, null=True, blank=True)
    rccm_number= models.CharField(max_length=40)
    impot_number= models.CharField(max_length=255)

    
class Category(models.Model):

    name = models.CharField(max_length=50)
    user_created =  models.ForeignKey(User, on_delete=models.CASCADE)
   

    def __str__(self):
        return self.name

class Product(models.Model):
   name = models.CharField(max_length=50)
   price = models.DecimalField(max_digits=10, decimal_places=2)
   puchase_price = models.DecimalField(max_digits=10, decimal_places=2)
   stock = models.PositiveIntegerField(default=0)
   category = models.ForeignKey(Category, on_delete= models.CASCADE)
   user_created = models.ForeignKey(User, on_delete=models.CASCADE)
   created_at = models.DateTimeField(auto_now_add=True)

   def __str__(self):
       created_at= self.created_at.strftime('%Y-%m-%d %H:%M')
       return f"{self.name} - {created_at}"                                                                                                                                     
   
class Invoice(models.Model):
    client_name = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10,decimal_places=2)
    change =  models.DecimalField(max_digits=10, decimal_places=2)
    cashier =  models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        created_at= self.created_at.strftime('%Y-%m-%d %H:%M')
        return f"Invoice {self.id} - {self.client_name} -{created_at}"
    

# class pour geree les adonnnemnt des utilisateur  
 
class Subscription(models.Model):
    BASIC = 'BASIC'
    MEDIUM = 'MEDIUM'
    PREMIUM = 'PREMIUM'

    SUBSCRIPTION_TYPES = [
        (BASIC, 'Basic'),
        (MEDIUM, 'Medium'),
        (PREMIUM, 'Premium'),
    ] 
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription_type = models.CharField(max_length=10, choices=SUBSCRIPTION_TYPES,default=BASIC)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateTimeField(auto_now=True)
    end_date =models.DateTimeField()
    is_active =models.BooleanField(default=True)

    def __str__(self):
        return f"subscription forn {self.user.username} - Activate: {self.is_active} "
    
    def is_expired(self):
        
        return self.end_date <= timezone.now()
    
    def deactivate_subscription(self):
        self.is_active = False
        self.save()

class CashOut(models.Model):
    user =  models.ForeignKey(User,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now= True)
    motif = models.CharField(max_length=30, default="Aucun motif")
    def __str__(self):
        return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_amount(self):
        return sum(detail.amount for detail in self.details.all())

class CashOutDetail(models.Model):
    cashout = models.ForeignKey(CashOut, related_name='details', on_delete=models.CASCADE)
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
       return f"{self.reason} - {self.amount}"   


class EntryNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now=True)
    supplier_name = models.CharField(max_length=30)

    def __str__(self):
         return f"{self.supplier_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def total_amount(self):
        return sum(detail.amount for detail in self.details.all())
    
class EntryNoteDetail(models.Model):
    entrynote = models.ForeignKey(EntryNote, related_name='details', on_delete=models.CASCADE)
    reason = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
       return f"{self.reason} - {self.amount}"   
