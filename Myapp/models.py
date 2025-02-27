from django.db import models
from django.contrib.auth.models import User , AbstractUser# type: ignore


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    
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