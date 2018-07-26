
import decimal
from onadata.apps.dashboard.forms import *
from django.db import connection
from onadata.apps.dashboard.models import *
import json
from onadata.apps.dashboard import utility_functions
import pandas as pd


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

    def __init__(self, graph_id):
        self.graph_id = graph_id
        self.dashboardGenerator= DashboardGenerator.objects.filter(id=self.graph_id).first()


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









        return table_html


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
            first_collection = df[col_names[0]]
        #STORE in a new column
        df['Progress']=first_collection-second_collection

        table_html = df.to_html(classes=table_classes)
        return table_html


    def get_outcome_progress_trend(self,query):
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
        df.index.name = 'Qualification'
        df = df.fillna(0)

        # Calculate Differce of two col and store it
        col_names = df.columns
        first_collection = 0
        second_collection = 0
        if len(col_names) == 2:
            first_collection = df[col_names[0]]
            second_collection = df[col_names[1]]
        elif len(col_names) == 1:
            first_collection = df[col_names[0]]
        # STORE in a new column
        df['Progress'] = first_collection - second_collection


        table_html = df.to_html(classes=table_classes)
        return table_html

    def get_polder_wise_avg_progress_marker_score(self,query):
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
        df = pd.pivot_table(df, values="value", rows=["District","Polder"], cols=["name"] ,aggfunc=len, margins=True, dropna=True,fill_value=0)
        df.index.name = 'Qualification'
        df = df.fillna(0)
        #append total col in each row
        #df['Total'] = df.sum(axis=1)
        table_html = df.to_html(classes=table_classes)
        return table_html


    def get_polder_wise_wmg_performance(self,query):
        '''
         BLUEGOLD Reporting
        :param query:
        :return: HTML CODE of TABLE
        '''
        table_html = ""
        df = pd.read_sql(query, connection)
        table_classes = "dataframe_{element_id} display table table-bordered table-striped table-condensed table-responsive nowrap".format(
            element_id=self.dashboardGenerator.element_id)
        df = pd.pivot_table(df, values="value", rows=["District","Polder"], cols=["name","category"])
        df.index.name = 'Qualification'
        df = df.fillna(0)


        # Calculate Differce/Progress of two col in  each section and store it
        for column in df:
            #PArent column have 1/2 child col
            child_col_names = df[column[0]].columns
            first_collection = 0
            print  len(child_col_names), "          "
            second_collection = 0
            if len(child_col_names) == 2:
                first_collection = df[column[0],child_col_names[0]]
                second_collection = df[column[0],child_col_names[1]]
            elif len(child_col_names) == 1:
                first_collection = df[column[0],child_col_names[0]]
            elif len(child_col_names) == 3:
                #After Progress added, 2nd iteration would be 3
                continue;
            # STORE in a new column
            df[column[0],'Progress'] = first_collection - second_collection

        table_html = df.to_html(classes=table_classes)


        return table_html


"""
END OF Table Config
"""
