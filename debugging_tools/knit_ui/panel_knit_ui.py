from bokeh.models import CustomJS

from tests.test_knitspeak_compiler import generate_initial_graph
from tests.test_knitspeak_compiler import generate_final_graph_hole
from tests.test_knitspeak_compiler import generate_final_graph_pocket
from tests.test_knitspeak_compiler import generate_file
from tests.test_knitspeak_compiler import generate_final_graph_handle
from tests.test_knitspeak_compiler import generate_final_graph_strap
from debugging_tools.exceptions import ErrorException

import pandas as pd
import numpy as np
import holoviews as hv
import re
from holoviews import opts
import panel as pn
from bokeh.models.widgets import Button, TextInput, Select, NumericInput, CheckboxGroup, RadioButtonGroup, Toggle
hv.extension('bokeh')
pn.extension('altair', 'tabulator')


# run the following command to launch notebook
# panel serve knit_ui.py --autoreload --show
# bokeh serve --show knit_ui.py

# if(type == "Sheet"):
#     all rs rows k. all ws rows p.
# else:
#     all rs rounds k. all ws rounds p.

ui = pn.Column()

knit_graph = None
html_graph = None

hole = []
hole_carrier = []
strap = []

# pattern type - button
pattern_type_options = ["Tube", "Sheet"]
pattern_type = RadioButtonGroup(name='Pattern Type', labels=pattern_type_options, active=0)

knit_speak = TextInput(title='Knit Speak', placeholder='Enter knit speak')

# knitting procedure - radio button
tube_knitting_procedure_options = ["Handle", "Pocket", "Hole", "Strap"]
sheet_knitting_procedure_options = ["Handle", "Pocket", "Hole"]

knitting_procedure = RadioButtonGroup(name='Knitting Procedure', labels=["Handle", "Pocket", "Hole", "Strap"], active=0)

# gauge - drop down
gauge_options = ["1/4", "1/3"]

gauge = Select(title='Gauge',
               options=gauge_options,
               value=gauge_options[0])

# yarn carrier - drop down
yarn_carrier_options = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
yarn_carrier = Select(title='Yarn ID', options=yarn_carrier_options, value=yarn_carrier_options[0])


# graph height and width - int sliders
height = NumericInput(title='Height', low=1, value=1)
width = NumericInput(title='Width', low=1, value=1)

# create knit graph - button
create_knit_graph_button = Button(label='Create Knit Graph', button_type='primary')

# knit graph generation section
update_map_button = Button(label='Update Knit Graph', button_type='primary')
confirm_graph = Button(label='Confirm Graph', button_type='primary')
back1 = Button(label='Back', button_type='danger')

# hole modification (SHEET)
hole_nodes = TextInput(title='Hole Nodes', placeholder='Node IDs to delete', width=160)
hole_carrier_sheet = Select(title='Yarn ID', options=yarn_carrier_options, value=yarn_carrier_options[0], width=160)
more_hole_sheet = Button(label='Add More Holes')

# hole modification (TUBE)
hole_nodes_tube = TextInput(title='Hole Nodes', placeholder='Node IDs to delete', width=320)
more_hole_tube = Button(label='Add More Holes', width=320)

# pocket modification (SHEET and TUBE)
left_keynodes_pocket = TextInput(title='Vertex Coordinates on Small Wale Side', placeholder='ex. (1,1), (2,2)')
right_keynodes_pocket = TextInput(title='Vertex Coordinates on the Big Wale Side', placeholder='ex. (1,1), (2,2)')
pocket_yarn_carrier_id = Select(title='Yarn ID for Pocket', options=yarn_carrier_options)
is_front_patch_pocket = Toggle(label='Make Front Patch', active=False)
close_top_pocket = Toggle(label='Close the Top', active=False)
confirm_tuples_pocket = Button(label='Confirm Vertices')
right_checkbox = CheckboxGroup(name='Big Wale Side Connections', inline=False)
left_checkbox = CheckboxGroup(name='Small Wale Side Connections', inline=False)

