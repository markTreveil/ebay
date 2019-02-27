# -*- coding: utf-8 -*-
import dataiku
import pandas as pd
import ebaysdk.exception, ebaysdk.shopping
from dataiku.customrecipe import *

input_name = get_input_names_for_role('input_dataset')[0]
df_in = dataiku.Dataset("RAM_cache").get_dataframe()

includeSelectors = ["Details", "ItemSpecifics", "ShippingCosts", "Description", "TextDescription", "Variations"]
includeSelectors = ",".join([name for name in includeSelectors if get_recipe_config().get("include_"+name,None)])

api = ebaysdk.shopping.Connection(appid=get_recipe_config()['ebay_app_id'],config_file=None,
      siteid=71, #'EBAY-FR',
      https=False,debug=False,timeout=30) # TODO https

i=0
chunksize = 20
results = []
nb_rows = df_in.shape[0]
while i < nb_rows:
    itemIDs = df_in.itemId[ i:min(nb_rows,i+chunksize) ]
    i += chunksize
    try:
        response = api.execute('GetMultipleItems', {"ItemID":list(itemIDs), "IncludeSelector":includeSelectors})
        assert(response.reply.Ack in ['Warning', 'Success']) # ebaysdk prints the structured error in case of warning
    except (ebaysdk.exception.ConnectionError, AssertionError, AttributeError) as e:
        print e
        print response.dict()
        raise
    results.extend(response.dict()['Item'])
    if i%100 == 0:
        print "read",i,"rows"

df_out = pd.DataFrame(results)
output_name = get_output_names_for_role('output_dataset')[0]
dataiku.Dataset(output_name).write_with_schema(df_out)
