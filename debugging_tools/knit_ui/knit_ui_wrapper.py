from knitspeak_compiler.knitspeak_compiler import Knitspeak_Compiler
from debugging_tools.final_knit_graph_viz import knitGraph_visualizer
from knitting_machine.final_knitgraph_to_knitout import Knitout_Generator
from debugging_tools.simple_knitgraph_generator import Simple_Knitgraph_Generator
from debugging_tools.polygon_generator import Polygon_Generator
from Modification_Generator.New_Mul_Hole_Generator_on_Sheet_KS import Hole_Generator_on_Sheet
from Modification_Generator.New_Mul_Hole_Generator_on_Tube_KS import Hole_Generator_on_Tube
from Modification_Generator.New_Pocket_Generator_on_Sheet_KS import Pocket_Generator_on_Sheet
from Modification_Generator.New_Pocket_Generator_on_Tube_KS import Pocket_Generator_on_Tube
from Modification_Generator.Handle_Generator_on_Sheet_KS import Handle_Generator_on_Sheet
from Modification_Generator.Handle_Generator_on_Tube_KS import Handle_Generator_on_Tube
from Modification_Generator.New_Strap_Generator_on_Tube_KS import Strap_Generator_on_Tube
from Modification_Generator.New_Strap_Generator_on_Sheet_KS import Strap_Generator_on_Sheet
from Modification_Generator.New_Strap_Without_Hole_Generator_on_Sheet_KS import Strap_Without_Hole_Generator_on_Sheet
from Modification_Generator.New_Strap_With_Hole_Generator_on_Sheet_KS import Strap_With_Hole_Generator_on_Sheet
from Modification_Generator.New_Strap_Without_Hole_Generator_on_Tube_KS import Strap_Without_Hole_Generator_on_Tube
from Modification_Generator.New_Strap_With_Hole_Generator_on_Tube_KS import Strap_With_Hole_Generator_on_Tube
from debugging_tools.exceptions import ErrorException

def generate_initial_graph(pattern_used, gauge, color, width, height, knit_speak_procedure):
    """
    note that if the generated polygon look weird, specifically wales are not align, probably caused by the improper gauge setting used
    below.
    """
    sheet_yarn_carrier_id = color
    compiler = Knitspeak_Compiler(carrier_id=sheet_yarn_carrier_id)
    try:
        knit_graph = compiler.compile(starting_width=width, row_count=height, object_type=knit_speak_procedure.lower(),
                                      pattern=pattern_used)
    except:
        raise ErrorException(f'Error when parsing the knit speak. Please check if the entered knit speak and the size is valid.')
    knit_graph.gauge = gauge    
    loop_ids_to_course, course_to_loop_ids = knit_graph.get_courses()
    loop_ids_to_wale, wale_to_loop_ids = knit_graph.get_wales()
    node_on_front_or_back = knit_graph.get_node_bed()
    course_to_loops_on_front_part_of_the_tube, course_to_loops_on_back_part_of_the_tube = knit_graph.get_node_bed_for_courses()
    node_to_course_and_wale = knit_graph.get_node_course_and_wale()
    course_and_wale_and_bed_to_node = knit_graph.get_course_and_wale_and_bed_to_node()
    #----mar 19
    max_wale_id_front_and_back = knit_graph.get_min_and_max_wale_id_on_course_on_bed()
    knit_graph.update_wales_to_reduce_float()
    knit_graph.adjust_overall_slanting()
    #----
    knit_graph.update_parent_offsets()
    #---mar 30
    knit_graph.bind_off_final_course()
    #---
    KnitGraph_Visualizer = knitGraph_visualizer(knit_graph=knit_graph)
    return KnitGraph_Visualizer.visualize()

def generate_final_graph_hole(pattern_english, modification, nodes_dict, knit_graph):
    if (pattern_english == "Sheet" and modification == "Hole"):
        hole_generator = Hole_Generator_on_Sheet(yarns_and_holes_to_add=nodes_dict, knitgraph=knit_graph)
        knitGraph = hole_generator.add_hole()
        KnitGraph_Visualizer = knitGraph_visualizer(knitGraph)
        return KnitGraph_Visualizer.visualize()

    if (pattern_english == "Tube" and modification == "Hole"):
        hole_generator = Hole_Generator_on_Tube(list_of_holes=nodes_dict, knitgraph=knit_graph)
        knitGraph = hole_generator.add_hole()
        KnitGraph_Visualizer = knitGraph_visualizer(knitGraph)
        html_graph, knit_graph = KnitGraph_Visualizer.visualize()
        assert html_graph is not None
        assert knit_graph is not None
        return KnitGraph_Visualizer.visualize()

