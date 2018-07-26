from onadata.apps.dashboard.forms import *
from onadata.apps.dashboard.models import *
import json


"""
*****************COMPONENT(Graph/Table/Map/Customized Something) CREATION  *******************


**To Introduce TYPE of Component:
1. Create a class that implements Component Interface
2. execute function returns a Dictionary having these attribute:
    'chart_html'
    'js_chart_calling_function'
    'js_chart_calling_function_with_param'
3. Add Newly Created Class inside ComponentManager Class (get_chart_content function)
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


class ComponentManager:
    """
    ENTRY POINT
    Create COMPONENT/ CHART For each navigation Tab
    """

    def __init__(self, nav_id):
        self.nav_id = nav_id
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

        for chart_def in chart_defs:
            if chart_def.content_type == 0:  # GRAPH
                self.components.append(Graph(chart_def))
            elif chart_def.content_type == 1:  # Table
                self.components.append(SimpleTable(chart_def))
            elif chart_def.content_type == 2:  # MAP
                self.components.append(SimpleMap(chart_def))
            elif chart_def.content_type == 3:  # Customized Component
                self.components.append(CustomizedComponent(chart_def))
            #Add New Component here................


        for c in self.components:
            jsondata = c.execute()
            self.chart_html += jsondata['chart_html']
            self.js_chart_calling_function += jsondata['js_chart_calling_function']
            self.js_chart_calling_function_with_param += jsondata['js_chart_calling_function_with_param']

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}




class Graph(Component):
    """
    Graph is a Component
    Its Taking Data from Chart Definition and making Required HTML and JS Functions
    """

    def __init__(self, chart_def):
        self.chart_html = ''
        self.js_chart_calling_function = ''
        self.js_chart_calling_function_with_param = ''
        self.chart_def = chart_def

    def execute(self):
        """
        Get HTML and JS for GRAPH
        :return: JSON
        """
        appearance = json.loads(self.chart_def.chart_object)
        width = "100%"
        customized = False
        if "width" in appearance:
            width = appearance["width"]

        if "customized" in appearance:
            customized = appearance["customized"]

        if customized == False:
            self.chart_html +="""
            <div  style="width:{width}%"  class="middle-item ">
                <div  id="{element_id}">
                </div>
            </div>
            """.format(width=width, element_id=self.chart_def.element_id);

        self.js_chart_calling_function += """
                mpowerRequestForChart("{post_url}", "{element_id}", {chart_object}, {{}});
            """.format(post_url=self.chart_def.post_url, element_id=self.chart_def.element_id, chart_object=self.chart_def.chart_object)


        self.js_chart_calling_function_with_param += """
                        mpowerRequestForChart("{post_url}", "{element_id}", {chart_object}, parameters);
            """.format(post_url=self.chart_def.post_url, element_id=self.chart_def.element_id, chart_object=self.chart_def.chart_object)

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function, 'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}


class SimpleTable(Component):
    """
    SimpleTable is a Component
    Its Taking Data from Chart Definition and making Required HTML and JS Functions For SimpleTable Generation
    """

    def __init__(self, chart_def):
        self.chart_html = ''
        self.js_chart_calling_function = ''
        self.js_chart_calling_function_with_param = ''
        self.chart_def = chart_def

    def execute(self):
        """
        Get HTML and JS for table
        :return: JSON
        """
        appearance = json.loads(self.chart_def.chart_object)
        width = "100%"
        if "width" in appearance:
            width = appearance["width"];

        self.chart_html += """
                    <div  style="width:{width}%"  class="middle-item ">
                        <table id="{element_id}" class="display table table-bordered table-striped table-condensed table-responsive nowrap">
                        </table>
                    </div>
                    """.format(width=width, element_id=self.chart_def.element_id)


        self.js_chart_calling_function += """
                        mpowerRequestForTable("{post_url}", "{element_id}", {chart_object}, {{}});
                    """.format(post_url=self.chart_def.post_url, element_id=self.chart_def.element_id,
                               chart_object=self.chart_def.chart_object)

        self.js_chart_calling_function_with_param += """
                                mpowerRequestForTable("{post_url}", "{element_id}", {chart_object}, parameters);
                    """.format(post_url=self.chart_def.post_url, element_id=self.chart_def.element_id,
                               chart_object=self.chart_def.chart_object)


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

        self.chart_html += """
            <div style="width:{width}%" class="map" id="{element_id}"></div>
            <div id="legend" class="legend"></div>
        """.format(width=width, element_id=self.chart_def.element_id)


        self.js_chart_calling_function += """
                                mpowerRequestForMap("{post_url}", "{element_id}", {chart_object}, {{}});
                            """.format(post_url=self.chart_def.post_url, element_id=self.chart_def.element_id,
                                       chart_object=self.chart_def.chart_object)

        self.js_chart_calling_function_with_param += """
                                        mpowerRequestForMap("{post_url}", "{element_id}", {chart_object}, parameters);
                            """.format(post_url=self.chart_def.post_url, element_id=self.chart_def.element_id,
                                       chart_object=self.chart_def.chart_object)

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}


class CustomizedComponent(Component):
    """
    CustomizedComponent is a Component
    Its Reading HTML AND JS Directly from DB
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
            width = appearance["width"]

        self.chart_html += '<div id="' + self.chart_def.element_id + '" style="width:' + str(
            width) + '%" class="middle-item ">' + self.chart_def.html_code + '</div>'

        self.chart_html += """
                    <div id="{element_id}" style="width:{width}%" class="middle-item ">
                        {html_code}
                    </div>
                """.format(width=width, element_id=self.chart_def.element_id, html_code=self.chart_def.html_code)

        if self.chart_def.js_code is not None:
            if "@parameter" in self.chart_def.js_code:
                global_caller = self.chart_def.js_code
                filter_caller = self.chart_def.js_code
                global_caller = global_caller.replace("@parameter", "{}")
                filter_caller = filter_caller.replace("@parameter", "parameters")
                self.js_chart_calling_function += global_caller
                self.js_chart_calling_function_with_param += filter_caller
            else:
                self.js_chart_calling_function += self.chart_def.js_code
                self.js_chart_calling_function_with_param += self.chart_def.js_code

        return {'chart_html': self.chart_html, 'js_chart_calling_function': self.js_chart_calling_function,
                'js_chart_calling_function_with_param': self.js_chart_calling_function_with_param}


