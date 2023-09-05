from django.shortcuts import render
from .models import Transactions,Collection,Rarity,Itemtype, WalletHistory, LastBlockProcessed
import json
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from web3 import Web3 
from eth_account import Account 
import aiohttp 
import asyncio 
import random
from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError 
from django.db import transaction
from web3.middleware import geth_poa_middleware 
from datetime import datetime
import time
from web3.datastructures import AttributeDict 
from asgiref.sync import sync_to_async 
from django.db.models import Count 
from dateutil.relativedelta import relativedelta 
import schedule
import sched


def load_transactions_database(start_block,end_block):
    # Connect to the Polygon network
    web3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))

    web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def retry(func):
        max_retries = 1000
        retries = 0

        def wrapper(*args, **kwargs):
            nonlocal retries

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"An error occurred: {str(e)}")
                    print("Retrying...")
                    retries += 1
                    time.sleep(0.1)  

            return None

        return wrapper

    @retry
    def get_transaction_time(transaction_hash):
        # Get the transaction receipt
        receipt = web3.eth.get_transaction_receipt(transaction_hash)

        if receipt is None or receipt.blockNumber is None:
            return None

        # Get the block number
        block_number = receipt.blockNumber

        # Retrieve the block information using block number
        block = web3.eth.get_block(block_number)

        if block is None or block.timestamp is None:
            return None

        # Retrieve the timestamp of the block
        block_timestamp = block.timestamp

        return {
            'timestamp': block_timestamp,
            'block_number': block_number
        }

    @retry
    def block_func(transaction_hash):
        # Get the transaction receipt
        receipt = web3.eth.get_transaction_receipt(transaction_hash)

        if receipt is None or receipt.blockNumber is None:
            return None

        # Get the block number
        block_number = receipt.blockNumber

        # Retrieve the block information using block number
        block = web3.eth.get_block(block_number)

        return block

    @retry
    def get_transaction_func(transaction_hash):
        # Get the transaction details
        transaction = web3.eth.get_transaction(transaction_hash)

        return {
            'transactionHash': transaction_hash,
            'sender': transaction['from'],
            'value': transaction['value'],
            'transaction': transaction
        }

    @retry
    def transaction_receipt_output_func(transaction_hash):
        # Get the transaction details
        transaction = web3.eth.get_transaction_receipt(transaction_hash)
        return transaction

    async def get_contract_transactions(contract_address, from_block, to_block):
        transactions = []
        processed_transactions = set()

        current_block = from_block
        batch_size = 3000

        while current_block <= to_block:
            # Define the filter parameters for the current batch
            filter_params = {
                'fromBlock': current_block,
                'toBlock': min(current_block + batch_size, to_block),
                'address': contract_address
            }

            # Retrieve the logs matching the filter
            logs = web3.eth.get_logs(filter_params)

            for log in logs:
                transaction_hash = log.transactionHash.hex()

                # Skip duplicate transactions
                if transaction_hash in processed_transactions:
                    continue

                transaction_details = get_transaction_func(transaction_hash)
                transaction_receipt_other_details = get_transaction_time(transaction_hash)
                transaction = {
                    'transactionHash': transaction_hash,
                    'sender': log.topics[1].hex(),
                    'receiver': transaction_details['sender'],
                    'amount': transaction_details['value'],
                    'transactionTime': transaction_receipt_other_details['timestamp'],
                    'transaction_output': transaction_details['transaction'],
                    'transaction_receipt_output': transaction_receipt_output_func(transaction_hash),
                    'block_output': block_func(transaction_hash),
                    'log_output': log,
                    'block_number': transaction_receipt_other_details['block_number']
                }
                transactions.append(transaction)

                # Mark transaction as processed
                processed_transactions.add(transaction_hash)

            # Print current progress
            print(f"Processing blocks {current_block} - {min(current_block + batch_size, to_block)}")

            # Increment the current_block for the next batch
            current_block += batch_size + 1

        return transactions

    def extract_data(string, start_char, end_char):
        extracted_data = []
        start_index = string.find(start_char)
        while start_index != -1:
            start_index += len(start_char)
            end_index = string.find(end_char, start_index)
            if end_index == -1:
                break
            str_data = string[start_index:end_index]
            if "HexBytes('0x')" in str_data:
                data = str_data[148:387]
                extracted_data.append(data)
            start_index = string.find(start_char, end_index)
        return extracted_data

    async def process_transactions():
        contract_address = '0x070F62778E939927eF99d330E590165F176fDf16'
        from_block = start_block
        to_block = end_block 
        transactions = await get_contract_transactions(contract_address, from_block, to_block)
        return transactions

    # Run the code within an asynchronous context
    transactions = asyncio.run(process_transactions())

    # Create a list to hold the Transactions objects
    bulk_transactions = []

    # Process each transaction
    for transaction in transactions:
        # Extract relevant data from the transaction
        amount = transaction['amount'] / 10 ** 18
        timestamp = transaction['transactionTime']
        readable_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        input_string = str(transaction['transaction_receipt_output'].__dict__)
        start_char = 'AttributeDict({'
        end_char = '})'
        extracted_data = extract_data(input_string, start_char, end_char)

        for data in extracted_data:
            data_from = "0x" + data[36:76]
            data_to = "0x" + data[116:156]
            data_id = data[170:236]
            if data_to != "0x0000000000000000000000000000000000000000":
                transaction_object = Transactions(
                    from_address=data_from,
                    to_address=data_to,
                    amount=amount,
                    token_id=int(data_id,16),
                    block=transaction['block_number'],
                    time=readable_time,
                    transactions_hash=transaction['transactionHash']
                )
                bulk_transactions.append(transaction_object)

    Transactions.objects.bulk_create(bulk_transactions)


