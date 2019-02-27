import urlparse
from xml.sax.saxutils import escape as xml_escape

def append_item_filter(APIParams,itemFilter):
    itemFilters = APIParams.get('itemFilter',[])
    itemFilters.append(itemFilter)
    APIParams['itemFilter'] = itemFilters

def convert_location(webParams, APIParams):
    if 'LH_PrefLoc' in webParams:
        prefLoc = webParams['LH_PrefLoc']
        if prefLoc == '1': # country
            append_item_filter(APIParams,{'name':'LocatedIn', 'value':'FR'}) #TODO: get the country code fron the ebay-site GlobalId
        elif prefLoc == '2': # world
            raise Exception('Item location filter "worldwide" is not supported')
        elif prefLoc == '3': # europe
            raise Exception('Item location filter "Europe" is not supported')
        elif prefLoc == '4':
            raise Exception('Item location filter "Neighboring countries" is not supported')
        elif prefLoc == '98': # "predefined", seems to be no filtering.
            pass
        elif prefLoc == '99':
            # location filtering will be done by other converters, converting _sadis (MaxDistance) and _stpos (buyerPostalCode)
            assert '_stpos' in webParams
            assert '_sadis' in webParams
        del webParams['LH_PrefLoc']
        del webParams['_fslt'] # TODO: not sure what those params do

def translate_field_name(webParams, APIParams, web_field, API_field, value_translator):
    if web_field in webParams:
        v = value_translator(webParams[web_field])
        if v is not None:
            APIParams[API_field] = v
        del webParams[web_field]
def convert_simple(webParams, APIParams):
    translate_field_name(webParams, APIParams, '_nkw', 'keywords', lambda x:x)
    translate_field_name(webParams, APIParams, '_stpos', 'buyerPostalCode', lambda x:x)
    # translate_field_name(webParams, APIParams, '_dcat', 'categoryId', lambda x:x)
    translate_field_name(webParams, APIParams, '_sacat', 'categoryId', lambda x: x[0] if x[0] != '0' else None)

def translate_item_filter(webParams, APIParams, web_field, API_field, value_translator):
    if web_field in webParams:
        itemFilters = APIParams.get('itemFilter',[])
        try:
            itemFilter = next(x for x in itemFilters if x['name'] == API_field)
        except StopIteration:
            itemFilter = {'name':API_field, 'value':[]}
            itemFilters.append(itemFilter)
        for value in webParams[web_field].split('|'):
            itemFilter['value'].append(value_translator(value))
        APIParams['itemFilter'] = itemFilters
        del webParams[web_field]
def convert_itemFilter(webParams, APIParams):
    translate_item_filter(webParams, APIParams, 'LH_FS', 'FreeShippingOnly',    lambda x:{'1':'true'}[x])
    translate_item_filter(webParams, APIParams, 'LH_Auction',    'ListingType', lambda x:{'1':'Auction'}[x])
    translate_item_filter(webParams, APIParams, 'LH_BIN',        'ListingType', lambda x:{'1':'FixedPrice'}[x])
    translate_item_filter(webParams, APIParams, 'LH_CAds',       'ListingType', lambda x:{'1':'Classified'}[x])
    translate_item_filter(webParams, APIParams, 'LH_AllListings','ListingType', lambda x:{'1':'All'}[x])
    # TODO ListingType=AuctionWithBIN
    translate_item_filter(webParams, APIParams, '_sadis','MaxDistance', lambda x:x)
    translate_item_filter(webParams, APIParams, 'LH_ItemCondition','Condition',
        lambda x:{'3':'New','4':'Used','10':'Unspecified',
                 '1000':'1000', '1500':'1500', '1750':'1750', '2000':'2000', '2500':'2500',
                 '3000':'3000', '4000':'4000', '5000':'5000', '6000':'6000', '7000':'7000'}[x])
    if '_saslt' in webParams and '_fss' in webParams: del webParams['_fss']
    translate_item_filter(webParams, APIParams, '_saslt','SellerBusinessType', lambda x:{'1':'Private','2':'Business'}[x])

def convert_price(webParams, APIParams):
    for web_field, API_field in {"_udlo":"MinPrice", "_udhi":"MaxPrice"}.items():
        if web_field in webParams:
            append_item_filter(APIParams,{
                'name':API_field, 'value':webParams[web_field],
                'paramName':'Currency', 'paramValue':'EUR'}) #TODO USD according to region code
            del webParams[web_field]

def convert_dropper(webParams, APIParams):
    for key in [
        '_trksid', # partner network ?
        # 'rt', # always added
        '_from',
        '_mPrRngCbx',
        '_osacat', # not sure what this is
        '_odkw',   # old keyword ?
        ]:
        if key in webParams: del webParams[key]

def convert_seller(webParams, APIParams):
    if 'LH_SpecificSeller' in webParams:
        assert (webParams['LH_SpecificSeller'] == '1')
        itemFilterName = {'1':'Seller', '2':'ExcludeSeller'}[webParams['_saslop']]
        itemFilterValue = webParams['_sasl'] # TODO: exclude multiple sellers
        append_item_filter(APIParams,{'name':itemFilterName, 'value':itemFilterValue})
        del webParams['LH_SpecificSeller']
        del webParams['_saslop']
        del webParams['_sasl']

def drop_bell(s):
    if s.endswith('%5Cu0007'):
        s = s[:-len('%5Cu0007')]
    return s
def convert_aspectFilters(webParams, APIParams):
    for k,v in webParams.items():
        if k[0].isupper():
            assert (len(v) == 1); v = v[0]
            del webParams[k]
            aspectFilters = APIParams.get('aspectFilter',[])
            aspects = urlparse.unquote(v).split('|') # todo unicode ?
            aspects = ['Not Specified' if x == '!' else xml_escape(x) for x in aspects]
            k = drop_bell(xml_escape(k))
            aspectFilters.append({'aspectName':k, 'aspectValueName':aspects})
            APIParams['aspectFilter'] = aspectFilters

def parse_url(url):
    parsed = urlparse.urlparse(url)
    webParams = urlparse.parse_qs(parsed.query)
    input = webParams.copy()
    result = dict()
    splits = parsed.path.split('/')
    if splits[1] == 'sch' and len(splits) == 5:
        result['categoryId'] = splits[3]
        int(splits[3])
        assert(splits[4] == 'i.html')
    for c in [convert_location, convert_simple, convert_itemFilter, convert_price, convert_seller,
              convert_dropper, convert_aspectFilters]:
        c(input, result)
    for k,v in input.items():
        print 'warning: unmatched web param: ', k, v
    return result
