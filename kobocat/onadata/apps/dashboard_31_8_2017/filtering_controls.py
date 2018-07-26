
from onadata.apps.dashboard.forms import *
from django.db import connection
from onadata.apps.dashboard.models import *
import json
from onadata.apps.dashboard import utility_functions


"""
*****************FILTERING CONTROLS/ Fields CREATION *******************


**To Introduce New Filtering Options:
1. JS: Add creating control function in mpower.dashbaord.js
2. SERVER SIDE: Add a function in FilteringControls Class that will return a caller function(JS as string) which is written in 1
3. Function Name at point 2 will be referenced in DashboardControlsGenerator Table(field 'control_type')

"""


class FilteringControls():
    """
    Add Filtering Control
    """

    def __init__(self, nav_id):
        self.nav_id = nav_id
        self.parent_div_id = ''
        self.controls_js = ''
        self.control_js_after_form_submit = ''

    def get_content(self):

        control_defs = DashboardControlsGenerator.objects.filter(navigation_bar_id=self.nav_id).order_by(
            'element_order')

        def func_not_found():  # just in case we dont have the function
            print "No Function Found!"


        #****Important::::::Here (Below one if condition) I am guessing that, All controls in a page will be on same side (Left/Right)
        #if there is filtering field then show Filtering icon.
        if len(control_defs)>0:
             self.controls_js += """
                $("#toggle_{allignment}_{nav_id}").show();
             """.format(allignment=control_defs[0].allignment,nav_id=str(self.nav_id))

             self.control_js_after_form_submit += """
               closeNav("{allignment}_{nav_id}", "#toggle_{allignment}_{nav_id}");
             """.format(allignment=control_defs[0].allignment, nav_id=str(self.nav_id))



        for control_def in control_defs:
            #Parent Div Id where current field will hook
            self.parent_div_id = control_def.allignment + '_' + str(self.nav_id)

            control_func_name = control_def.control_type
            control_function = getattr(self, control_func_name, func_not_found)
            control_function(control_def)

        result = {'controls_js': self.controls_js, 'control_js_after_form_submit':self.control_js_after_form_submit}
        return result

    def single_select(self, control_def):
        """
        Single Select Create HTML AND JS
        :return: JSON including 2 attributes:  'controls_html', 'controls_js'
        """
        onchange_function_js = ''
        cursor = connection.cursor()
        #if control_def.cascaded_by is None:
        #    cursor.execute(control_def.datasource.replace("@id", "%"))
        #else:
        #    cursor.execute(control_def.datasource.replace("@id", ""))
        cursor.execute(control_def.datasource.replace("@id", "%"))
        cascaded_elements = DashboardControlsGenerator.objects.filter(cascaded_by_id=control_def.id).first()
        if cascaded_elements is not None:
            onchange_function_js = 'var changed_val= $(this).val();onChangeElement(' + str(
                control_def.id) + ',changed_val);'
        row = cursor.fetchone()
        ds_data = utility_functions.unicodoToString(row[0])

        if control_def.appearance=="":
            appearance = "{}"
        else:
            appearance = control_def.appearance
        #print appearance
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(
            ds_data) + ');\n dropdownControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '","' + onchange_function_js + '", jsondata_' + str(
            control_def.id) + ', '+ appearance+' );'

    def multiple_select(self, control_def):
        """
        Multiole Select Create HTML AND JS
        :return: JSON including 2 attributes:  'controls_html', 'controls_js'
        """
        cursor = connection.cursor()
        onchange_function_js = ''
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
        if control_def.appearance=="":
            appearance = "{}"
        else:
            appearance = control_def.appearance
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(
            ds_data) + ');\n multipleSelectControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '",  "' + control_def.control_label + '"  ,"' + onchange_function_js + '", jsondata_' + str(
            control_def.id) + ', '+appearance+');'

    def checkbox(self, control_def):
        """
        Checkbox Create HTML AND JS
        :return: None
        """
        cursor = connection.cursor()
        cursor.execute(eachrow.datasource)
        row = cursor.fetchone()
        ds_data = utility_functions.unicodoToString(row[0])
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(
            ds_data) + ');\n checkboxControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '", jsondata_' + str(
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
        self.controls_js += '\nvar jsondata_' + str(control_def.id) + '=JSON.parse(' + json.dumps(
            ds_data) + ');\n radioControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '", jsondata_' + str(
            control_def.id) + ' );'

    def date(self, control_def):
        """
        Date Create HTML AND JS
        :return: None
        """
        if control_def.appearance == "":
            control_def.appearance = '{"format":"dd-mm-yyyy","viewmode":"days","minviewmode":"days", "minviewmode":"years"}'
        self.controls_js += '\n dateControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '",' + control_def.appearance + ', ""  );'

    def button(self, control_def):
        """
        Button Create HTML AND JS
        :return: None
        """
        self.controls_js += '\n buttonControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '", "' + control_def.control_label + '" );  '

    def text(self, control_def):
        """
        Text Box Create HTML AND JS
        :return: None
        """
        self.controls_js += '\n textinputControlCreate("' + control_def.control_id + '","' + self.parent_div_id + '","' + control_def.control_name + '","' + control_def.control_label + '", ""  );'