def get_current_owner(edition):
    return Transactions.objects.filter(token_id=edition).last().to_address


def load_collection_database():
    import aiohttp
    import asyncio
    from aiohttp.client_exceptions import ClientConnectorError, ServerDisconnectedError
    from django.db import transaction
    from asgiref.sync import sync_to_async

    MAX_RETRIES = 1000

    async def process_data(i):
        url = f"https://ipfs.io/ipfs/QmSXJSHP9uJzRzJoD8crZZ1RmAtqnNNZitLbpsmtZpCa5w/{i}.json"

        retry_count = 0
        while retry_count < MAX_RETRIES:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        data = await response.json()

                        name = data['name']
                        image1 = data['image']
                        image = "https://ipfs.io/ipfs/" + image1[7:]
                        edition = data['edition']
                        attributes = data['attributes']
                        current_owner = await sync_to_async(get_current_owner)(edition)

                        print(f"Processed {name} ......")

                        result = {
                            "Name": name,
                            "Image": image,
                            "Edition": edition,
                            "Background": attributes[0]['value'],
                            "Hat": attributes[1]['value'],
                            "Mouth": attributes[2]['value'],
                            "current_owner": current_owner
                        }

                        return i, result

            except (ClientConnectorError, ServerDisconnectedError) as e:
                retry_count += 1
                print(f"Retry {retry_count} - Error: {e}")

        return i, None

    async def main():
        iterations = 1049

        processed_urls = set()
        tasks = []
        for i in range(1, iterations + 1):
            url = f"https://ipfs.io/ipfs/QmSXJSHP9uJzRzJoD8crZZ1RmAtqnNNZitLbpsmtZpCa5w/{i}.json"
            if url not in processed_urls:
                processed_urls.add(url)
                task = asyncio.create_task(process_data(i))
                tasks.append(task)

        results = await asyncio.gather(*tasks)

        results.sort(key=lambda x: x[0])

        data_to_save = []
        for result in results:
            if result[1] is not None:
                i, data = result
                data_to_save.append(data)

        await save_data_to_database(data_to_save)

    @sync_to_async
    @transaction.atomic
    def save_data_to_database(data_list):
        bulk_data = [
            Collection(
                Name=data['Name'],
                ImageUrl=data['Image'],
                Edition=data['Edition'],
                Background=data['Background'],
                Hat=data['Hat'],
                Mouth=data['Mouth'],
                current_owner=data['current_owner']
            )
            for data in data_list
        ]

        Collection.objects.bulk_create(bulk_data)

        for data in data_list:
            print(f"Name: {data['Name']}")
            print(f"ImageURL: {data['Image']}")
            print("----------------------")

    asyncio.run(main())


