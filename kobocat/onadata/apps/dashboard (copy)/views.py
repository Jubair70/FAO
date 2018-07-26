import decimal
import simplejson
#from distutils.command.config import config
#from mercurial.dispatch import request

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.db.models import Count, Q
from django.http import (HttpResponseRedirect, HttpResponse)
from django.shortcuts import render_to_response, get_object_or_404, render
from onadata.apps.dashboard.forms import *
from django.db.models import ProtectedError
from django.db import connection
from django.db.models import Max, Sum
from onadata.apps.dashboard.models import *
import json
from datetime import *
from django.forms.models import inlineformset_factory
from collections import OrderedDict
from django.forms.formsets import BaseFormSet

from dateutil.relativedelta import relativedelta
from django.shortcuts import redirect

from django.views.decorators.csrf import csrf_exempt
from onadata.apps.dashboard import utility_functions

# *************************** Household (hh) Module *****************************************



'''
Lis of Constants for sla meeting
@persia
'''
DS_QUERY='1'
DS_URL='2'
DS_STATIC_JSON='3'
DS_NOT_APPLICABLE='4'



"""
Prepare json of given query for data table
@persia
"""


def index(request):
    return render(request,"dashboard/index.html")

def getDashboardDatatable(query):
    data_list = []
    col_names = []
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall();
    col_names = [i[0] for i in cursor.description]
    #col_names.append('Action')
    for eachval in fetchVal:
        # delete_button = '<a class="delete-program-item tooltips" data-placement="top" href="#" data-original-title="Delete Program"  onclick="delete_program('+ str(eachval[0]) +')"><i class="fa fa-2x fa-trash-o"></i></a>'
        delete_button = ''
        edit_button = '<a class="tooltips" data-placement="top" data-original-title="Edit Program" href="#" onclick="edit_entity(' + str(
            eachval[0]) + ');"><i class="fa fa-2x fa-pencil-square-o"></i></a>' + ' '
        #eachval = eachval + (edit_button,)
        data_list.append(list(eachval))
    return json.dumps({'col_name': col_names, 'data': data_list})


def getDatatable(query):
    data_list = []
    col_names = []
    cursor = connection.cursor()
    cursor.execute(query)
    fetchVal = cursor.fetchall();
    col_names = [i[0] for i in cursor.description]
    col_names.append('Action')
    for eachval in fetchVal:
        delete_button = '<a class="delete-program-item tooltips" data-placement="top" href="#" data-original-title="Delete"  onclick="delete_entity('+ str(eachval[0]) +')"><i class="fa fa-2x fa-trash-o"></i></a>'
        #delete_button = ''
        edit_button = '<a class="tooltips" data-placement="top" data-original-title="Edit Program" href="#" onclick="edit_entity(' + str(
            eachval[0]) + ');"><i class="fa fa-2x fa-pencil-square-o"></i></a>' + ' ' + delete_button
        eachval = eachval + (edit_button,)
        data_list.append(list(eachval))
    return json.dumps({'col_name': col_names, 'data': data_list})



'''
highcharts Graph Generation Functions Type Wise
'''

def date_handler(obj):
    return obj.isoformat() if hasattr(obj, 'isoformat') else obj


def decimal_default(obj):
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    raise TypeError


def getUniqueValues(dataset, colname):
    list = [];

    for dis in dataset:
        if dis[colname] in list:
            continue;
        else:
            list.append(dis[colname]);
    return list;



def generate_json_bar_line_area_Chart(category_field,data_field, query):
    """
    Line Chart
    Horizontal Bar Chart
    Basic Area Chart
    @author:Emtious
    :param category_field:
    :param data_field:
    :param query:
    :return:
    """
    dataset = utility_functions.__db_fetch_values_dict(query);
    category_list = getUniqueValues(dataset, category_field)
    seriesData = []
    dict = {}
    dict['data'] = [nameTodata[data_field] for nameTodata in dataset  ]
    seriesData.append(dict)
    jsonForChart = json.dumps({'categories': category_list, 'seriesdata': seriesData}, default=decimal_default)
    return jsonForChart



