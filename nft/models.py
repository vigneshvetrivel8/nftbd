from django.db import models

from django.utils import timezone

# Create your models here.

class Transactions(models.Model):
    from_address = models.CharField(max_length=150)
    to_address = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    token_id = models.IntegerField()
    block = models.BigIntegerField()
    time = models.DateTimeField()
    transactions_hash = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.id}. {self.from_address} to {self.to_address}"

class Collection(models.Model):
    Name = models.CharField(max_length=60)
    ImageUrl = models.CharField(max_length=600)
    Edition = models.IntegerField()
    Background = models.CharField(max_length=60)
    Hat = models.CharField(max_length=60)
    Mouth = models.CharField(max_length=60)
    current_owner = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.Name}"

class Rarity(models.Model):
    Name = models.CharField(max_length=5)
    Rarity_number = models.IntegerField()

    def __str__(self): 
        return f"{self.Name}: {self.Rarity_number}"

class Itemtype(models.Model):
    Name = models.CharField(max_length=15,unique=True)
    type_name = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.Name}: {self.type_name}"


class WalletHistory(models.Model):
    address = models.CharField(max_length=150)    
    time = models.DateTimeField()    

    def __str__(self):
        return f"{self.id}.{self.time}: {self.address}"

class LastBlockProcessed(models.Model):
    block = models.BigIntegerField()
    time = models.DateTimeField()    

    def __str__(self):
        return f"{self.block} at {self.time}"
    
    