# ---------------------------------------------------------------------------------------------------------------

# # functions part 1:
# load_transactions_database(29936472,29936472)
# load_transactions_database(33131494,34247571)
# load_transactions_database(44628933,44946017)
# load_collection_database()
# print("-------------------------------------------------------------------------------------------")
# print("completed feeding collection and transaction data")

# --------------------------------------------------------------------------------------------------------------

# #note:
# #load_transactions_database are run for the above block intervals as only these blocks were involved for this nft collection.
# #may run the below load_transactions_database to process all blocks, which is time-consuming.
# web3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
# load_transactions_database(0,web3.eth.block_number)
# # web3.eth.block_number is the latest block

# ------------------------------------------------------------------------------------------------------------

# # part 1:
unique_backgrounds = Collection.objects.values_list('Background', flat=True).distinct()
background_list = list(unique_backgrounds)

unique_backgrounds_h = Collection.objects.values_list('Hat', flat=True).distinct()
hat_list = list(unique_backgrounds_h)

unique_backgrounds_m = Collection.objects.values_list('Mouth', flat=True).distinct()
mouth_list = list(unique_backgrounds_m)

background_counts = {}
hat_counts = {}
mouth_counts = {}

for background in background_list:
    count = Collection.objects.filter(Background=background).count()
    background_counts[f"{background}"] = count

for hat in hat_list:
    count = Collection.objects.filter(Hat=hat).count()
    hat_counts[f"{hat}"] = count   

for mouth in mouth_list:
    count = Collection.objects.filter(Mouth=mouth).count()
    mouth_counts[f"{mouth}"] = count

# ----------------------------------------------------------------------------------------------------------------

def load_rarity():
    max_retries=150
    retry_delay=0
    bulk_rarity = []
    for i in range(1049):
        retries = 0
        while retries < max_retries:
            try:
                item = Collection.objects.filter(Edition=(i + 1)).first()
                background_number = background_counts[item.Background]
                hat_number = hat_counts[item.Hat]
                mouth_number = mouth_counts[item.Mouth]
                item_total = background_number + hat_number + mouth_number
                Rarity_object = Rarity(Name=f"{i + 1}", Rarity_number=item_total)
                print(f"Processed {i + 1} ......")
                bulk_rarity.append(Rarity_object)
                break  
            except Exception as e:
                print(f"Error occurred for {i + 1}. Retry attempt {retries + 1}/{max_retries}. Error: {e}")
                retries += 1
                time.sleep(retry_delay)  
        else:
            print(f"Failed to process {i + 1} after {max_retries} retries. Skipping this item.")

    if bulk_rarity:
        Rarity.objects.bulk_create(bulk_rarity)
        print("Bulk create completed successfully.")


def update_item_type():
    sales_value = {}
    for i in range(1049):
        item_no = i+1
        sales_count = Transactions.objects.filter(amount__gt=0, token_id=item_no).count()
        sales_value[f"{i+1}"] = sales_count    
    
    sales_value_gt_0_dict = {key: value for key, value in sales_value.items() if value > 0}

    keys_to_filter = sales_value_gt_0_dict.keys()

    int_keys_to_filter = map(int, keys_to_filter)

    filtered_objects = Itemtype.objects.filter(Name__in=int_keys_to_filter)

    for obj in filtered_objects:
        obj.type_name = "Type_1"
        print(f"Completed {obj.Name}............")
        obj.save()

    print("completed updating")

    