def generate_json_column_area_chart(name_field, category_field,data_field, query):
    """
    Percentage Area Chart
    Multiple Area chart
    :param name_field:
    :param category_field:
    :param data_field:
    :param query:
    :return:
    """
    dataset = utility_functions.__db_fetch_values_dict(query)  ## ******  ( Category for multiple value of each Legend) ******* (Start)    '''
    uniqueList = getUniqueValues(dataset, name_field)
    category_list = getUniqueValues(dataset, category_field)
    seriesData = []
    for ul in uniqueList:
        dict = {}
        dict['name'] = ul;
        dict['data'] = [nameTodata[data_field] for nameTodata in dataset if nameTodata[name_field] == ul]
        seriesData.append(dict)
    jsonForChart = json.dumps({'categories': category_list, 'seriesdata': seriesData}, default=decimal_default)
    return jsonForChart


def get_member_chart(request):
    query = "SELECT  (select name from geo_ward where id=geo_ward_id) as category, sum(hh_member_number) as value FROM public.household group by geo_ward_id";
    jsondata= generate_json_bar_line_area_Chart( 'category','value' , query)
    return HttpResponse(jsondata,content_type="application/json")



@csrf_exempt
def generate_graph(request, graph_id):
    """
    From Ajax Request
    Router of Chart Generation
    :param request:
    :param graph_id:
    :return:
    """
    dashboardGenerator = DashboardGenerator.objects.filter(id=graph_id).first()
    jsondata={}
    if dashboardGenerator.content_type==0: # GRAPH
        if dashboardGenerator.datasource_type=="1": # 1 = QUERY
            query=get_filtered_query(request.POST, dashboardGenerator.datasource)
            jsondata = execute_query(dashboardGenerator.chart_type.id,query)
        else: # 2 = URL
            #TODO: URL will Return a json
            jsondata = HttpResponseRedirect(dashboardGenerator.datasource)

    elif dashboardGenerator.content_type==1: # TAble
        if dashboardGenerator.datasource_type=="1":  # 1 = QUERY
            jsondata = getDashboardDatatable(dashboardGenerator.datasource)
        else: # 2 = URL
            #TODO: URL will Return a json
            jsondata = json.dumps(HttpResponseRedirect(dashboardGenerator.datasource))

    else: # MAP
        if dashboardGenerator.datasource_type == "1":  # 1 = QUERY
            jsondata = {}
        elif dashboardGenerator.datasource_type == "2":  # 2 = URL
            # TODO: URL will Return a json
            jsondata = HttpResponseRedirect(dashboardGenerator.datasource)
        else: #Static JSON
            jsondata = dashboardGenerator.datasource
        return HttpResponse(jsondata)

    return HttpResponse(jsondata, content_type = "application/json")



def execute_query(chart_type, query):
    #TODO Add more Chart type and check before excuting
    jsondata=''
    if chart_type==1:
        jsondata = generate_json_column_area_chart('name', 'category', 'value', query)
    else:
        jsondata = generate_json_bar_line_area_Chart('category', 'value', query)
    return jsondata;


def get_filtered_query(post_dict, query):
    keyward_param=""
    for key in post_dict:
        keyward_param="@"+key
        if keyward_param in query:
            query=query.replace(keyward_param, post_dict[key])

    return query;