# handle modification (SHEET and TUBE)
handle_yarn_carrier_id = Select(title='Yarn ID for Handle', options=yarn_carrier_options)
is_front_patch_handle = Toggle(label='Make Front Patch', active=False)
left_keynodes_handle = TextInput(title='Vertex Coordinates on Small Wale Side', placeholder='ex. (1,1), (2,2)')
right_keynodes_handle = TextInput(title='Vertex Coordinates on the Big Wale Side', placeholder='ex. (1,1), (2,2)')

# strap modification (TUBE)
strap_height = NumericInput(title='Strap Height', low=1, value=1)
strap_front = TextInput(title='Strap 1 Front', placeholder='ex. (1, 1)', width=160)
strap_back = TextInput(title='Strap 1 Back', placeholder='(1, 1)', width=160)
strap_front_color = Select(title='Yarn ID for Strap 1 Front', options=yarn_carrier_options, width=160)
strap_back_color = Select(title='Yarn ID for Strap 1 Back', options=yarn_carrier_options, width=160)
more_strap = Button(label='Add More Straps', width=320)

# confirmation and download section
filename_input = TextInput(title='Knit-Out File Name', placeholder='Enter file name for knit out (no extension)')
confirm_filename = Button(label='Confirm Knit Out File Name')
back2 = Button(label='Back', button_type='danger')

# widget sections
widget1 = pn.WidgetBox('## Starting Selections', pattern_type, knit_speak, knitting_procedure, gauge,
                       yarn_carrier, height, width, create_knit_graph_button)

widget2 = pn.WidgetBox('## Modification Selections', back1, update_map_button, confirm_graph)
widget3 = pn.WidgetBox('## Export Knit-Out File', filename_input, confirm_filename, back2)


def _update_knit_procedures(attr, old, new):
    if new == 0:
        knitting_procedure.labels = tube_knitting_procedure_options
    elif new == 1:
        knitting_procedure.labels = sheet_knitting_procedure_options

    knitting_procedure.active = 0


pattern_type.on_change("active", _update_knit_procedures)

def _update_color_strap(attr, old, new):
    yarn_carrier.options = yarn_carrier_options
    if new == 3:
        yarn_carrier.options = ["9"]

knitting_procedure.on_change("active", _update_color_strap)


def _update_gauge(attr, old, new):
    gauge.options = ["1/4", "1/3", "1/2"]
    gauge.value = gauge_options[0]
    if (new == 0 or new == 1) and pattern_type.active == 0: # if (new == "Handle" or new == "Pocket") and pattern_type.active == "Tube":
        gauge.options = ["1/4", "1/3"]
    elif new == 2 and pattern_type.active == 1: # elif new == "Hole" and new == "Sheet":
        gauge.options = ["1/4", "1/3", "1/2", "1"]


knitting_procedure.on_change("active", _update_gauge)

