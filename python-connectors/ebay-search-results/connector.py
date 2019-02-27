# coding: utf-8
import urlparse, sys
import pandas as pd, datetime as dt
import lxml.etree as etree#, xml.dom.minidom
import ebaysdk, ebaysdk.utils, ebaysdk.exception, ebaysdk.finding

from dataiku.connector import Connector
import dataiku

import ebay_utils


class MyConnector(Connector):
    def __init__(self, config):
        Connector.__init__(self, config)  # pass the parameters to the base class

    def get_read_schema(self):
        return None

    def get_partitioning(self):
        return {
            "dimensions": [{
                "name" : "day",
                "type" : "time",
                "params" : {"period" : "DAY"}
            }]
        }

    def generate_rows(self, dataset_schema=None, dataset_partitioning=None, partition_id=None, records_limit = -1):
        try:
            beg_date = dt.datetime.strptime(partition_id, "%Y-%m-%d")
            end_date = beg_date + dt.timedelta(days=1)
            api = ebaysdk.finding.Connection(appid=self.config['ebay_app_id'],config_file=None,warnings=True,
                siteid='EBAY-FR', timeout=30,debug=False,https=False) # TODO https
            API_params = ebay_utils.parse_url(self.config['website_search_url'])
            if 'xml_query' in self.config and self.config['xml_query']:
                raise Exception("not implemented yet")   #TODO

            # ensure "itemFilter" exists and has no StartTimeFrom / StartTimeTo entries, then add this filter:
            if "itemFilter" not in API_params:
                API_params["itemFilter"] = []
            else:
                API_params["itemFilter"] = [v for v in API_params["itemFilter"]
                    if "name" not in v.keys() or v["name"] not in ["StartTimeFrom", "StartTimeTo"]]
            API_params["itemFilter"].append({"name":"StartTimeFrom", "value":beg_date.strftime("%Y-%m-%dT%H:%M:%S."+"000Z")})
            API_params["itemFilter"].append({"name":"StartTimeTo",   "value":end_date.strftime("%Y-%m-%dT%H:%M:%S."+"000Z")})

            print 'API_params: ', API_params
            xml = '<findItemsAdvancedRequest>' +ebaysdk.utils.dict2xml(API_params)+ '</findItemsAdvancedRequest>'
            print 'as XML:\n', etree.tostring(etree.fromstring(xml), pretty_print = True)
            # print 'as XML: ', xml.dom.minidom.parseString(xml).toprettyxml()
            sys.stdout.flush()
            nb_records = 0
            page = 1
            if "paginationInput" not in API_params:
                API_params["paginationInput"] = {}
            while page:
                API_params["paginationInput"]["pageNumber"] = page
                response = api.execute('findItemsAdvanced', API_params)
                if api.error():
                    print "has errors: %s" % api.error()
                assert(response.reply.ack == 'Success')

                searchResult = response.dict()['searchResult']
                pagination = response.reply.paginationOutput
                nb_pages = int(pagination.totalPages)
                nb_records += int(searchResult['_count'])
                print "got {}/{} pages, {}/{} records".format(pagination.pageNumber, nb_pages, nb_records, pagination.totalEntries)
                if searchResult['item'] is not None:
                    for row in searchResult['item']:
                        yield row
                else:
                    print "no results"
                    return
                if page == 100: print "Max nb pages reached"
                if page < nb_pages and (records_limit == -1 or nb_records < records_limit) \
                    and page < 100: # see http://developer.ebay.com/devzone/finding/callref/finditemsadvanced.html#Request.paginationInput
                    page += 1
                else:
                    page = None

        except (ebaysdk.exception.ConnectionError, AssertionError) as e:
            print(e)
            print(response.dict())
            raise