def load_item_type():
    sales_value = {}
    for i in range(1049):
        item_no = i+1
        sales_count = Transactions.objects.filter(amount__gt=0, token_id=item_no).count()
        sales_value[f"{i+1}"] = sales_count

    sorted_sales_value = dict(sorted(sales_value.items(), key=lambda item: item[1], reverse=True))
    sales_value_gt_0_dict = {key: value for key, value in sales_value.items() if value > 0}
    
    from django.db.models import F, IntegerField
    from django.db.models.functions import Cast

    rarest_above_599 = {}
    rarest_items = Rarity.objects.annotate(Name_int=Cast('Name', IntegerField())).filter(Name_int__gt=599).order_by('Rarity_number')[:32]

    for item in rarest_items:
        rarest_above_599[item.Name] = item.Rarity_number

    order_dict_1 = {}
    order_dict_1.update(sales_value_gt_0_dict)
    order_dict_1.update(rarest_above_599)

    max_retries = 150
    retry_delay = 0
    bulk_item_type = []

    for i in range(1049):
        for retry in range(max_retries + 1):
            try:
                if (i + 1) in map(int, order_dict_1.keys()):
                    item_type_object = Itemtype(Name=f"{i + 1}", type_name="Type_1")
                else:
                    item_type_object = Itemtype(Name=f"{i + 1}", type_name="Type_2")
                print(f"Processed {i + 1} ......")
                bulk_item_type.append(item_type_object)
                break  
            except Exception as e:
                print(f"Error occurred during processing {i + 1}. Retry attempt {retry + 1}/{max_retries}. Error: {e}")
                if retry < max_retries:
                    time.sleep(retry_delay)  
                else:
                    print(f"Failed to process {i + 1} after {max_retries} retries. Skipping this item.")

    if bulk_item_type:
        Itemtype.objects.bulk_create(bulk_item_type)
        print("Bulk create completed successfully.")

# ----------------------------------------------------------------------------------------------------------------------------------------------

# # functions part 2:
# load_rarity()
# load_item_type()
# print("completed feeding data")

# -----------------------------------------------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------------------------------

# part 2:
items_type_1 = Itemtype.objects.filter(type_name="Type_1")
list_of_tuples_1 = [(item.Name, item.type_name) for item in items_type_1]
dict_1 = dict(list_of_tuples_1)

items_type_2 = Itemtype.objects.filter(type_name="Type_2")
list_of_tuples_2 = [(item.Name, item.type_name) for item in items_type_2]
dict_2 = dict(list_of_tuples_2)

# -------------------------------------------------------------------------------------------------------------------------------------------

def nft_object():
    random.shuffle(list_of_tuples_1)
    new_dict_1 = dict(list_of_tuples_1)

    random.shuffle(list_of_tuples_2)
    new_dict_2 = dict(list_of_tuples_2)

    new_dict_1.update(new_dict_2)

    edition_numbers_dict1 = new_dict_1.keys()

    int_edition_numbers_dict1 = [int(edition) for edition in edition_numbers_dict1]

    sorted_collections_dict1 = Collection.objects.filter(Edition__in=int_edition_numbers_dict1)

    def custom_sort(item):
        return int_edition_numbers_dict1.index(item.Edition)

    sorted_collections_dict1 = sorted(sorted_collections_dict1, key=custom_sort)
    return sorted_collections_dict1

# ------------------------------------------------------------------------------------------------------------------------

# part 3:
rarity_objects = Rarity.objects.all().order_by('Rarity_number')
list_of_rarity_objects = [(item.Name, item.Rarity_number) for item in rarity_objects]
dict_rarity = dict(list_of_rarity_objects)

owner_objects = Collection.objects.all()
list_of_owner_objects = [(item.Edition, item.current_owner) for item in owner_objects]
dict_owner = dict(list_of_owner_objects)

