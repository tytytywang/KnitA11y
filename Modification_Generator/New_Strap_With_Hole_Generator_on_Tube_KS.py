from typing import Optional, List, Dict, Tuple
import copy
from knit_graphs.Yarn import Yarn
from knit_graphs.Knit_Graph import Knit_Graph, Pull_Direction
from debugging_tools.final_knit_graph_viz import knitGraph_visualizer
from debugging_tools.simple_knitgraph_generator import Simple_Knitgraph_Generator
from debugging_tools.polygon_generator import Polygon_Generator
from knitspeak_compiler.knitspeak_compiler import Knitspeak_Compiler
from debugging_tools.exceptions import ErrorException
from Modification_Generator.New_Mul_Hole_Generator_on_Sheet_KS import Hole_Generator_on_Sheet

class Strap_With_Hole_Generator_on_Tube:
    def __init__(self, strap_without_hole_knitgraph: Knit_Graph, parent_knitgraph: Knit_Graph, child_knitgraph: Knit_Graph, yarns_and_holes_to_add):
        """
        :param left_keypoints: List of (course_id, wale_id) of the spiky points on the left side of the pattern.
        :param right_keypoints: List of (course_id, wale_id) of the spiky points on the right side of the pattern.
        (Note that the keypoints should be enter in order of from bottom to top for each side, and we assume the origin
        of the pattern is (0, 0). ).
        Note that differ from pocket case, both sides of strap need to be attached to the parent fabric, thus we do not provide the edge_connection_left_side and edge_connection_right_side as params anymore. 
        In addition, close_top is also not provided. 
        """
        self.strap_with_hole_graph: Knit_Graph = Knit_Graph()
        # self.strap_with_hole_graph: Knit_Graph = copy.deepcopy(strap_without_hole_knitgraph)
        self.child_knitgraph_with_hole: Knit_Graph = Knit_Graph()
        self.child_knitgraph_with_hole_coors_connectivity: List[Tuple] = []
        self.strap_without_hole_knitgraph: Knit_Graph = copy.deepcopy(strap_without_hole_knitgraph)
        self.strap_without_hole_knitgraph_coors_connectivity: List[Tuple] = []
        self.parent_knitgraph: Knit_Graph = parent_knitgraph
        self.child_knitgraph: Knit_Graph = child_knitgraph
        self.child_knitgraph_deep_copy = copy.deepcopy(self.child_knitgraph)
        self.child_knitgraph_nodes = self.child_knitgraph.graph.nodes
        #
    
        #
        self.parent_knitgraph.loop_ids_to_course: Dict[int, float] = parent_knitgraph.loop_ids_to_course
        self.parent_knitgraph.course_to_loop_ids: Dict[float, List[int]] = parent_knitgraph.course_to_loop_ids
        self.parent_knitgraph.loop_ids_to_wale: Dict[int, float] = parent_knitgraph.loop_ids_to_wale
        self.parent_knitgraph.wale_to_loop_ids: Dict[float, List[int]] = parent_knitgraph.wale_to_loop_ids
        self.parent_knitgraph.node_to_course_and_wale: Dict[int, Tuple(int, int)] = parent_knitgraph.node_to_course_and_wale
        self.parent_knitgraph.node_on_front_or_back: Dict[int, str] = parent_knitgraph.node_on_front_or_back
        self.parent_knitgraph_course_and_wale_to_node: Dict[Tuple[int, int], int] = {tuple(v): k for k, v in parent_knitgraph.node_to_course_and_wale.items()}
        self.parent_knitgraph_course_id_to_wale_ids: Dict[int, List[int]] = {} 
        # 
        self.child_knitgraph.course_to_loop_ids: Dict[float, List[int]]
        self.child_knitgraph.node_to_course_and_wale: Dict[int, Tuple(int, int)]
        self.child_knitgraph_course_and_wale_to_node: Dict[Tuple[int, int], int] 
        self.child_knitgraph_course_id_to_wale_ids: Dict[int, List[int]] = {}
        
        #    
        self.strap_with_hole_graph.node_to_course_and_wale: Dict[int, Tuple(int, int)]
        self.strap_with_hole_graph.node_on_front_or_back: Dict[int, str] = {}
        #
        self.yarns_and_holes_to_add = yarns_and_holes_to_add
        self.wale_dist = int(1/self.strap_without_hole_knitgraph.gauge)

    def add_hole_on_strap(self):
        hole_generator = Hole_Generator_on_Sheet(self.yarns_and_holes_to_add, knitgraph = self.child_knitgraph)  
        self.child_knitgraph_with_hole = hole_generator.add_hole()
        # KnitGraph_Visualizer = knitGraph_visualizer(self.child_knitgraph_with_hole)
        # KnitGraph_Visualizer.visualize()
        # KnitGraph_Visualizer = knitGraph_visualizer(self.parent_knitgraph)
        # KnitGraph_Visualizer.visualize()
        return self.child_knitgraph_with_hole
                 
    def read_connectivity_from_child_knitgraph_with_hole(self):
        """
        transform edge_data_list where connectivity is expressed in terms of node id into coor_connectivity where connectivity is
        expressed in terms of coordinate in formart of (course_id, wale_id). This transform is needed because we are going to 
        change the node order to represent the correct knitting operation order when knitting a strap, thus at each coor, the node
        id would change, that's why we need to update node_to_course_and_wale for both parent graph and child graph.
        """
        child_knitgraph_with_hole_edge_data_list = self.child_knitgraph_with_hole.graph.edges(data=True)
        for edge_data in child_knitgraph_with_hole_edge_data_list:
            node = edge_data[1]
            node_coor = self.child_knitgraph_with_hole.node_to_course_and_wale[node]
            predecessor = edge_data[0]
            predecessor_coor = self.child_knitgraph_with_hole.node_to_course_and_wale[predecessor]
            attr_dict = edge_data[2]
            self.child_knitgraph_with_hole_coors_connectivity.append([predecessor_coor, node_coor, attr_dict])

    def update_stitches_on_strap_without_hole_knitgraph(self):
        self.strap_with_hole_graph = copy.deepcopy(self.strap_without_hole_knitgraph)
        # KnitGraph_Visualizer = knitGraph_visualizer(self.strap_with_hole_graph)
        # KnitGraph_Visualizer.visualize()

        #delete hole nodes and change (remove&add) yarns
        for hole in self.yarns_and_holes_to_add.values():
            self.strap_with_hole_graph.graph.remove_nodes_from(hole)
            self.strap_with_hole_graph.yarns['strap_yarn'].yarn_graph.remove_nodes_from(hole)
        # KnitGraph_Visualizer = knitGraph_visualizer(self.strap_with_hole_graph)
        # KnitGraph_Visualizer.visualize()

        for node in self.child_knitgraph_with_hole.graph.nodes:
            #check if node is on a new yarn besides parent fabric yarn and child fabric yarn
            if node not in self.child_knitgraph_with_hole.yarns['strap_yarn'].yarn_graph.nodes:
                #find which yarn the node is on
                for yarn in [*self.child_knitgraph_with_hole.yarns.values()]:
                    if node in yarn: 
                        break
                self.strap_with_hole_graph.add_yarn(yarn)                
                if node not in yarn.yarn_graph.nodes:
                    child_id, loop = yarn.add_loop_to_end(loop_id = node)
                self.strap_with_hole_graph.yarns['strap_yarn'].yarn_graph.remove_node(node)
        print(f'self.strap_with_hole_graph.yarns is {self.strap_with_hole_graph.yarns}')
        print(f'self.parent_knitgraph.yarns is {self.parent_knitgraph.yarns}')
        print(f'self.child_knitgraph.yarns is {self.child_knitgraph.yarns}')
        print(f'self.child_knitgraph_with_hole.yarns is {self.child_knitgraph_with_hole.yarns}')

        #then, reconnect the stitches: since the only stitches change can only happen on the self.child_fabric_with_hole, we only use the connectivity from it below
        for (parent_coor, child_coor, attr_dict) in self.child_knitgraph_with_hole_coors_connectivity:
            parent_node = self.child_knitgraph_with_hole.course_and_wale_to_node[parent_coor]
            child_node = self.child_knitgraph_with_hole.course_and_wale_to_node[child_coor]
            if (parent_node, child_node) not in self.child_knitgraph_deep_copy.graph.edges:
                pull_direction = attr_dict['pull_direction']
                depth = attr_dict['depth']
                parent_offset = attr_dict['parent_offset']
                self.strap_with_hole_graph.connect_loops(parent_node, child_node, pull_direction = pull_direction, depth = depth, parent_offset = int(parent_offset/self.wale_dist)) 
   
    def build_strap_with_hole_graph(self) -> Knit_Graph:   
        self.add_hole_on_strap()
        self.read_connectivity_from_child_knitgraph_with_hole()
        self.update_stitches_on_strap_without_hole_knitgraph()
        return self.strap_with_hole_graph
  