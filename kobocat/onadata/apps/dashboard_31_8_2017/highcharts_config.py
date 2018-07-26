
import decimal
from onadata.apps.dashboard.forms import *
from django.db import connection
from onadata.apps.dashboard.models import *
import json
from onadata.apps.dashboard import utility_functions
import pandas as pd


'''
***********************Highcharts: Data Processing*******************************
Link: https://www.highcharts.com/demo/line-basic



******To Introdce New Chart:
1. Add chart type and acting functuan name in DashboardChartType Table
2. Implement that function (with exact same name!) inside HighchartsConfig Class


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

class HighchartsConfig():
    """
    HighCharts Functions.
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

    def execute_query(self,chart_type, query):
        """
        Called From Outside
        :param chart_type: from DashboardChartType Table
        :param query: SQL
        :return: JSON
        """
        jsondata = ''
        control_func_name = chart_type.function_name

        # GET DS Manipulator FUNCTION Name
        datasource_manipulator_func_name=getattr(self, self.dashboardGenerator.datasource_manipulator_func)
        df=datasource_manipulator_func_name(query)


        #GET CHART GENERATOR FUNCTION
        control_function = getattr(self, control_func_name)
        jsondata = control_function('name','category','value',df)
        return jsondata;

    def date_handler(self,obj):
        return obj.isoformat() if hasattr(obj, 'isoformat') else obj

    def decimal_default(self,obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        raise TypeError

    def getUniqueValues(self,dataset, colname):
        list = [];

        for dis in dataset:
            if dis[colname] in list:
                continue;
            else:
                list.append(dis[colname]);
        return list;


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
        :return: panda dataframe. Structure
        name|category|value
        ..................
        ...................

        '''
        df = pd.read_sql(query, connection)
        return df

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
        return df


    def generate_json_bar_line_area_Chart(self,name_field, category_field, data_field,df):
        """
        Line Chart
        Horizontal Bar Chart
        Basic Area Chart
        @author:Emtious
        :param category_field:
        :param data_field:
        :param query:
        :return: JOSN
        """

        seriesData = []
        category_list = ""
        category_list = df[category_field].values.tolist()
        dict = {}
        dict['data']=df[data_field].values.tolist()
        seriesData.append(dict)

        jsonForChart = json.dumps({'categories': category_list, 'seriesdata': seriesData}, default=self.decimal_default)
        return jsonForChart


    def generate_json_column_area_chart(self, name_field, category_field, data_field,dataframe):
    #def generate_json_column_area_chart(self, dataframe):
        """
        Percentage/Normal Multiple Area Chart
        Percentage/Normal Multiple Stack Chart
        Percentage/Normal Multiple Column Chart

        :param name_field:
        :param category_field:
        :param data_field:
        :param query:
        :return: JSON


        REQUIRED DF TYPE AS EXAMPLE:
        TYPE 1:
        name       | category       | data
        ---------------------------------
         Tokyo     |  Jan           |  10
         Tokyo     |  Feb           |  23
         New York  |  Feb           |  22
         Barlin    |  Mar           |  34
         ...............................
         ................................

        TYPE 2:
        name       | category       | data | colors| name_sorting |  category_sorting
        ------------------------------------------------------------------------------
         Tokyo     |  Jan           |  10  | #ff1  | 1            |            1
         Tokyo     |  Feb           |  23  | #fff  | 1            |            2
         New York  |  Feb           |  22  | #fff  | 2            |            2
         Barlin    |  Mar           |  34  | #ff2  | 3            |            3
         ............................................................................
         ..............................................................................

        colors-> of each category
        name_sorting-> sorting of name field
        colors-> sorting of category field
        **Generated graph of this here http://jsfiddle.net/gh/get/library/pure/highcharts/highcharts/tree/master/samples/highcharts/demo/column-basic/

        """
        df=dataframe
        seriesData = []
        category_list = ""
        if df.empty == False:
            if "colors" in df and "name_sorting"  in df and "category_sorting" in df:
                df = pd.pivot_table(df, values=data_field, rows=['name_sorting',name_field,'colors' ],
                                    cols=["category_sorting", category_field])
                df = df.fillna(0)
                # Check in Name Sorting order defined or not
                appearance = json.loads(self.dashboardGenerator.chart_object)
                name_sorting_ascending = True
                if "name_sorting_ascending" in appearance:
                    name_sorting_ascending = appearance["name_sorting_ascending"]

                df = df.sort_index(ascending=name_sorting_ascending)
                category_list = []
                for data in df.columns.values:
                    category_list.append(data[1])

                for row in df.iterrows():
                    dict = {}
                    index, data = row
                    dict['name'] = index[1]
                    dict['data'] = data.tolist()
                    dict['color'] = index[2]
                    seriesData.append(dict)

            else:
                df = df.pivot(index=name_field, columns=category_field, values=data_field)
                df = df.fillna(0)
                category_list = list(df.columns.values)
                for row in df.iterrows():
                    dict = {}
                    index, data = row
                    dict['name'] = index
                    dict['data'] = data.tolist()
                    seriesData.append(dict)


        jsonForChart = json.dumps({'categories': category_list, 'seriesdata': seriesData}, default=self.decimal_default)
        return jsonForChart



    def generate_json_pie_chart(self, query):
        """
        Pie Chart
        :param name_field:
        :param category_field:
        :param data_field:
        :param query:
        :return:
        """
        category_field = 'category'
        data_field = 'value'
        name_field = 'name',
        dataset = utility_functions.db_fetch_values_dict(query)
        seriesData = []
        for data in dataset:
            dict = {}
            dict['name'] = data[name_field]
            dict['y'] = data[data_field]
            seriesData.append(dict)

        jsonForChart = json.dumps({'seriesdata': [{'name': name_field, 'data': seriesData}]}, default=self.decimal_default)

        return jsonForChart


"""
END OF Highcharts Config
"""