def _create_knit_graph(event):
    check_pattern_type = knit_speak.value.lower().split(" ")
    if ("rounds" in check_pattern_type and pattern_type.active == 0) or ("rows" in check_pattern_type and pattern_type.active == 1): # 0 is Tube, 1 is Sheet
        ui.clear()
        final_type = knit_speak.value
        hole.clear()
        strap.clear()
        try:
            gauge_map = {"1/4": 0.25, "1/3": 1/3, "1/2": 0.5}
            global html_graph
            global knit_graph
            html_graph, knit_graph = generate_initial_graph(final_type, gauge_map[gauge.value], int(yarn_carrier.value), width.value, height.value, "Tube" if pattern_type.active == 0 else "Sheet")
            html_pane = pn.pane.HTML(html_graph)
            row = pn.Row(widget2)
            ui.append(row)

            if knitting_procedure.active == 2 and pattern_type.active == 1: # 0 is Handle, 1 is Pocket, 2 is Hole, 3 is Strap
                ui.append(more_hole_sheet)
                ui.append(pn.Row(hole_carrier_sheet, hole_nodes))
                hole_carrier.append(hole_carrier_sheet)
                hole.append(hole_nodes)
            elif knitting_procedure.active == 2 and pattern_type.active == 0:
                ui.append(more_hole_tube)
                ui.append(hole_nodes_tube)
                hole.append(hole_nodes_tube)
            elif knitting_procedure.active == 1:
                pocket_widget_box = pn.WidgetBox("## Pocket Modification", left_keynodes_pocket, right_keynodes_pocket,
                                                confirm_tuples_pocket, pocket_yarn_carrier_id,
                                                 is_front_patch_pocket, close_top_pocket)
                ui.append(pocket_widget_box)
            elif knitting_procedure.active == 0:
                handle_widget_box = pn.WidgetBox("## Handle Modification", left_keynodes_handle, right_keynodes_handle,
                                                 handle_yarn_carrier_id, is_front_patch_handle)
                ui.append(handle_widget_box)
            elif knitting_procedure.active == 3:
                ui.append(strap_height)
                ui.append(more_strap)
                ui.append(pn.Row(strap_front, strap_back))
                ui.append(pn.Row(strap_front_color, strap_back_color))
                strap.append([strap_front, strap_back, strap_front_color, strap_back_color])

            ui[0].append(html_pane)

        except ErrorException as error:
            error = pn.pane.Alert(error.message)
            ui.append(error)
            ui.append(back1)
        except AssertionError as error:
            error = pn.pane.Alert(str(error) + '\nPlease contact developers for more information')
            ui.append(error)
            ui.append(back1)
        except:
            error = pn.pane.Alert('## Internal errors occurred.' + '\nPlease contact developers for more information')
            ui.append(error)
            ui.append(back1)
    else:
        error = pn.pane.Alert('Knit speak entered does not match with pattern type')
        ui.insert(0, error)


def _back_to_start(event):
    ui.clear()
    ui.append(widget1)