def on_change_element(request ):
    """
    On change for Single Select Cascading
    :param request:
    :return:
    """
    control_id=request.POST.get("control_id")
    changed_val=request.POST.get("changed_val")
    controls_js=''
    cascaded_elements = DashboardControlsGenerator.objects.filter(cascaded_by_id=control_id).first()
    parent_div_id=cascaded_elements.allignment +'_'+ str(cascaded_elements.id)
    cursor = connection.cursor()
    onchange_function_js = ""
    cursor.execute(cascaded_elements.datasource.replace("@id", changed_val))
    cascaded_elements_next = DashboardControlsGenerator.objects.filter(cascaded_by_id=cascaded_elements.id).first()
    if cascaded_elements_next is not None:
        onchange_function_js = 'onChangeElement(' + str(control_id) + ');'
    row = cursor.fetchone()

    ds_data = utility_functions.unicodoToString(row[0])
    #controls_js += '\nvar jsondata_' + str(cascaded_elements.id) + '=JSON.parse(' + json.dumps(row[ 0]) + ');\n dropdownControlCreate("' + cascaded_elements.control_id + '","' + parent_div_id + '","' + cascaded_elements.control_name + '","' + cascaded_elements.control_label + '","' + onchange_function_js + '", jsondata_' + str(cascaded_elements.id) + ' );'
    #jsondata={"jsondata":row[0], "element": cascaded_elements.control_id ,"parent_div_id": parent_div_id , "control_name": cascaded_elements.control_label ,"control_label": cascaded_elements.control_name, "has_cascaded_element":onchange_function_js  }
    jsondata={"jsondata":ds_data, "element": cascaded_elements.control_id }

    return HttpResponse(json.dumps(jsondata),content_type="application/json")


def on_change_multiple_select(request):
    """
    On change for Multiple Select Cascading
    :param request:
    :return:
    """
    control_id=request.POST.get("control_id")
    changed_vals=request.POST.getlist("changed_val[]")
    changed_val=",".join([str(item) for item in changed_vals])
    controls_js=''
    cascaded_elements = DashboardControlsGenerator.objects.filter(cascaded_by_id=control_id).first()
    parent_div_id=cascaded_elements.allignment +'_'+ str(cascaded_elements.id)
    cursor = connection.cursor()
    onchange_function_js = ""
    updateted_datasource=cascaded_elements.datasource.replace("::text", " ")
    cursor.execute(updateted_datasource.replace("@id", " in("+changed_val +") "))
    cascaded_elements_next = DashboardControlsGenerator.objects.filter(cascaded_by_id=cascaded_elements.id).first()
    if cascaded_elements_next is not None:
        onchange_function_js = 'onChangeMultipleSelect(' + str(control_id) + ');'
    row = cursor.fetchone()
    ds_data = utility_functions.unicodoToString(row[0])
    #print json.dumps(cascaded_elements), '  JSON  '
    #controls_js += '\nvar jsondata_' + str(cascaded_elements.id) + '=JSON.parse(' + json.dumps(row[ 0]) + ');\n dropdownControlCreate("' + cascaded_elements.control_id + '","' + parent_div_id + '","' + cascaded_elements.control_name + '","' + cascaded_elements.control_label + '","' + onchange_function_js + '", jsondata_' + str(cascaded_elements.id) + ' );'
    #jsondata={"jsondata":row[0], "element": cascaded_elements.control_id ,"parent_div_id": parent_div_id , "control_name": cascaded_elements.control_label ,"control_label": cascaded_elements.control_name, "has_cascaded_element":onchange_function_js  }
    jsondata={"jsondata":ds_data, "element": cascaded_elements.control_id }
    return HttpResponse(json.dumps(jsondata),content_type="application/json")




"""
FILTERING CONTROL CREATE
"""

