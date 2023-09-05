# Distinctiveness and Complexity


### Distinctiveness:
This project is distinct from social-network (project-4) because this is a Web3 or Blockchain website(Nft's website). So in order to be decentralised there is no username or any other related features involved(wallet address or user's address is involved though). It also doesnt have anything like comments, likes etc.  

This project is different from e-commerce (project-2) because it doesnt have any features like buying or listing
an item. This is a NFT website of a particular collection, so the count of items involved is constant. No new items can be added or the existing items cannot be removed.  

This project is different from CS50W pizza project as it doesnt have any add to cart or add item from menu, or
anything similar.  

This project is also different from Mail (project-3), Wiki (project-1) or Search (project-0) in terms of usage.


### Complexity:
This project is related to nft collection. So in order to make this website we need to have data related to transactions, info of each and every item, etc. As this collection involves 1050 items(and we may see 10000 or more items in many other collections) it is impossible to manually enter the data related to each item involved or each transactions involved. 

So we have 2 functions which does that for us. 

We have a function "load_transactions_database(start_block,end_block)" which helps in feeding each transactions involved. In this function we have to call the function with block numbers(range in which we want to call). When the function is called it processes blocks, and looks if the collection we are looking for is present in them. Example:load_transactions_database(33131494,34247571), when this function is called it processeses somewhere around 1 million blocks and some 1000 transactions in which this collection was involved and feed them in about 2-3 minutes. The processing speed is even faster when the collection is not involved much in the given range, and becomes a bit slower when there are too many transactions involved in given range.  
This function involves get_transaction_receipt and many other web3 function, which provides us with a very big and complex data for each block and interpreting them according to our needs is a bit complex(The function will be discussed briefly in documentation later).

Then we have a function to feed info related to each item like traits, image url etc. this is done by a function called "load_collection_database()", which helps in processing all items(1050 here) and feeds the info in database in about 2 minutes.

These are the 2 main function and 2 database involved.

We also have function and database which is related to 
* rarity of the traits involved in each item, 
* arranging items such that best results or items are displayed first.  

This was the backend part.

In frontend we have home, about, gallery, stats, terms, items page, owners page.  
Each page has a connect button which we can use if we have a metamask wallet.
Connecting helps in viewing items which that wallet address own and filter can be applied on them in gallery page. In backend the user's address and time at which user's wallet is connected is stored.

In gallery page we display all the items, we can search for a particular item, view items based on traits or combination of traits, connect the wallet and view items that the connected wallet address own, sort based on ascending order or rarity of traits. But all these are done in front end itself, and not processed from backend.

Next we have stats page, which has some graphs which are made according to the state or situation of the collection.

Then we have items page, which shows all information related to particular item. It also has traits, clicking on it leads to gallery with that filter pre applied, showing all items with that particular trait. It also has transactions table and graph, clicking on each row of table or each bar of bar graph leads to even more info.

These are a little bit tough front end pages.

Then we have owner's page which shows item or items from this collection, owned by that particular address.

Then we have home, about, terms page which are normal static pages.

All pages are responsive.  

This was the frontend part.

# Documentation
Discussing all the files

# models.py:
* We have a model named Transactions, which stores details related to a particular transaction.  
We have from and to address, which says between which addresses the transactions occured.  
Then amount, which stores amount involved in the transaction(0 if none).  
Then we have token_id which stores the edition number or item involved in the transaction.  
Then block and time stores the block number and date-time at which the transaction occured.  
Then transactions_hash stores the transaction hash of the transaction.  
(Same block number can have a number of transactions but transaction hash is unique for each transaction involved).

* Collection model is used to store informations like traits, image url(which is used in web page),current owner, name and edition for each item.Except edition all other fields are charfield.

* Rarity model is used to store the item number or edition and its corresponding rarity number.(rarity number is calculated based on traits of the item and its calculation is discussed later).

* ItemType model is used to store the item number and its type.  
we are basically storing the items as either Type1 or Type2.  
Type1 items are those which are having sales or somewhat rare. These items are shown first in gallery enabling to show the good items first.

All the above models are automatically feeded into through functions.  

Though we have itemtype where if an itemtype has some sales to it, it is converted from Type2 to Type1.(it is updated through update_item_type function)

* WalletHistory is the model which comes into play when user connects there wallet to the website, this model stores the wallet address and the time at which it was connected.

# views.py:

In views.py we have some functions:

### def load_transactions_database(start_block,end_block):
This function processes from start_block to end_block and feeds it into Transactions model.
we are using "https://polygon-rpc.com" for this purpose.  

