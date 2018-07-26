

import decimal
from onadata.apps.dashboard.forms import *
from django.db import connection
from onadata.apps.dashboard.models import *
import json
from onadata.apps.dashboard import utility_functions
import pandas as pd
import ast

import simplejson as sjson
import numpy as np
import xlwt
import os
from django.conf import settings

'''
***********************Table: Data Processing*******************************


******To Introdce New Chart:
1. Add chart type and acting functuan name in DashboardChartType Table
2. Implement that function (with exact same name!) inside TableConfig Class


Json generation Flow:
Get query
    |
    |query
    v
Run function to create DataFrame required for that Graph (From DashboardGenerator Table)
    |
    |Dataframe
    v
Run function to get json from chart type (From DashboardChartType Table)
'''

class TableConfig():
    """
    Table Functions.
    Creating JOSN for different charts
    """

    def __init__(self, graph_id, request, appearance):
        self.graph_id = graph_id
        self.dashboardGenerator= DashboardGenerator.objects.filter(id=self.graph_id).first()
        self.post_dict = request.POST
        self.request = request
        self.appearance = appearance


    def func_not_found(name_field, category_field, data_field, query):
        """
        Error Handler for Function calling from String
        """
        print "Exp: No Function Found!"
        return {}

    def execute_query(self, query):
        """
        Called From Outside
        :param chart_type: from DashboardChartType Table
        :param query: SQL
        :return: JSON/ HTML
        """
        jsondata = ''

        # GET DS Manipulator FUNCTION Name
        datasource_manipulator_func_name=getattr(self, self.dashboardGenerator.datasource_manipulator_func)
        dataset=datasource_manipulator_func_name(query)

        return dataset;


    def getDashboardDatatable(self, df):
        """
        For generating TABLE (USing Datatable.js)
        :param query: SQL QUERY
        :return: JSON Required For Datatable.js
        JSON STRUCTURE AS EXAMPLE:
        {"data": [["Good", 11], ["Medium", 12]], "col_name": ["Qualification", "Count"]}
        PRODUCED TABLE AS EXAMPLE:
        --------------------
        Qualification | Count
        ---------------------
        Good          |  11
        Medium        |  12

        **SQL Query Output same as to be produced one
        """
        data_list = []
        col_names = []
        col_names = list(df.columns.values)
        for row in df.iterrows():
            index, data = row
            data_list.append(data.tolist())
        return json.dumps({'col_name': col_names, 'data': data_list})

    def getDashboardDatatable(self, df):
        """
        For generating TABLE (USing Datatable.js)
        :param query: SQL QUERY
        :return: JSON Required For Datatable.js
        JSON STRUCTURE AS EXAMPLE:
        {"data": [["Good", 11], ["Medium", 12]], "col_name": ["Qualification", "Count"]}
        PRODUCED TABLE AS EXAMPLE:
        --------------------
        Qualification | Count
        ---------------------
        Good          |  11
        Medium        |  12

        **SQL Query Output same as to be produced one
        """
        data_list = []
        col_names = []
        col_names = list(df.columns.values)
        for row in df.iterrows():
            index, data = row
            data_list.append(data.tolist())
        return json.dumps({'col_name': col_names, 'data': data_list})

    def get_default(self,query):
        '''
        Use this function
        WHEN QUERY OUTPUT IS LIKE
        --------------------
        name   |category| value
        ------------------
        'Afrin'|'2017'  | 5.00
        'Arian'|'2016'  | 6.00
        ..................
        .................
        :param query:
        :return: JSON (panda dataframe. Structure
        name|category|value TO JSON)
        ..................
        ...................
        '''
        df = pd.read_sql(query, connection)
        return self.getDashboardDatatable(df)


    def get_pivoted(self,query):
        '''
        Use this function
        WHEN QUERY OUTPUT IS LIKE
        --------------------
        name   |category| value
        ------------------
        'Afrin'|'2017'  | 5.00
        'Arian'|'2016'  | 6.00
        ..................
        .................
        :param query:
        :return: HTML CODE
        ..................
        ...................

        '''
        table_html=""
        table_classes="dataframe_{element_id} display table table-bordered table-striped table-condensed table-responsive nowrap".format(element_id=self.dashboardGenerator.element_id)

        df = pd.read_sql(query, connection)
        if 'name_sorting' in  df:
            df = df.fillna(0)
            df = pd.pivot_table(df, values="value", rows=['name_sorting', "name"], cols=["category"])



        else:
            df = pd.pivot_table(df, values="value", rows=["name"], cols=["category"])
            df.index.name = 'Title'

        df = df.fillna(0)
        table_html = df.to_html(classes=table_classes)

        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)






    def get_transposed_df(self,query):
        '''
        Use this function
        WHEN QUERY OUTPUT IS LIKE
        col_1  | col_2 |col_3 |..................unlimited column
        ------------------------------------------
        33     | 2017  | 5.00 |


        :param query:
        :return: panda dataframe. Structure
        --------------
        category| value
        ---------------
        col_1   | 33
        col_2   | 2017
        col_3   | 5.00
        .............
        ............

        '''
        df = pd.read_sql(query, connection)
        df=df.T
        df['category'] = df.index
        df.columns=['value','category']
        return self.getDashboardDatatable(df)


    def get_outcome_progress_status(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE
        ..................
        ...................

        '''


        table_html=""
        df = pd.read_sql(query, connection)
        table_classes="dataframe_{element_id} display table table-bordered table-striped table-condensed table-responsive nowrap".format(element_id=self.dashboardGenerator.element_id)
        df = pd.pivot_table(df, values="value", rows=["name"], cols=["category"])
        df.index.name = 'Score'
        df = df.fillna(0)

        #Calculate Differce of two col and store it
        col_names=df.columns
        first_collection=0
        second_collection = 0
        if len(col_names)==2:
            first_collection = df[col_names[0]]
            second_collection = df[col_names[1]]
        elif len(col_names)==1:
            second_collection = df[col_names[0]]
        #STORE in a new column
        df['Progress']=second_collection-first_collection

        # Hide Column Name:  'Category' from Table
        df.columns.name = ""
        table_html = df.to_html(classes=table_classes)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)

    def activity_wmg_fund(self, query):
        '''
                BLUEGOLD Reporting
               :param query:
               :return: HTML CODE
               ..................
               ...................

               '''

        # print "table query"
        # print query
        table_html = ""
        df = pd.read_sql(query, connection)
        "getting index_name from column"
        col_length = len(df.columns.values)

        index_name = str(df[df.columns.values[col_length - 1]][0])
        print index_name
        table_classes = "dataframe_{element_id} display table cell-border".format(
            element_id=self.dashboardGenerator.element_id)
        df = pd.pivot_table(df, values="value", rows=["name"], cols=["category"])
        df.index.name = index_name
	print "trend1#########################3"
        print df
        df = df.sort_index(ascending=False, axis = 1)
        df = df.fillna(0)
        print "trend########################3"
        print df

        # Calculate Differce of two col and store it
        col_names = df.columns
        print col_names
        first_collection = 0
        second_collection = 0
        if len(col_names) == 2:
            first_collection = df[col_names[0]]
            second_collection = df[col_names[1]]
        elif len(col_names) == 1:
            second_collection = df[col_names[0]]
        # STORE in a new column
        df['Progress'] = second_collection - first_collection
        print "activities of wmg fund"
	
	#df = df.sort_index(ascending=False, axis = 1)
        sum_row = {col: df[col].sum() for col in df}

        print sum_row

        sum_df = pd.DataFrame(sum_row, index=["Total"])
        print sum_df

        # Hide Column Name:  'Category' from Table
        df = df.append(sum_df)
	col_names = col_names.tolist() +['Progress']
	df = df.reindex_axis(col_names,axis=1)
	print "checking"
        print df
        df.index.name = index_name
        df.columns.name = ""
	#df = df.sort_index(ascending=False, axis = 1)
        table_html = df.to_html(classes=table_classes)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)

    def get_outcome_progress_trend(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE
        ..................
        ...................

        '''

        # print "table query"
        # print query

        
        table_html=""
        df = pd.read_sql(query, connection)
        flag = False
        if "col_name" in df:
            flag = True
        "getting index_name from column"
        col_length =  len(df.columns.values)

        index_name = str(df[df.columns.values[col_length-1]][0])
        print index_name
        table_classes="dataframe_{element_id} display table cell-border".format(element_id=self.dashboardGenerator.element_id)
        if flag:
            df = pd.pivot_table(df, values="value", rows=["name"], cols=["category", "col_name"])
        else:
            df = pd.pivot_table(df, values="value", rows=["name"], cols=["category"])

        df.index.name = index_name
        df = df.fillna(0)
	
        print "trend eco table of use"
        print df

        # Calculate Differce of two col and store it
        col_names = df.columns
        print col_names
        first_collection = 0
        second_collection = 0
        if len(col_names) == 2:
            first_collection = df[col_names[0]]
            second_collection = df[col_names[1]]
        elif len(col_names) == 1:
            second_collection = df[col_names[0]]
        # STORE in a new column
        df['Progress'] = second_collection - first_collection

        #Hide Column Name:  'Category' from Table
        if flag:
            df.columns.names=["",""]
        else:
            df.columns.names = [""]

        table_html = df.to_html(classes=table_classes)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)

    def use_wmg_fund(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE
        ..................
        ...................

        '''

        # print "table query"
        # print query

        
        table_html=""
        df = pd.read_sql(query, connection)
        flag = False
        if "col_name" in df:
            flag = True
        "getting index_name from column"
        col_length =  len(df.columns.values)

        index_name = str(df[df.columns.values[col_length-1]][0])
        print index_name
        table_classes="dataframe_{element_id} display table cell-border".format(element_id=self.dashboardGenerator.element_id)
        if flag:
            df = pd.pivot_table(df, values="value", rows=["name"], cols=["category", "col_name"])
        else:
            df = pd.pivot_table(df, values="value", rows=["name"], cols=["category"])

        df.index.name = index_name
        df = df.fillna(0)
	df = df.sort_index(ascending=False, axis = 1)
        print "trend eco table of use"
        print df

        # Calculate Differce of two col and store it
        col_names = df.columns
        print col_names
        first_collection = 0
        second_collection = 0
        if len(col_names) == 2:
            first_collection = df[col_names[0]]
            second_collection = df[col_names[1]]
        elif len(col_names) == 1:
            second_collection = df[col_names[0]]
        # STORE in a new column
        df['Progress'] = second_collection - first_collection

        #Hide Column Name:  'Category' from Table
        if flag:
            df.columns.names=["",""]
        else:
            df.columns.names = [""]

	col_names = col_names.tolist() +['Progress']
	df = df.reindex_axis(col_names,axis=1)
        table_html = df.to_html(classes=table_classes)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)


    def get_outcome_progress_trend_v2(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE
        ..................
        ...................

        '''

        # print "table query"
        # print query
        table_html=""
        df = pd.read_sql(query, connection)
        "getting index_name from column"
        col_length =  len(df.columns.values)

        index_name = str(df[df.columns.values[col_length-1]][0])
        print index_name
        table_classes="dataframe_{element_id} display table cell-border".format(element_id=self.dashboardGenerator.element_id)
        df = pd.pivot_table(df, values="value", rows=["sl","Activities"], cols=["category"])
        df.index.name = index_name
        df = df.fillna(0)
	df = df.sort_index(ascending=False, axis = 1)
        print "trend"
        #print df

        # Calculate Differce of two col and store it
        col_names = df.columns
        print col_names
        first_collection = 0
        second_collection = 0
        if len(col_names) == 2:
            first_collection = df[col_names[0]]
            second_collection = df[col_names[1]]
        elif len(col_names) == 1:
            second_collection = df[col_names[0]]
        # STORE in a new column
        df['Progress'] = second_collection - first_collection

        #Hide Column Name:  'Category' from Table
        df.columns.name=""

        col_names = col_names.tolist() +['Progress']
	df = df.reindex_axis(col_names,axis=1)
        table_html = df.to_html(classes=table_classes)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)







    def get_polder_wise_avg_progress_marker_score(self,query):
        '''
         NEW NAME:::  Polder Wise WMG Performance Level
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE
        ..................
        ...................

        '''
        param_val = self.post_dict['calculation_type']


        table_html=""
        # query = "with q as(with p as(with t as(SELECT polder,district,extract(year from reporting_month::date) yr,extract(month from reporting_month::date) mn, name_wmg,round((sum(rank1_pm11+rank1_pm12+rank1_pm13+rank1_pm14+rank1_pm15+rank1_pm16+rank1_pm17+rank2_pm21+rank2_pm22+rank2_pm23+rank2_pm24+rank2_pm25+rank2_pm26+rank3_pm31+rank3_pm32+rank3_pm33+rank4_pm41+rank4_pm42+rank4_pm43+rank4_pm44)*100.0)/(count(*)*60.0),2) qualification ,reporting_month FROM vwparticipatory_monitoring where reporting_month=any(select distinct reporting_month from vwparticipatory_monitoring where reporting_month is not null and reporting_month::text='2017-04-01 00:00:00' order by reporting_month desc limit 1) group by name_wmg,district, polder,extract(year from reporting_month::date),extract(month from reporting_month::date),reporting_month) select polder,district, name_wmg,yr,reporting_month ,(case when qualification>=80 then 'High Performance' when qualification>=70 then 'Upper Medium Performance' when qualification>=60 then 'Medium Performance' when qualification>=50 then 'Upper Low Performance' else 'Low Performance' end) qualification , (case when qualification>=80 then 1 when qualification>=70 then 2 when qualification>=60 then 3 when qualification>=50 then 4 else 5 end) as name_sorting from t) select polder as \"Polder\",(select name from geo_district where code=district) as \"District\", name_sorting ,qualification as name ,count(distinct name_wmg) as value from p group by polder,district,name_sorting,qualification),s as(select \"District\",\"Polder\",sum(value) total from q  group by \"District\",\"Polder\")select q.\"Polder\",q.\"District\",name_sorting,name,round((value*100)/(select total from s where s.\"District\"=q.\"District\" and s.\"Polder\"=q.\"Polder\"),2) from q order by \"District\",\"Polder\" "
        #query="with p as(with t as(SELECT polder,district,name_wmg,extract(year from reporting_month::date) yr,extract(month from reporting_month::date) mn, round((rank1_pm11+rank1_pm12+rank1_pm13+rank1_pm14+rank1_pm15+rank1_pm16+rank1_pm17+rank2_pm21+rank2_pm22+rank2_pm23+rank2_pm24+rank2_pm25+rank2_pm26+rank3_pm31+rank3_pm32+rank3_pm33+rank4_pm41+rank4_pm42+rank4_pm43+rank4_pm44)*100.0/60.0,2) qualification ,reporting_month FROM vwparticipatory_monitoring where reporting_month=any(select distinct reporting_month from vwparticipatory_monitoring where reporting_month is not null and reporting_month::text='2017-04-01 00:00:00' order by reporting_month desc limit 1) ) select polder,district, name_wmg,yr,reporting_month ,(case when qualification>=80 then 'High Performance' when qualification>=70 then 'Upper Medium Performance' when qualification>=60 then 'Medium Performance' when qualification>=50 then 'Upper Low Performance' else 'Low Performance' end) qualification , (case when qualification>=80 then 1 when qualification>=70 then 2 when qualification>=60 then 3 when qualification>=50 then 4 else 5 end) as name_sorting from t) select polder as \"Polder\",(select name from geo_district where code=district) as \"District\", name_sorting ,qualification as name ,count(distinct name_wmg) as value from p group by qualification,yr, name_sorting,polder,district"
        df = pd.read_sql(query, connection)
        table_classes="dataframe_{element_id} display table table-bordered table-striped table-condensed table-responsive nowrap".format(element_id=self.dashboardGenerator.element_id)
        #df = pd.pivot_table(df, values="value", rows=["District","Polder"], cols=["name_sorting","name"] ,aggfunc=len, margins=True, dropna=True,fill_value=0)
        df = pd.pivot_table(df, values="value", rows=["District", "Polder"], cols=["name_sorting", "name"],
                            fill_value = 0,  dropna = True)
        df['Total'] = df.sum(axis=1)
	df.ix[('Total',''), :] = df.sum()
	df = np.round(df)
        if param_val =='Percentage':
            df = df.div( df.Total, axis='index')
            print "test"
            df = 100*np.round(df, decimals=3)
        # margins = True, dropna = True,

        df.index.name = 'Qualification'
        df = df.fillna(0)
        print "average progress marker score"
        #print df
        #Hide Column Name
        #HIde name and name_soring Col name
        df.columns.names=["",""]

        table_html = df.to_html(classes=table_classes)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)


    def get_polder_wise_wmg_performance(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE of TABLE
        '''
        param_val = self.post_dict['theme']
        filtering_options = sjson.loads(str(self.dashboardGenerator.filtering), strict=False)
        print (type(filtering_options))
        # filtering_option = self.dashboardGenerator.filtering

        if param_val in filtering_options:
            query = filtering_options.get(param_val)
        table_html = ""


        print "query for performance"
        print query
        df = pd.read_sql(query, connection)
        print "original data"
        print df

        table_classes = "dataframe_{element_id} display table table-bordered cell-border".format(
            element_id=self.dashboardGenerator.element_id)
        df = pd.pivot_table(df, values="value", rows=["district","polder"], cols=["title","category"])
        # dg = pd.pivot_table(df, values="value", index=["district", "polder"], cols=["title", "category"], aggfunc=len)
        df.index.name = 'Qualification'
        df = df.fillna(0)
        df = np.round(df, decimals=3)
        # print "performance"
        # print self.post_dict
        # Calculate Differce/Progress of two col in  each section and store it
        print "dataframe"
        #print df
        for column in df:
            #PArent column have 1/2 child col
            print column
            child_col_names = df[column[0]].columns
            print "child"
            print child_col_names
            first_collection = 0
            second_collection = 0
            if len(child_col_names) == 2:
                first_collection = df[column[0],child_col_names[0]]
                second_collection = df[column[0],child_col_names[1]]
            elif len(child_col_names) == 1:
                second_collection = df[column[0],child_col_names[0]]
            elif len(child_col_names) == 3:
                #After Progress added, 2nd iteration would be 3
                continue;
            # STORE in a new column
            df[column[0],'Progress'] = second_collection - first_collection


        # Hide Column Name
        df.columns.names = ["", ""]

        table_html = df.to_html(classes=table_classes)

        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)


    def test_eco_activity(self, query):
        df = pd.read_sql(query, connection)

        table_classes = "dataframe_{element_id} display table table-bordered cell-border".format(
            element_id=self.dashboardGenerator.element_id)
        df = df.pivot( values="value", index="Activities", columns=["category", "name"])
        # dg = pd.pivot_table(df, values="value", index=["district", "polder"], cols=["title", "category"], aggfunc=len)
        df.index.name = 'Activities'
        df = df.fillna(0)

        # df.columns.names = ["", "", ""]

        table_html = df.to_html(classes=table_classes)

        return table_html

    def eco_dev_activity(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE of TABLE
        '''
        df = pd.read_sql(query, connection)

        table_classes = "dataframe_{element_id} display table table-bordered cell-border".format(
            element_id=self.dashboardGenerator.element_id)
        print "getting index_name from column"
        col_length =  len(df.columns.values)

        index_name = str(df[df.columns.values[col_length-1]][0])
        print index_name
        df = pd.pivot_table(df,values=["value"],  rows=["Activities"],  cols=["category","name"])
        # dg = pd.pivot_table(df, values="value", index=["district", "polder"], cols=["title", "category"], aggfunc=len)
        df.index.name = index_name
        df = df.fillna(0)
	df = df.sort_index(ascending=False, axis = 1)
	#dropping one level of complex header
        df.columns = df.columns.droplevel([0])
	df = df.sort_index(ascending=False, axis = 1)
	
	#current columns tuple
	col_names = df.columns
	col = []
	#taking progress at last position
	for f in col_names:
	    if 'Progress' not in f[0]:
		col.append(f)
	for f in col_names:
            if 'Progress' in f[0]:
		col.append(f)
	#reindexing according to order
	df = df.reindex_axis(col,axis=1)
        # Hide Column Name
        df.columns.names = ["",""]

        table_html = df.to_html(classes=table_classes)

        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)






    def eco_investment_iga(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE of TABLE
        '''
        df = pd.read_sql(query, connection)
        print "original data"
        print df
        print "getting index_name from column"
        col_length =  len(df.columns.values)

        index_name = str(df[df.columns.values[col_length-1]][0])
        table_classes = "dataframe_{element_id} display table table-bordered cell-border".format(
            element_id=self.dashboardGenerator.element_id)
        print "sort"
        df =df.sort('name', ascending=False)
        df = pd.pivot_table(df,values=["value"],  rows=["Activities"],  cols=["category","name"])
        df.index.name = index_name
        df = df.fillna(0)
        # dropping level one step
        df.columns = df.columns.droplevel([0])
        "getting column names"
        idx = df.columns
        col = idx.tolist()

        "getting list of values"
        percentage = []
        if len(col)==6:
            quarter_fund = df[col[3]].tolist()
        else:
            quarter_fund = df[col[1]].tolist()

        total_fund = 0
        for f in quarter_fund:
            total_fund = total_fund+int(f)

        for f in quarter_fund:
            percent = float(f)/total_fund*100
            percentage.append(percent)


        percentage = np.round(percentage, decimals=2)


        df['Percentage of total investment (Last quarter)'] = percentage
        #print df['Progress','No. of person involved']
        df.ix[('Total Fund Invested in IGAs'), :] = df.sum()
        #print df.index.values
        df.columns.names = ["",""]

        table_html = df.to_html(classes=table_classes)
        #func_name = getattr(self,excel_file)
        filename = self.excel_file(df)
        data = {'table': table_html,
                'filename': filename}
        # print table_html
        return json.dumps(data)


        # return table_html



    def excel_file(self, df):
        
        file = 'pandas_simple_' + self.graph_id
        if 'title' in self.appearance:
            file = str(self.appearance['title'])
            file = file.replace(' ', '_')

        # current_user = UserModuleProfile.objects.filter(user=user)
        user_path_filename = os.path.join(settings.MEDIA_ROOT, self.request.user.username)
        user_path_filename = os.path.join(user_path_filename, "exported_file")
        if not os.path.exists(user_path_filename):
            os.makedirs(user_path_filename)

        filename = os.path.join(user_path_filename, file + '.xls')

        writer = pd.ExcelWriter(filename, engine='xlwt')
        # Convert the dataframe to an XlsxWriter Excel object.
        df.to_excel(writer, sheet_name='Sheet1')

        # Close the Pandas Excel writer and output the Excel file.
        

        writer.save()

        return file+'.xls'

"""
END OF Table Config
"""