def _update_graph(event):
    # try:
    while isinstance(ui[0], type(pn.pane.Alert())):
        ui.pop(0)
    global html_graph
    global knit_graph
    final_html_graph = None
    final_knit_graph = None
    if knitting_procedure.active == 2: # Hole
        if pattern_type.active == 0: # Tube
            complete_nodes_dict = []
            pattern = re.compile("^([0-9]*,)*[0-9]+$")
            for i in range(len(hole)):
                current = hole[i].value
                if pattern.match(current):
                    complete_nodes_dict.append([int(i) for i in current.split(",")])
                else:
                    error = pn.pane.Alert('## Wrong Input Format\nExample Input Format for Hole Nodes: 1,2,3,4,5,6')
                    ui.insert(0, error)
                    complete_nodes_dict = []
                    break

            if len(complete_nodes_dict) != 0:
                final_html_graph, final_knit_graph = generate_final_graph_hole("Tube" if pattern_type.active == 0 else "Sheet",
                                                                               "Hole", complete_nodes_dict, knit_graph)
        elif pattern_type.active == 1: # Sheet
            complete_nodes_dict = {}
            pattern = re.compile("^([0-9]*,)*[0-9]+$")
            for i in range(len(hole)):
                current = hole[i].value
                current_carrier = int(hole_carrier[i].value)
                if pattern.match(current):
                    complete_nodes_dict.update({current_carrier: [int(i) for i in current.split(",")]})
                else:
                    error = pn.pane.Alert('## Wrong Input Format\nExample Input Format for Hole Nodes: 1,2,3,4,5,6')
                    ui.insert(0, error)
                    complete_nodes_dict = {}
                    break

            print(str(complete_nodes_dict))
            if len(complete_nodes_dict) != 0:
                final_html_graph, final_knit_graph = generate_final_graph_hole(
                    "Tube" if pattern_type.active == 0 else "Sheet",
                    "Hole", complete_nodes_dict, knit_graph)

    elif knitting_procedure.active == 1: # pocket
        pattern = re.compile("^(\([0-9]+,[0-9]+\), )*\([0-9]+,[0-9]+\)$")
        if pattern.match(left_keynodes_pocket.value) and pattern.match(right_keynodes_pocket.value):
            left_vertices, right_vertices = parse_left_right_vertices(left_keynodes_pocket.value, right_keynodes_pocket.value)
            right_options = right_checkbox.labels
            left_options = left_checkbox.labels
            right_bools = []
            left_bools = []

            for i in range(0, len(right_options)):
                if i in right_checkbox.active:
                    right_bools.append(True)
                else:
                    right_bools.append(False)

            for i in range(0, len(left_options)):
                if i in left_checkbox.active:
                    left_bools.append(True)
                else:
                    left_bools.append(False)


            final_html_graph, final_knit_graph = generate_final_graph_pocket("Tube" if pattern_type.active == 0 else "Sheet",
                                                                             "Pocket",
                                                                             int(yarn_carrier.value),
                                                                             int(pocket_yarn_carrier_id.value),
                                                                             knit_graph,
                                                                             is_front_patch_pocket.active,
                                                                             left_vertices,
                                                                             right_vertices,
                                                                             close_top_pocket.active, right_bools, left_bools)
        else:
            error = pn.pane.Alert('## Wrong Input Format\nExample Input Format for Vertex Coordinates: (1,2), (3,4), (5,6)')
            ui.insert(0, error)
    elif knitting_procedure.active == 0: # Handle
        pattern = re.compile("^(\([0-9]+,[0-9]+\), )*\([0-9]+,[0-9]+\)$")
        if pattern.match(left_keynodes_handle.value) and pattern.match(right_keynodes_handle.value):
            left_vertices, right_vertices = parse_left_right_vertices(left_keynodes_handle.value, right_keynodes_handle.value)
            final_html_graph, final_knit_graph = generate_final_graph_handle("Tube" if pattern_type.active == 0 else "Sheet",
                                                                             "Handle",
                                                                             int(yarn_carrier.value),
                                                                             int(handle_yarn_carrier_id.value), knit_graph,
                                                                             is_front_patch_handle.active, left_vertices,
                                                                             right_vertices)
        else:
            error = pn.pane.Alert('## Wrong Input Format\nExample Input Format for Vertex Coordinates: (1,2), (3,4), (5,6)')
            ui.insert(0, error)

    elif knitting_procedure.active == 3: # Strap
        strap_coor_info = {}
        pattern = re.compile("^\([0-9]+, [0-9]+\)$")
        j = 1

        for i in range(len(strap)):
            current = strap[i]
            if pattern.match(current[0].value) and pattern.match(current[1].value):
                tup_front = current[0].value.replace('(', '')
                tup_front = tup_front.replace(')', '')
                tup_back = current[1].value.replace('(', '')
                tup_back = tup_back.replace(')', '')
                color_front = int(current[2].value)
                color_back = int(current[3].value)
                strap_coor_info.update({j: {'front': [tuple(map(int, tup_front.split(', '))), color_front],
                                            'back': [tuple(map(int, tup_back.split(', '))), color_back]}})
            else:
                error = pn.pane.Alert('## Wrong Input Format\nExample Input Format for Front or Back Vertex Coordinate: (1, 2)')
                ui.insert(0, error)
                strap_coor_info = {}
                break

        if len(strap_coor_info) != 0:
            final_html_graph, final_knit_graph = generate_final_graph_strap("Tube",
                                                                            "Strap",
                                                                            int(yarn_carrier.value),
                                                                            int(strap_height.value),
                                                                            knit_graph,
                                                                            strap_coor_info)

    ui[0].pop(1)
    ui[0].append(final_html_graph)
    html_graph = final_html_graph
    knit_graph = final_knit_graph

    # except ErrorException as error:
    #     error = pn.pane.Alert(error.message)
    #     ui.insert(0, error)
    # except AssertionError as error:
    #     error = pn.pane.Alert(str(error) + '\nPlease contact developers for more information')
    #     ui.insert(0, error)
    # except:
    #     error = pn.pane.Alert('Internal errors occurred.' + '\nPlease contact developers for more information')
    #     ui.insert(0, error)

def _more_hole_sheet(event):
    new_hole_nodes = TextInput(title='Hole Nodes', placeholder='Node IDs to delete', width=160)
    new_hole_carrier = Select(title='Yarn ID', options=yarn_carrier_options, value=yarn_carrier_options[0], width=160)
    hole.append(new_hole_nodes)
    hole_carrier.append(new_hole_carrier)
    ui.append(pn.Row(new_hole_carrier, new_hole_nodes))

