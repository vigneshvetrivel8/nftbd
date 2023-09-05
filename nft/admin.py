from django.contrib import admin
from nft.models import Transactions,Collection,Itemtype,Rarity,WalletHistory, LastBlockProcessed

# Register your models here.
admin.site.register(Transactions)
admin.site.register(Collection)
admin.site.register(Itemtype)
admin.site.register(Rarity)
admin.site.register(WalletHistory)
admin.site.register(LastBlockProcessed)