class FilteringControl():
    """
    Add Filtering Control
    """
    def __init__(self,nav_id):
        self.nav_id = nav_id
        self.parent_div_id = ''
        self.controls_js= ''
        self.controls_html =  '<div id="right_'+str(nav_id)+'" class="mpower-section right sidenav sidenav_right"><a  href="javascript:void(0)"  class="closebtn " onclick="closeNav(\'right_'+str(nav_id)+'\');">&times;</a>  </div> <a  href="#" id="right_link_'+str(nav_id)+'"  onclick="openNav(\'right_'+str(nav_id)+'\',\'container_'+str(nav_id)+'\');"  style="display:none;"  ><i class="fa fa-filter"></i></a> '

    def get_content(self):

        control_defs = DashboardControlsGenerator.objects.filter(navigation_bar_id=self.nav_id).order_by('element_order')

        def func_not_found():  # just in case we dont have the function
            print "No Function Found!"

        for control_def in control_defs:
            self.parent_div_id = control_def.allignment + '_' + str(self.nav_id)
            self.controls_js+='$("#'+control_def.allignment+'_link_'+str(self.nav_id)+'").show();\n'
            control_func_name = control_def.control_type
            control_function = getattr(self, control_func_name, func_not_found)
            control_function(control_def)


        result={'controls_html': self.controls_html,'controls_js': self.controls_js }
        return  result

    def single_select(self, control_def):
        """
        Single Select Create HTML AND JS
        :return: JSON including 2 attributes:  'controls_html', 'controls_js'
        """
        onchange_function_js=''
        cursor = connection.cursor()
        if control_def.cascaded_by is None:
            cursor.execute(control_def.datasource.replace("@id", "%"))
        else:
            cursor.execute(control_def.datasource.replace("@id", ""))
        cascaded_elements = DashboardControlsGenerator.objects.filter(cascaded_by_id=control_def.id).first()
        if cascaded_elements is not None:
            onchange_function_js = 'var changed_val= $(this).val();onChangeElement(' + str(
                control_def.id) + ',changed_val);'
        row = cursor.fetchone()
        ds_data = utility_functions.unicodoToString(row[0])
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(ds_data) + ');\n dropdownControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '","' + onchange_function_js + '", jsondata_' + str(control_def.id) + ' );'



    def multiple_select(self, control_def):
        """
        Multiole Select Create HTML AND JS
        :return: JSON including 2 attributes:  'controls_html', 'controls_js'
        """
        cursor = connection.cursor()
        onchange_function_js=''
        ds_data = '[]'
        if control_def.datasource_type == '1':
            cursor.execute(control_def.datasource.replace("@id", "like '%'"))
            cascaded_elements = DashboardControlsGenerator.objects.filter(cascaded_by_id=control_def.id).first()
            if cascaded_elements is not None:
                onchange_function_js = ' var changed_val= $(this).val(); onChangeMultipleSelect(' + str(
                    control_def.id) + ',changed_val);'
            row = cursor.fetchone()
            ds_data = utility_functions.unicodoToString(row[0])
        if control_def.datasource_type == '3':
            ds_data = control_def.datasource
 
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(
            ds_data) + ');\n multipleSelectControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '",  "' + control_def.control_label + '"  ,"' + onchange_function_js + '", jsondata_' + str(
            control_def.id) + ' );'


    def checkbox(self, control_def):
        """
        Checkbox Create HTML AND JS
        :return: None
        """
        cursor = connection.cursor()
        cursor.execute(eachrow.datasource)
        row = cursor.fetchone()
        ds_data = utility_functions.unicodoToString(row[0])
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(ds_data) + ');\n checkboxControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '", jsondata_' + str(
            control_def.id) + ' );'


    def radio(self, control_def):
        """
        Radio Create HTML AND JS
        :return: None
        """
        # controls_html += '<div id="' + parent_div_id + '"></div>'
        cursor = connection.cursor()
        cursor.execute(control_def.datasource)
        row = cursor.fetchone()
        ds_data = utility_functions.unicodoToString(row[0])
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(ds_data) + ');\n radioControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '", jsondata_' + str(
            control_def.id) + ' );'


    def date(self, control_def):
        """
        Date Create HTML AND JS
        :return: None
        """
        if control_def.appearance =="":
            control_def.appearance = '{"format":"dd-mm-yyyy","viewmode":"days","minviewmode":"days", "minviewmode":"years"}'
        self.controls_js += '\n dateControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '",' + control_def.appearance + ', ""  );'


    def button(self, control_def):
        """
        Button Create HTML AND JS
        :return: None
        """
        self.controls_js += '\n buttonControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '", "' + control_def.control_label + '" );'

    def text(self, control_def):
        """
        Text Box Create HTML AND JS
        :return: None
        """
        self.controls_js += '\n textinputControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '", ""  );'