def _more_hole_tube(event):
    new_hole_nodes = TextInput(title='Hole Nodes', placeholder='Node IDs to delete', width=320)
    hole.append(new_hole_nodes)
    ui.append(new_hole_nodes)

def _more_strap(event):
    if len(ui) < 11:
        new_strap_front = TextInput(title='Strap ' + str(int((len(ui) / 2) - 0.5)) + ' Front', value='', width=160)
        new_strap_back = TextInput(title='Strap ' + str(int((len(ui) / 2) - 0.5)) + ' Back', value='', width=160)
        new_strap_front_color = Select(name='Yarn ID for Strap ' + str(int((len(ui) / 2) - 0.5)) + 'Front', options=yarn_carrier_options, width=160)
        new_strap_back_color = Select(name='Yarn ID for Strap ' + str(int((len(ui) / 2) - 0.5)) + ' Back', options=yarn_carrier_options, width=160)
        ui.append(pn.Row(new_strap_front, new_strap_back))
        ui.append(pn.Row(new_strap_front_color, new_strap_back_color))
        strap.append([new_strap_front, new_strap_back, new_strap_front_color, new_strap_back_color])
    else:
        error = pn.pane.Alert('## Maximum of 4 straps allowed')
        ui.insert(0, error)

def _confirm_graph(event):
    ui.clear()
    ui.append(widget3)

def _confirm_file_name(event):
    global knit_graph
    generate_file(knit_graph, filename_input.value_input + '.k')
    file_download = pn.widgets.FileDownload(file=filename_input.value + '.k', embed=True, button_type='success')
    ui[0].append(file_download)


def _back_to_graph(event):
    ui.clear()
    ui.append(widget2)

def _confirm_tuples(event):
    left_vertices, right_vertices = parse_left_right_vertices(left_keynodes_pocket.value, right_keynodes_pocket.value)
    right_options = []
    left_options = []
    for i in range(0, len(right_vertices) - 1):
        right_options.append("Connect " + str(right_vertices[i]) + " and " + str(right_vertices[i + 1]))

    for i in range(0, len(left_vertices) - 1):
        left_options.append("Connect " + str(left_vertices[i]) + " and " + str(left_vertices[i + 1]))

    if right_options != [] and left_options != [] and (left_options != left_checkbox.labels or right_options != right_checkbox.labels):
        if left_checkbox.labels != []:
            ui.pop(len(ui) - 2)
        if right_checkbox.labels != []:
            ui.pop(len(ui) - 1)

        left_checkbox.labels = left_options
        right_checkbox.labels = right_options

        ui.append(pn.WidgetBox("## Connections on Small Wale Side", left_checkbox))
        ui.append(pn.WidgetBox("## Connections on Big Wale Side", right_checkbox))


def parse_left_right_vertices(left_string, right_string):
    left_vertices = []
    right_vertices = []

    left_split = left_string.split(", ")
    right_split = right_string.split(", ")
    for i in range(0, len(left_split)):
        tuple_l = left_split[i].replace('(', '')
        tuple_l = tuple_l.replace(')', '')
        left_vertices.append(tuple(map(int, tuple_l.split(','))))
    for i in range(0, len(right_split)):
        tuple_r = right_split[i].replace('(', '')
        tuple_r = tuple_r.replace(')', '')
        right_vertices.append(tuple(map(int, tuple_r.split(','))))

    return left_vertices, right_vertices


create_knit_graph_button.on_click(_create_knit_graph)
back1.on_click(_back_to_start)
update_map_button.on_click(_update_graph)
confirm_graph.on_click(_confirm_graph)
back2.on_click(_back_to_graph)
more_hole_sheet.on_click(_more_hole_sheet)
confirm_filename.on_click(_confirm_file_name)
more_hole_tube.on_click(_more_hole_tube)
confirm_tuples_pocket.on_click(_confirm_tuples)
more_strap.on_click(_more_strap)

# ui
ui.append(widget1)
ui.servable()