# -----------------------------------------------------------------------------------------------------------------------

# update_item_type()(isn't required initially)

# ------------------------------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------------------------

def update_block_number():
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

# -------------------------------------------------------------------------------------------------------------------

# Views:


def gallery(request):
    dict_1_value = nft_object()
    if request.method == "POST":
        if "traitb" in request.POST:
            trait = request.POST["traitb"]
        elif "traith" in request.POST:
            trait = request.POST["traith"]

        elif "traitm" in request.POST:
            trait = request.POST["traitm"]

        return render(request, 'nfts/gallery.html' ,{
            "nfts" : dict_1_value,
            "total" : 1049,
            "background_list" : background_list,
            "hat_list" : hat_list,
            "mouth_list" : mouth_list,
            "background_count_dict" : background_counts,
            "hat_count_dict" : hat_counts,
            "mouth_count_dict" : mouth_counts,
            "traits" : trait,
            "first_section" : json.dumps(dict_1),
            "second_section" : json.dumps(dict_2),
            "rarity" : json.dumps(list_of_rarity_objects),
            "current_owner": json.dumps(dict_owner)
        })

    else:
        return render(request, 'nfts/gallery.html' ,{
            "nfts" : dict_1_value,
            "total" : 1049,
            "background_list" : background_list,
            "hat_list" : hat_list,
            "mouth_list" : mouth_list,
            "background_count_dict" : background_counts,
            "hat_count_dict" : hat_counts,
            "mouth_count_dict" : mouth_counts,
            "first_section" : json.dumps(dict_1),
            "second_section" : json.dumps(dict_2),
            "rarity" : json.dumps(list_of_rarity_objects),
            "current_owner" : json.dumps(dict_owner)
        })


def item(request,nft_id):
    from django.db.models import Count

    transactions_sale = Transactions.objects.filter(token_id=nft_id, amount__gt=0)

    transaction_hashes = transactions_sale.values_list('transactions_hash', flat=True)

    transactions_with_hashes = Transactions.objects.filter(transactions_hash__in=transaction_hashes)

    transaction_counts = transactions_with_hashes.values('transactions_hash').annotate(count=Count('transactions_hash'))

    divided_amounts = []
    transaction_hashes_of_sales = []
    for transaction in transactions_sale:
        transaction_hash = transaction.transactions_hash
        count_with_hash = next(item['count'] for item in transaction_counts if item['transactions_hash'] == transaction_hash)
        amount = float(transaction.amount)
        divided_amount = amount / count_with_hash
        divided_amounts.append(divided_amount)
        transaction_hashes_of_sales.append(transaction_hash)


    transactions = Transactions.objects.values('transactions_hash').annotate(hash_count=Count('transactions_hash')).filter(amount__gt=0.0, hash_count__gt=1)
    transaction_hashes = [transaction['transactions_hash'] for transaction in transactions if transaction['hash_count'] > 1]

    background_percentage_dict = {}
    hat_percentage_dict = {}
    mouth_percentage_dict = {}

    for background, count in background_counts.items():
        percentage = (count / 1049) * 100
        background_percentage_dict[background] = round(percentage)

    for background, count in hat_counts.items():
        percentage = (count / 1049) * 100
        hat_percentage_dict[background] = round(percentage)

    for background, count in mouth_counts.items():
        percentage = (count / 1049) * 100
        mouth_percentage_dict[background] = round(percentage)

    return render(request, 'nfts/item_page.html',{
        "nft_item" : Collection.objects.filter(Edition=nft_id),
        "transactions" : Transactions.objects.filter(token_id=nft_id),
        "transaction_hashes": transaction_hashes,
        "amounts": divided_amounts,
        "transaction_hashes_of_sales": transaction_hashes_of_sales,
        "background_percentage_dict" : background_percentage_dict,
        "hat_percentage_dict" : hat_percentage_dict,
        "mouth_percentage_dict" : mouth_percentage_dict,
        "background_count_dict" : background_counts,
        "hat_count_dict" : hat_counts,
        "mouth_count_dict" : mouth_counts,
        "current_owner" : json.dumps(dict_owner)
    })