When we run this function though there is a high probability that the processing of the transaction fails, so we are using a retry mechanism such that the transaction which failed is processeed again and again until it succeeds.  

We use some functions from web3.eth objects like get_block, get_transaction_receipt, get_transaction and then we tweak the output received from these according to our needs. After many tests we found that processing 3000 blocks is the maximum effective way possible in this situation, so the function processes 3000 blocks at a time.  

get_transaction_receipt presents with one of the largest outputs and many information. This method has been used, to get info like to_address, from_address, which are not available in a straight forward way and are extracted after refining the data according to the requirement. Then after processing all the transactions, the entries are feeded in the database in a single go with bulk_create method.

### def load_collection_database():
This function helps in creating database with information like traits, current_owner, image_url for each item. Generally NFT's have metadata stored in the ipfs in json format.  
We have url "https://ipfs.io/ipfs/QmSXJSHP9uJzRzJoD8crZZ1RmAtqnNNZitLbpsmtZpCa5w/{i}.json" where "i" is the edition number for this collection.  
Now from this we can get information like image url(above url is the metadata url), traits(hats,mouths,backgrounds), edition, name from this url, then we use the transaction database to retrieve the latest owner of each item.

### load_rarity():
Lets understand rarity number first. Lets say an item has following traits: Background : background_x, Hat : hat_x, Mouth : mouth_x. Lets say in this collection 30 items has background_x as its background, 40 items has hat_x as its hat and 35 items has mouth_x as its mouth. Now the rarity number will be 30+40+35 = 105.

So with this function we take an item look for the traits get rarity number out of it and feed it into the database. We do this for "sort by rarity of traits" section in gallery, and "rarity rank" in owners page.

### load_item_type() and update_item_type():
we classify each items as Type_1 and Type_2.  

Initially Any item which has sales in it(we extract those items which has amount>0 in transactions) is considered Type_1. We have around 100 items at the time of writing. And take 32 rarest items from edition no. above 599. So totally we have 132 items as type1 initially.(132 was taken randomly and doesnt involve any logic or reason. In gallery if a row has 1,2,3 or 4 items per row 132 fits in.But taking 132 is not any rule).  

Type_2 is all the other items other than Type_1 items. In future if any items in Type_2 has sales than we can call update_item_type, to update the latest item types.  

We have made items to Type_1 and Type_2, so that we can always show the best items at the top in gallery page.

So these were some of the functions involved in views.py .

### Views:

### def_gallery(request) 
It involves gallery page.  

If its a get request then gallery page is rendered with some values in it.  

Post request is made when an user visits items-page (or stats page) and click on one of the traits,like:hat_x then gallery page opens up with hat_x filter pre-selected.

So we process the trait filter from post request and render gallery page accordingly.

### def_item(request,nft_id)  
This involves item-page.  

This page gives details about each item. we pass the edition as nft_id.  

We extract some transaction_hashes involving this edition and pass them, this is to lead them to polygonscan page to know extra details of that transaction.  

Then we pass background_percentage, hat_percentage_dict, mouth_percentage_dict to retrieve percentage of trait for that item. Also we pass the background_count, hat_count, mouth_count to retrieve number of items having that particular trait in the items page.

### def owner_page(request,address)
It involves owner page.  

This page shows items that this address owns and some other related informations. We pass the address through url and gain information involving that address. We create dict_activity because its one of the field for each item of owner page. Other info required to be passed are common and already processed.

### def stats_page(request) 
This is for stats page.  

This page shows stats of this whole collection. Here we pass sorted_count_of_counts, which will look like {'1 item': xx, '2 items':yy, '3 items':zz,..........}.i.e., This dictionary has owner distribution like how many wallets have 1 item, 2 items and so on.  

Then we have first_25_dict. This dict has top 25 collectors owning most items from the collection.Then we have time_count dictionary which tells no.of activities that took place every 6 months.

### def about(request),def home(request),def terms(request) 
This involves about, home and terms pages respectively. These are pretty straight forward and doesnt involve much functionalities.

We are passing dict_owner in all page because of the connect button in the menu, when we click connect then items belonging to that address will be stored in localstorage.

### def save_history(request) 
This doesnt involve any page. When user click connect button it saves the wallet address and time of connection. 


# How to run:

First let us locate some parts of code:  

-------------------------------------------------------------------------------------------------------------------    

(possibly in lines 318-324 or nearby in views.py)  
functions part 1:  
load_transactions_database(29936472,29936472)  
load_transactions_database(33131494,34247571)
load_transactions_database(44628933,44946017)
load_collection_database()  
print("-------------------------------------------------------------------------------------------")  
print("completed feeding collection and transaction data")  