"""
********COMPONENT(Chart) CREATION********
"""
class Component:
    """
    Interface For Any Component, Ex- Graph, Table, Map ect
    """
    def execute(self):
        """
        :return: JSON having these attribute 'chart_html', 'js_chart_calling_function' ,'js_chart_calling_function_with_param'
        """
        pass



class Graph(Component):
    """
    Graph is a Component
    Its Taking Data from Chart Definition and making Required HTML and JS Functions
    """
    def __init__(self,chart_def):
        self.chart_html = ''
        self.js_chart_calling_function = ''
        self.js_chart_calling_function_with_param = ''
        self.chart_def=chart_def


    def execute(self):
        """
        Get HTML and JS for GRAPH
        :return: JSON
        """
        appearance = json.loads(self.chart_def.chart_object)
        width="100%"
        if "width" in appearance:
            width = appearance["width"]

        self.chart_html += '<div  style="width:' + str(
            width) + '%"  class="middle-item "><div  id="' + self.chart_def.element_id + '"></div></div>'
        self.js_chart_calling_function += '\nmpowerRequestForChart("' + self.chart_def.post_url + '", "' + self.chart_def.element_id + '", ' + self.chart_def.chart_object + ', {});'
        self.js_chart_calling_function_with_param += 'mpowerRequestForChart("' +self.chart_def.post_url + '", "' + self.chart_def.element_id + '", ' +self.chart_def.chart_object + ', parameters );'
        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}




class SimpleTable(Component):
    """
    SimpleTable is a Component
    Its Taking Data from Chart Definition and making Required HTML and JS Functions For SimpleTable Generation
    """
    def __init__(self,chart_def):
        self.chart_html = ''
        self.js_chart_calling_function = ''
        self.js_chart_calling_function_with_param = ''
        self.chart_def=chart_def


    def execute(self):
        """
        Get HTML and JS for table
        :return: JSON
        """

        appearance = json.loads(self.chart_def.chart_object)
        width="100%"
        if "width" in appearance:
            width = appearance["width"];

        self.chart_html += '  <div style="width:' + str(
            width) + '%"  class="middle-item "><table id="' + self.chart_def.element_id + '"class="display table table-bordered table-striped table-condensed nowrap"></table></div>'
        self.js_chart_calling_function += '\nmpowerRequestForTable("' + self.chart_def.post_url + '", "' + self.chart_def.element_id + '", {});'
        self.js_chart_calling_function_with_param += 'mpowerRequestForTable("' + self.chart_def.post_url + '", "' + self.chart_def.element_id + '", parameters );'

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}






class SimpleMap(Component):
    """
    SimpleMap is a Component
    Its Taking Data from Chart Definition and making Required HTML and JS Functions For SimpleMap Generation
    """

    def __init__(self, chart_def):
        self.chart_html = ''
        self.js_chart_calling_function = ''
        self.js_chart_calling_function_with_param = ''
        self.chart_def = chart_def

    def execute(self):
        appearance = json.loads(self.chart_def.chart_object)
        width = "100%"
        if "width" in appearance:
            width = appearance["width"];

        self.chart_html += '<div style="width:' + str(width) + '%" class="map" id="' + self.chart_def.element_id + '"></div>'
        self.js_chart_calling_function += '\nmpowerRequestForMap("' + self.chart_def.post_url + '", "' + self.chart_def.element_id + '",  ' + self.chart_def.chart_object + ', {});'
        self.js_chart_calling_function_with_param += 'mpowerRequestForMap("' + self.chart_def.post_url + '", "' + self.chart_def.element_id + '", parameters );'

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}