def owner_page(request,address):
    dict_activity={}

    for i in range(1049):
        count = Transactions.objects.filter(token_id=i+1).count()
        dict_activity[f"{i+1}"] = count

    return render(request, 'nfts/owner_page.html',{
        "nfts" : Collection.objects.filter(current_owner=address.lower()),
        "count" : Collection.objects.filter(current_owner=address.lower()).count(),
        "address" : address,
        "rarity" : json.dumps(dict_rarity),
        "activity" : json.dumps(dict_activity),
        "current_owner" : json.dumps(dict_owner)
    })


def stats(request):
    token_owner={}
    for i in range(1049):
        instance = Collection.objects.filter(Edition=i+1).last()
        token_owner[f"{i+1}"] = instance.current_owner

    owners_count={}

    for edition, owner in token_owner.items():
        if owner in owners_count:
            owners_count[owner] += 1
        else:
            owners_count[owner] = 1

    sorted_owners_count = dict(sorted(owners_count.items(), key=lambda item: item[1], reverse=True))

    count_of_counts = {}

    for owner_count in owners_count.values():
        if f"{owner_count} items" in count_of_counts:
            count_of_counts[f"{owner_count} items"] += 1
        else:
            count_of_counts[f"{owner_count} items"] = 1

    sorted_count_of_counts = dict(sorted(count_of_counts.items(), key=lambda item: int(item[0].split()[0])))

    time_count = {}
    start_date = datetime(2022, 1, 1, 0, 0, 0)
    end_date = datetime(2022, 6, 30, 23, 59, 59)

    while end_date <= datetime.now():
        transactions_within_time_range = Transactions.objects.filter(time__range=(start_date, end_date))

        count_of_transactions_within_time_range = transactions_within_time_range.count()

        time_count[f"{start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}"] = count_of_transactions_within_time_range

        start_date += relativedelta(months=6)
        end_date += relativedelta(months=6)

    end_date = datetime.now()
    transactions_within_time_range = Transactions.objects.filter(time__range=(start_date, end_date))

    count_of_transactions_within_time_range = transactions_within_time_range.count()

    time_count[f"{start_date.strftime('%d/%m/%Y')} to {end_date.strftime('%d/%m/%Y')}"] = count_of_transactions_within_time_range

    first_25_pairs = list(sorted_owners_count.items())[:25]
    first_25_dict = {key: value for key, value in first_25_pairs}
    sorted_count_of_counts['1 items'] += 1

    first_key = next(iter(sorted_owners_count))  
    first_value = sorted_owners_count[first_key]  

    return render(request, 'nfts/stats.html',{
        "top_25" : json.dumps(first_25_dict),
        "time_count" : json.dumps(time_count),
        "items_count" : json.dumps(sorted_count_of_counts),
        "max_items_per_wallet" : first_value,
        "owners_count" : len(sorted_owners_count),
        "current_owner" : json.dumps(dict_owner)
    })


def about(request):
    unique_owner_count = Collection.objects.values('current_owner').annotate(owner_count=Count('current_owner')).count()            
    return render(request, 'nfts/about.html',{
        "count" : unique_owner_count,
        "current_owner" : json.dumps(dict_owner)
    })


def home(request):
    return render(request, 'nfts/home.html',{
        "current_owner" : json.dumps(dict_owner)
    })


def save_history(request):
    if request.method == "POST":
        current_time = datetime.now()
        address = request.POST["history-f"]
        WalletHistory(address=address, time=current_time).save()
        return HttpResponse(status=204)


def terms(request):
    return render(request, 'nfts/terms.html',{
        "current_owner" : json.dumps(dict_owner)
    })