-------------------------------------------------------------------------------------------------------------------

(possibly in lines 337-361 or nearby in views.py)  
part 1:  
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
    count = Collection.objects.filter  (Background=background).count()  
    background_counts[f"{background}"] = count

for hat in hat_list:  
    count = Collection.objects.filter(Hat=hat).count()  
    hat_counts[f"{hat}"] = count   

for mouth in mouth_list:  
    count = Collection.objects.filter(Mouth=mouth).count()  
    mouth_counts[f"{mouth}"] = count

-------------------------------------------------------------------------------------------------------------------

(possibly in lines 467-470 or nearby in views.py)  
functions part 2:  
load_rarity()  
load_item_type()  
print("completed feeding data")

-------------------------------------------------------------------------------------------------------------------

(possibly in lines 476-483 or nearby in views.py)  
part 2:  
items_type_1 = Itemtype.objects.filter(type_name="Type_1")  
list_of_tuples_1 = [(item.Name, item.type_name) for item in items_type_1]  
dict_1 = dict(list_of_tuples_1)

items_type_2 = Itemtype.objects.filter(type_name="Type_2")  
list_of_tuples_2 = [(item.Name, item.type_name) for item in items_type_2]  
dict_2 = dict(list_of_tuples_2)  

-------------------------------------------------------------------------------------------------------------------

(possibly in lines 510-517 or nearby in views.py)  
part 3:  
rarity_objects = Rarity.objects.all().order_by('Rarity_number')  
list_of_rarity_objects = [(item.Name, item.Rarity_number) for item in rarity_objects]  
dict_rarity = dict(list_of_rarity_objects)

owner_objects = Collection.objects.all()  
list_of_owner_objects = [(item.Edition, item.current_owner) for item in owner_objects]  
dict_owner = dict(list_of_owner_objects)

-------------------------------------------------------------------------------------------------------------------

These 5 sections are located:
functions part 1, part 1, functions part 2, part 2,part 3.


Now if we want to see the webpage with existing database, then we may uncomment the code in part 1, part 2 and part 3. And run "python manage.py runserver" to view the webpage.

If we want to load the database from scratch and then run the website, steps given below can be followed:  
* first migrate to zero.  
* Then makemigrations.  
* Then uncomment all 5 parts(functions part 1, part 1, functions part 2, part 2,part 3).  
* Now run python manage.py runserver.

load_transactions_database(29936472,29936472)  
load_transactions_database(33131494,34247571)  
load_transactions_database(44628933,44946017)  
These 3 function calls will take sometimes around 5 minutes.

load_collection_database()  
This will take around 2 minutes.

And other lines of code will take around 2 minutes as well.

So overall in about 10 minutes all the process will be completed.  
Now move to admin page you would see all the database feeded with data.  
Transactions will have around 2400 rows(2402 maybe).  
Collections, Raritys, Itemtypes will have 1049 or 1050 data.  
Now we may look at the website.

We have to comment out functions part 1, functions part 2 after completion of all the above processes. If we run "python manage.py runserver" again without commenting out these 2 sections then the database will be filled again.

Note:

-------------------------------------------------------------------------------------------------------------------

(possibly in lines 328-333 in views.py)  
note:  
#load_transactions_database are run for the above block intervals as only these blocks were involved for this nft collection.  
#may run the below load_transactions_database to process all blocks, which is time-consuming.  
web3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))  
load_transactions_database(0,web3.eth.block_number)  
#web3.eth.block_number is the latest block

-------------------------------------------------------------------------------------------------------------------

We may process all blocks as well, with above step but its highly time consuming.

**** This was the backend. ****

-----------------------------------------------------------------------------------------------------------------------

### Now we will look at the frontend:

# Menu
Menu in each page is a sticky navbar.  
It shows name on the left side and options on the right side.  
The menu leads us to home, about, gallery and stats page.  
We have 'more' option which is a dropdown leading us to social media, other useful links and terms page.  
Then it has a connect button. If we have metamask extension in our browser, then this works fine. We may need to install metamask extension to view how it works. If the Metamask extension is present, clicking on the "Connect" button in menu will result in extracting the wallet address and storing it in the WalletHistory database on the backend. It also involves storing the time at which wallet was connected. Also any item the wallet address holds from this collection will be stored in localstorage. Those items can be seen by checking "My items" checkbox in gallery page.


# gallery.html:
This page shows all the items of the collection. Clicking on an item leads us to that particular item's item-page.