class ComponentManager:
    """
    Create COMPONENT/ CHART For each navigation Tab
    """
    def __init__(self,nav_id):
        self.nav_id=nav_id
        self.components = []
        self.chart_html = ''
        self.js_chart_calling_function = ''
        self.js_chart_calling_function_with_param = ''

    def get_chart_content(self):
        """
        GET ALL HTML and JS Content
        :return: JSON having these attribute 'chart_html', 'js_chart_calling_function' ,'js_chart_calling_function_with_param'
        """

        chart_defs = DashboardGenerator.objects.filter(navigation_bar_id=self.nav_id).order_by('content_order')
        #chart_defs = DashboardGenerator.objects.filter(id=32).order_by('content_order')

        for chart_def in chart_defs:
            if chart_def.content_type == 0:  # GRAPH
                self.components.append(Graph(chart_def))
            elif chart_def.content_type == 1:  # Table
                self.components.append(SimpleTable(chart_def))
            elif chart_def.content_type == 2:  # MAP
                self.components.append(SimpleMap(chart_def))

        for c in self.components:
            jsondata=c.execute()
            self.chart_html+= jsondata['chart_html']
            self.js_chart_calling_function+= jsondata['js_chart_calling_function']
            self.js_chart_calling_function_with_param+= jsondata['js_chart_calling_function_with_param']

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}