def generate_final_graph_pocket(pattern_english, modification, original_id, pocket_id, knit_graph, front_patch,
                                left_keys, right_keys, top_connection, right_connection, left_connection):
    if (pattern_english == "Sheet" and modification == "Pocket"):
        pocket_generator = Pocket_Generator_on_Sheet(parent_knitgraph=knit_graph, sheet_yarn_carrier_id=original_id,
                                                     pocket_yarn_carrier_id=pocket_id, is_front_patch=front_patch,
                                                     left_keynodes_child_fabric=left_keys,
                                                     right_keynodes_child_fabric=right_keys, close_top=top_connection,
                                                     edge_connection_left_side=left_connection,
                                                     edge_connection_right_side=right_connection)
        knitGraph = pocket_generator.build_pocket_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(knitGraph)
        return KnitGraph_Visualizer.visualize()

    if (pattern_english == "Tube" and modification == "Pocket"):
        pocket_generator = Pocket_Generator_on_Tube(parent_knitgraph=knit_graph, tube_yarn_carrier_id=original_id,
                                                    pocket_yarn_carrier_id=pocket_id, is_front_patch=front_patch,
                                                    left_keynodes_child_fabric=left_keys,
                                                    right_keynodes_child_fabric=right_keys, close_top=top_connection,
                                                    edge_connection_left_side=left_connection,
                                                    edge_connection_right_side=right_connection)
        knitGraph = pocket_generator.build_pocket_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(knitGraph)
        return KnitGraph_Visualizer.visualize()

def generate_final_graph_handle(pattern_english, modification, original_id, handle_id, knit_graph, front_patch,
                                left_keys, right_keys):
    if (pattern_english == "Sheet" and modification == "Handle"):
        handle_generator = Handle_Generator_on_Sheet(parent_knitgraph=knit_graph,
                                                     sheet_yarn_carrier_id=original_id,
                                                     handle_yarn_carrier_id=handle_id, is_front_patch=front_patch,
                                                     left_keynodes_child_fabric=left_keys,
                                                     right_keynodes_child_fabric=right_keys)
        knitGraph = handle_generator.build_handle_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(knitGraph)
        return KnitGraph_Visualizer.visualize()

    if (pattern_english == "Tube" and modification == "Handle"):
        handle_generator = Handle_Generator_on_Tube(parent_knitgraph=knit_graph,
                                                    tube_yarn_carrier_id=original_id, handle_yarn_carrier_id=handle_id,
                                                    is_front_patch=front_patch,
                                                    left_keynodes_child_fabric=left_keys,
                                                    right_keynodes_child_fabric=right_keys)
        knitGraph = handle_generator.build_handle_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(knitGraph)
        return KnitGraph_Visualizer.visualize()

def generate_final_graph_strap(pattern_english, modification, original_id, strap_id, knit_graph, front_patch,
                                keys, strap_length):
    if (pattern_english == "Sheet" and modification == "Strap"):
        strap_generator = Strap_Without_Hole_Generator_on_Sheet(parent_knitgraph=knit_graph,
                                                  sheet_yarn_carrier_id=original_id,
                                                  strap_yarn_carrier_id=strap_id,
                                                  is_front_patch=front_patch, 
                                                  keynode_child_fabric=keys, 
                                                  strap_length=strap_length)
        strap_graph, updated_child_graph, parent_knitgraph = strap_generator.build_strap_without_hole_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(strap_graph)
        return KnitGraph_Visualizer.visualize(), updated_child_graph, parent_knitgraph
    
    if (pattern_english == "Tube" and modification == "Strap"):
        strap_generator = Strap_Without_Hole_Generator_on_Tube(parent_knitgraph=knit_graph,
                                                  tube_yarn_carrier_id=original_id,
                                                  strap_yarn_carrier_id=strap_id,
                                                  is_front_patch=front_patch, 
                                                  keynode_child_fabric=keys, 
                                                  strap_length=strap_length)
        strap_graph, updated_child_graph, parent_knitgraph = strap_generator.build_strap_without_hole_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(strap_graph)
        return KnitGraph_Visualizer.visualize(), updated_child_graph, parent_knitgraph

def general_final_strap_graph_with_hole(pattern_english, modification, strap_without_hole_knitgraph, parent_knitgraph, child_knitgraph, yarns_and_holes_to_add):
    if (pattern_english == "Sheet" and modification == "Strap"):
        #     def __init__(self, strap_without_hole_knitgraph: Knit_Graph, parent_knitgraph: Knit_Graph, child_knitgraph: Knit_Graph, yarns_and_holes_to_add):
        strap_generator = Strap_With_Hole_Generator_on_Sheet(strap_without_hole_knitgraph,
                                                  parent_knitgraph,
                                                  child_knitgraph,
                                                  yarns_and_holes_to_add)
        strap_graph = strap_generator.build_strap_with_hole_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(strap_graph)
        return KnitGraph_Visualizer.visualize()
    
    if (pattern_english == "Tube" and modification == "Strap"):
        #     def __init__(self, strap_without_hole_knitgraph: Knit_Graph, parent_knitgraph: Knit_Graph, child_knitgraph: Knit_Graph, yarns_and_holes_to_add):
        strap_generator = Strap_With_Hole_Generator_on_Tube(strap_without_hole_knitgraph,
                                                  parent_knitgraph,
                                                  child_knitgraph,
                                                  yarns_and_holes_to_add)
        strap_graph = strap_generator.build_strap_with_hole_graph()
        KnitGraph_Visualizer = knitGraph_visualizer(strap_graph)
        return KnitGraph_Visualizer.visualize()
    
def generate_file(knitGraph, file_name):
    generator = Knitout_Generator(knitGraph)
    return generator.write_instructions(file_name)
