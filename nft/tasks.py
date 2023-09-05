# your_app/tasks.py

from celery import shared_task
from datetime import datetime
from .models import Transactions, LastBlockProcessed
from web3 import Web3 
from .views import load_transactions_database



from web3 import Web3 
from eth_account import Account 
import aiohttp 
import asyncio 
from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError 
from django.db import transaction
from web3.middleware import geth_poa_middleware 
from datetime import datetime
import time
from web3.datastructures import AttributeDict 
from asgiref.sync import sync_to_async 
from dateutil.relativedelta import relativedelta 




@shared_task
def my_periodic_task():
    # Your task logic here
    print(f"Task executed at: {datetime.now()}")
    web3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
    if LastBlockProcessed.objects.exists():
        last_entry = LastBlockProcessed.objects.latest('id')
        latest_transaction_block = last_entry.block
        last_entry.delete()
        load_transactions_database(int(latest_transaction_block)+1,web3.eth.block_number)
        last_block_processed = LastBlockProcessed(block=web3.eth.block_number,time=datetime.now())
        last_block_processed.save()


    else:
        latest_transaction = Transactions.objects.latest('id')
        latest_transaction_block = latest_transaction.block
        load_transactions_database(int(latest_transaction_block)+1,web3.eth.block_number)
        last_block_processed = LastBlockProcessed(block=web3.eth.block_number,time=datetime.now())
        last_block_processed.save()