def generate_dynamic_report(request):
    """
    Generate Dynamic Report From saved Data
    :param request:
    :return:
    """

    #Get parent navigation titles
    MODULE_NAME='dashboard'
    navigationBarParent=DashboardNavigationBar.objects.filter(parent_link_id__isnull=True)
    sub_navigation=''
    # get parent;s child
    navigation_bars = '<div class="portlet-body" ><ul class="nav nav-pills">'
    content_tabs = '<div class="tab-content ">'
    html_code = ''
    js_code = ''
    css_active='active'

    for eachrow in navigationBarParent:
        sub_navigation=''
        navigationBarChild = DashboardNavigationBar.objects.filter(parent_link_id=eachrow.id)
        init_tab_caller=''

        if not navigationBarChild:
            navigation_bars += '<li class="'+css_active+'"><a data-toggle="tab" onclick="init_tab_' + str(eachrow.id) + '();" href="#tab_'+str(eachrow.id)+'">' + eachrow.link_name + '</a></li>'
            content_tabs += '<div class="tab-pane ' + css_active + '" id="tab_'+str(eachrow.id)+'"  ><form id="form_' + str(eachrow.id) + '" > <div  class="flex "> <div  id="left_' + str(eachrow.id) + '" class="mpower-section left sidenav sidenav_left" ><a href="javascript:void(0)" class="closebtn" onclick="closeNav(\'left_'+str(eachrow.id)+'\');">&times;</a>   </div>  <a  href="#"   style="display:none;" id="left_link_'+str(eachrow.id)+'"    onclick="openNav(\'left_'+str(eachrow.id)+'\');"    ><i class="fa fa-filter"></i></a><div  id="middle_' + str(eachrow.id) + '" class="mpower-section middle " >'

            # Creating Filtering Control for each tab
            filteringControl=FilteringControl(eachrow.id)
            controls_info=filteringControl.get_content()

            #Creating CHART/Component for each tab
            componentManager = ComponentManager(eachrow.id)
            chart_content = componentManager.get_chart_content()

            js_code += 'function init_tab_' + str(eachrow.id) + '() { if ($("#container_' + str(eachrow.id) + '").data("load")=="unloaded") {  ' + controls_info['controls_js'] + '  ' + chart_content['js_chart_calling_function'] + ' \n $("#container_' + str(eachrow.id) + '").data("load","loaded"); }   }\n\n'
            content_tabs += ' <div class="mpower-section middle-top" id="top_' + str(eachrow.id) + '"> </div><div data-load="unloaded" class="middle-container" id="container_'+ str(eachrow.id) + '">'+chart_content['chart_html']+' </div></div>'+controls_info['controls_html']
            content_tabs += '</div></form></div>'
            js_code+='$("#form_'+str(eachrow.id)+'").submit(function(event) { event.preventDefault(); var parameters = $(this).serializeArray(); console.log("Data "+parameters); \n '+chart_content['js_chart_calling_function_with_param']+' });'

            if css_active == 'active':
                init_tab_caller = 'init_tab_' + str(eachrow.id) + '(); \n'
                css_active = ''
        else:
            sub_navigation='<li class="dropdown '+css_active+'"><a   href="#" class="dropdown-toggle" data-toggle="dropdown" id="tabDrop_'+str(eachrow.id)+'">'+eachrow.link_name+' <i class="fa fa-angle-down"></i></a> <ul  class="dropdown-menu" role="menu" aria-labelledby="tabDrop_'+str(eachrow.id)+'" >'
            for eachchildrow in navigationBarChild:
                #dashboardGenerator = DashboardGenerator.objects.filter(navigation_bar_id=eachchildrow.id).first()
                sub_navigation+='<li class="'+css_active+'"><a onclick="init_tab_' + str(eachchildrow.id) + '();" href="#tab_'+str(eachchildrow.id)+'"  tabindex="-1" data-toggle="tab" >' + eachchildrow.link_name + '</a></li>'
                content_tabs += ' <div class="tab-pane ' + css_active + '" id="tab_'+str(eachchildrow.id)+'"> <form id="form_' + str(eachchildrow.id) + '" > <div  class="flex"> <div class="mpower-section left  sidenav sidenav_left "  id="left_' + str(eachchildrow.id) + '" ><a href="javascript:void(0)" class="closebtn" onclick="closeNav(\'left_'+str(eachchildrow.id)+'\');">&times;</a> </div><a  href="#" style="display:none;" id="left_link_'+str(eachchildrow.id)+'"   onclick="openNav(\'left_'+str(eachchildrow.id)+'\');"    ><i class="fa fa-filter"></i></a>  <div class="mpower-section middle"  id="middle_' + str(eachchildrow.id) + '" > '

                # Creating Filtering Control for each tab
                filteringControl = FilteringControl(eachchildrow.id)
                controls_info = filteringControl.get_content()

                # Creating CHART/Component for each tab
                componentManager = ComponentManager(eachchildrow.id)
                chart_content= componentManager.get_chart_content()

                js_code += 'function init_tab_' + str(eachchildrow.id) + '() {  if($("#container_' + str(eachchildrow.id) + '").data("load")=="unloaded") {  '+ controls_info['controls_js'] +'  ' + chart_content['js_chart_calling_function'] + '\n $("#container_' + str(eachchildrow.id) + '").data("load","loaded");   } }\n\n'
                content_tabs +=  '<div class="mpower-section middle-top"  id="top_' + str(eachchildrow.id) + '" >  </div><div data-load="unloaded" class="middle-container" id="container_'+ str(eachchildrow.id) + '">'+chart_content['chart_html']+'</div></div>' + controls_info['controls_html']
                content_tabs += ' </div></form></div>'
                js_code += '$("#form_' + str(eachchildrow.id) + '").submit(function(event) { event.preventDefault(); var parameters = $(this).serializeArray(); console.log("Data "+parameters); \n ' +chart_content['js_chart_calling_function_with_param'] + ' });'

                if css_active == 'active':
                    init_tab_caller = 'init_tab_' + str(eachchildrow.id) + '(); \n'
                    css_active=''
            sub_navigation+='</ul>  </li>'

        css_active=''
        js_code +=init_tab_caller
        navigation_bars+=sub_navigation
    content_tabs += '</div>'
    navigation_bars+='</ul>' + content_tabs +'</div>'

    return {'html_code':navigation_bars, 'js_code':js_code}


def generate_saved_report(request,id):
    """
    Generate Report From saved Data
    :param request:
    :param id:
    :return:
    """
    json_output={}
    if id=="0":
        json_output=generate_dynamic_report(request)
    else:
        loaded_dashboard_instance = DashboardLoader.objects.get(pk=id)
        json_output={'html_code':loaded_dashboard_instance.html_code, 'js_code':loaded_dashboard_instance.js_code }

    return render(request, "dashboard/generate_saved_report.html",json_output)