### Shuffle:  
The items are showed in a random order. Clicking on shuffle will present us with different set of items.  
Actually we are having 2 parts(first 132 items or type_1 items, remaining or type2 items), clicking on shuffle will shuffle within first 132 cards and the remaining cards will shuffle within remaining cards ensuring that type_1 items are shown first, even after shuffling. If number of items to be displayed is less(240 or lesser), then it is shuffled in random order. If number of items to be displayed is more then it is shuffled in 2 parts.  
For code displaying above functionality look for shuffleButtonSmall(shuffle button for smaller screens) or shuffleButtonLarge(shuffle button for large screens) and related codes.

### Menu:

#### search:
If we enter a valid edition number then that item is displayed. If we enter an invalid edition number or alphabets or invalid characters alert message pops up and no item is displayed.  
For code displaying above functionality look for searchInput or performSearch() function and related codes.

#### Filter By:
It has dropdown menu with names:Backgrounds, hats, mouths.  
These helps in filtering out items based on traits. count of each value of backgrounds, hats, mouths is also shown.  
For code displaying above functionality look for handleFilterChange function and related codes.

#### My items:
It is used to show items belonging to connected wallet.  
The user needs to have metamask extension.If the user has metamask extension and is connected then items belonging to that wallet address will be displayed. If the user does not have metamask extension or is not connected then trying to check "My items" results in alert message being displayed and checkbox, wont be checked.  
On unchecking, all the items (or) items based on selected filters will be displayed.  
If this checkbox is checked and user disconnects then "My items" checkbox will be unchecked.  
For code displaying above functionality look for walletcheckbox, connectMetamask function and related codes.

#### Sort By:
#### Ascending:  
Checking this will arrange all items or filtered items in ascending order. Unchecking this will show the items in old or previous order.  
For code displaying above functionality look for sortAscendingCheckbox, sortAscending function and related codes.

#### Rarity of traits:
Checking this will arrange all items or filtered items on the basis of rarity(Most rare to least rare). Unchecking this will show the items in old or previous order.  
For code displaying above functionality look for sortRarityCheckbox,rarityKeys_2,rarityFilterElement and related codes. 

Also items can be sorted either by ascending order or rarity order, both cant be checked at the same time, if we attempt to check both, then previous sort by ascending or rarity checkboxes will be unchecked and latest will be checked.

#### Others:
We then have count:xx which shows the count of number items displayed.  
For code displaying above count functionality look for item-count and related codes. 

We have filters which shows all the checked or selected filters, if we uncheck it will be reflected as well.  
Number of filters selected is also displayed.  
If we click on filters element then that filter is removed and that particular checkbox is unchecked.  
Clicking on clear all results in removing or unchecking all selected filters.  
For code displaying above filter functionality look for dynamic-filters,dynamicFiltersContainer, addFilterElement and related codes. 

# stats.html:

This page consists of stats, graph and other useful informations about the collection.  

This page loads the latest available info, as it loads required information only after requesting the page.

First we have some general info. We have Rarest Hat, Rarest Background, Rarest Mouth with form in them clicking on them leads to the gallery page with that filter pre-selected in it.  

Then we have owner's Distribution pie chart, Hovering over them shows what they represent and their count.

All the graphs are done through chart.js.

Then we have table showing owner distribution and top collectors, both table's data are appended through javascript.

Clicking on a row in top collectors table leads us to owner-page of that particular address.

Then we have bargraph, Here we show the No.of activities that took place during certain time interval(6 months).  
This graph just represents the range and not the exact number of activity that took place over the time interval.  
Hovering over each bar shows time interval and exact count.

# item_page.html:

This page shows the information related to a particular item.

First we have the image of the item.

Then we have the traits which has forms in them, clicking on it leads us to the gallery page with that filter pre-selected in the gallery page.(Other info like no.of items having that trait and their percentage is also shown).

Then it shows the owner, clicking on it leads to the owner-page of that address.

Then we have transactions table showing the activities or transactions involving this particular item.
Clicking on a row leads us to polygonscan page involving that particular transaction(through transaction hash).

Then we have sales graph which shows the amount at which the item was previously sold at, clicking on a particular bar leads us to details of that transaction.

charts here is made with chart.js as well.

# owner_page.html:

First we have the address at the top, followed by no.of items that address owns in this collection, and buttons which leads us to opensea page and polygonscan page of that user.

Then each item with edition number, traits, rarity rank of that particular item and no,of activities in which this item is displayed. External links for that item is also provided as buttons.

# home.html, about.html, terms.html:

Home.html has 2 buttons, one leads to about page and another to gallery page.

about.html just explains about the collection.

terms.html explains the terms of usage of this whole site.

# styles.css:
'Gallery.html' loads css from 'styles.css' in static.

All pages are responsive.