'''
******************  Save Current Template ***********************
'''





def save_loaded_dashboard(request):
    """
    Save Current Dynamic Dashboard
    :param request:
    :return:
    """

    generated_saved_report=generate_dynamic_report(request)
    if request.method=="POST":

        try:
            dashboardLoader=DashboardLoader()
            dashboardLoader.html_code=generated_saved_report['html_code']
            dashboardLoader.js_code = generated_saved_report['js_code']
            dashboardLoader.name=request.POST.get("dashboard_name")
            dashboardLoader.save()
            messages.success(request, '<i class="fa fa-check-circle"></i> Dashboard Saved Successfully',
                             extra_tags='alert-success crop-both-side')
        except:
            messages.success(request, '<i class="fa fa-cross-circle"></i> Dashboard saving failed.',
                             extra_tags='alert-danger crop-both-side')
        return index(request)


def show_template_get_json(request):
    """
    Show List of Saved Template
    :param request:
    :return:
    """
    datajson = getDatatable('select id ,\'<a href="/dashboard/generate_saved_report/\' || id::text || \'/">\' || name ::text || \'</a> \' as name , created_at::text as Date from dashboard_loader order by created_at desc')
    return HttpResponse(datajson, content_type='application/json')




def update_loaded_dashboard(request, loaded_db_id):
    """
    Update loaded_dashboard
    :param request:
    :param loaded_db_id:
    :return:
    """
    LOADED_DASHBOARD_ID = loaded_db_id
    if request.method == "GET":
        loaded_dashboard_form_instance = DashboardLoader.objects.filter(id=LOADED_DASHBOARD_ID).first()
        loaded_dashboard_form = DashboardLoaderUpdateForm(instance=loaded_dashboard_form_instance)
        context = {
            "loaded_dashboard_form": loaded_dashboard_form,
            "LOADED_DASHBOARD_ID": LOADED_DASHBOARD_ID
        }
    if request.method == "POST":
        loaded_dashboard_form_instance = DashboardLoader.objects.filter(id=loaded_db_id).first()
        loaded_dashboard_form = DashboardLoaderUpdateForm(data=request.POST, instance=loaded_dashboard_form_instance)
        if loaded_dashboard_form.is_valid():
            loaded_dashboard_form_instance = loaded_dashboard_form.save()
            messages.success(request, '<i class="fa fa-check-circle"></i> Dashboard Saved Successfully',
                             extra_tags='alert-success crop-both-side')
            return index(request)
        else:
            messages.success(request, '<i class="fa fa-cross-circle"></i> Dashboard saving failed. Please Try again.',
                             extra_tags='alert-danger crop-both-side')
            context = {
                "loaded_dashboard_form": loaded_dashboard_form,
                "LOADED_DASHBOARD_ID": LOADED_DASHBOARD_ID
            }
            return render(request, "dashboard/update_loaded_dashboard.html", context, status=500);
    return render(request, "dashboard/update_loaded_dashboard.html", context);



def delete_loaded_dashboard(request, loaded_db_id):
    """
    Delete Loaded Dashboard
    :param request:
    :param loaded_db_id:
    :return:
    """
    loaded_dashboard_instance = DashboardLoader.objects.get(pk=loaded_db_id)
    try:
        loaded_dashboard_name=loaded_dashboard_instance.name;
        loaded_dashboard_instance.delete()
        data=getAjaxMessage("success",'<i class="fa fa-check-circle"></i> Dashboard -'+loaded_dashboard_name+' has been deleted successfully!')
    except ProtectedError:
        loaded_dashboard_del_message = "Dashboard could not be deleted."
        data=getAjaxMessage("danger", loaded_dashboard_del_message)
    return HttpResponse(simplejson.dumps(data), content_type="application/json")
