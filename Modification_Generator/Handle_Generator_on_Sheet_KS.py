from typing import Optional, List, Dict, Tuple
from knit_graphs.Yarn import Yarn
from knit_graphs.Knit_Graph import Knit_Graph, Pull_Direction
from debugging_tools.final_knit_graph_viz import knitGraph_visualizer
from debugging_tools.simple_knitgraph_generator import Simple_Knitgraph_Generator
from debugging_tools.polygon_generator import Polygon_Generator
from knitspeak_compiler.knitspeak_compiler import Knitspeak_Compiler
from debugging_tools.exceptions import ErrorException

class Handle_Generator_on_Sheet:
    def __init__(self, parent_knitgraph: Knit_Graph, sheet_yarn_carrier_id: int, handle_yarn_carrier_id: int, is_front_patch: bool, left_keynodes_child_fabric, right_keynodes_child_fabric):
        """
        :param left_keypoints: List of (course_id, wale_id) of the spiky points on the left side of the pattern.
        :param right_keypoints: List of (course_id, wale_id) of the spiky points on the right side of the pattern.
        (Note that the keypoints should be enter in order of from bottom to top for each side, and we assume the origin
        of the pattern is (0, 0). )
        """
        #self.handle_graph is handle graph, the result of processing given child graph and parent graph.
        self.handle_graph: Knit_Graph = Knit_Graph()
        self.parent_knitgraph: Knit_Graph = parent_knitgraph
        if self.parent_knitgraph.object_type != 'sheet':
            raise ErrorException(f'wrong object type of parent knitgraph')
        self.handle_graph.object_type = 'sheet'
        self.child_knitgraph: Knit_Graph = Knit_Graph()
        self.child_knitgraph.object_type = 'sheet'
        self.child_knitgraph_demo_yarn: Yarn = Yarn("demo_yarn", self.child_knitgraph, carrier_id = handle_yarn_carrier_id)
        self.child_knitgraph.add_yarn(self.child_knitgraph_demo_yarn)
        self.child_knitgraph_coors_connectivity: List[Tuple] = []
        self.parent_knitgraph_coors_connectivity: List[Tuple] = []
        self.left_keynodes_child_fabric: List[Tuple[int, int]] = left_keynodes_child_fabric
        self.right_keynodes_child_fabric: List[Tuple[int, int]] = right_keynodes_child_fabric
        if self.parent_knitgraph.gauge > 0.5:
            raise ErrorException(f'the gauge of given parent knitgraph has to be less than 0.5, and we set it to 0.5 which is sufficient to keep texture for sheet case') #otherwise it will mess up because xfers involved.
        self.handle_graph.gauge = self.child_knitgraph.gauge = self.parent_knitgraph.gauge #this is true for adding handle on sheet case
        self.wale_dist = int(1/self.parent_knitgraph.gauge)
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
        self.is_front_patch: bool  = is_front_patch
        # 
        self.child_knitgraph.course_to_loop_ids: Dict[float, List[int]]
        self.child_knitgraph.node_to_course_and_wale: Dict[int, Tuple(int, int)]
        self.child_knitgraph_course_and_wale_to_node: Dict[Tuple[int, int], int] 
        self.child_knitgraph_course_id_to_wale_ids: Dict[int, List[int]] = {}
        self.child_knitgraph.node_on_front_or_back: Dict[int, str] = {}
        #    
        if sheet_yarn_carrier_id == handle_yarn_carrier_id:
            raise ErrorException(f'yarn carrier id for sheet: {sheet_yarn_carrier_id} cannot be the same as yarn carrier id for tube: {handle_yarn_carrier_id}')
        self.sheet_yarn_carrier_id: int = sheet_yarn_carrier_id
        self.sheet_yarn: Yarn = Yarn("parent_yarn", self.handle_graph, carrier_id=self.sheet_yarn_carrier_id)
        self.handle_graph.add_yarn(self.sheet_yarn)
        self.handle_yarn_carrier_id: int = handle_yarn_carrier_id
        self.handle_yarn: Yarn = Yarn("handle_yarn", self.handle_graph, carrier_id=self.handle_yarn_carrier_id)
        self.handle_graph.add_yarn(self.handle_yarn)
        self.handle_graph.node_to_course_and_wale: Dict[int, Tuple(int, int)]
        self.handle_graph.node_on_front_or_back: Dict[int, str] = {}
        # use for connecting root nodes to split nodes     
        self.wale_id_offset: int

    def check_keynodes_validity(self): 
        """
        non-symmetry is now allowable for the shape.
        check if keynodes are entered correctly: for any two neighbor keynodes to be valid, to make sure
        no other keynodes is mistakenly ingored bewtween this range, delta wale_id % delta course_id should
        == 0.
        """
        # first ensure even for situation where keynode on the left side and the right side turns out to be the same,
        # e.g, a bottom vertex of a triangle, users enter that special keynode into both self.left_keynodes_child_fabric and
        # self.right_keynodes_child_fabric keynodes lists.
        first_keynode_left =  self.left_keynodes_child_fabric[0]
        last_keynode_left = self.left_keynodes_child_fabric[-1]
        first_keynode_right =  self.right_keynodes_child_fabric[0]
        last_keynode_right = self.right_keynodes_child_fabric[-1]
        if first_keynode_left[0] != first_keynode_right[0]:
            raise ErrorException(f'first keynode on the left and right do not share the same course_id')
        if last_keynode_left[0] != last_keynode_right[0]:
            raise ErrorException(f'last keynode on the left and right do not share the same course_id')
        # keynode check 1: gauge check
        if (first_keynode_right[1] - first_keynode_left[1]) % self.wale_dist != 0:
            raise ErrorException(f'wale distance between first keynodes does not match the gauge setup')
        if (last_keynode_right[1] - last_keynode_left[1]) % self.wale_dist != 0:
            raise ErrorException(f'wale distance between last keynodes does not match the gauge setup')
        # keynode check 2: slope check
        num_of_nodes_left_side = len(self.left_keynodes_child_fabric)
        num_of_nodes_right_side = len(self.right_keynodes_child_fabric)
        for i in range(1, num_of_nodes_left_side):
            curr_left_keynode = self.left_keynodes_child_fabric[i]
            last_left_keynode = self.left_keynodes_child_fabric[i-1] 
            width_change_left = curr_left_keynode[1] - last_left_keynode[1]
            increase_height_left = curr_left_keynode[0] - last_left_keynode[0]
            if width_change_left % self.wale_dist != 0:
                raise ErrorException(f'wale distance between keynodes {i-1} and {i} does not match the gauge setup')
            #check if any other keynodes might be missed in between 
            if width_change_left % increase_height_left != 0:
                print(f'some keynodes might exist bewtween given keynodes {last_left_keynode} and {curr_left_keynode} on the left side if these two keynodes are entered correctly')
                exit()
        for i in range(1, num_of_nodes_right_side):    
            curr_right_keynode = self.right_keynodes_child_fabric[i]
            last_right_keynode = self.right_keynodes_child_fabric[i-1]
            width_change_right = curr_right_keynode[1] - last_right_keynode[1]
            increase_height_right = curr_right_keynode[0] - last_right_keynode[0]
            if width_change_right % self.wale_dist != 0:
                raise ErrorException(f'wale distance between keynodes {i-1} and {i} does not match the gauge setup')
            if width_change_right % increase_height_right != 0:
                print(f'some keynodes might exist bewtween given keynodes {last_right_keynode} and {curr_right_keynode} on the right side if these two keynodes are entered correctly')
                exit()
                
    def generate_polygon_from_keynodes(self):
        self.check_keynodes_validity()
        # first process given keynodes on each side, to get starting node coordinate and ending node coordinate on each course.
        starting_nodes_coor = []
        ending_nodes_coor = []
        num_of_nodes_left_side = len(self.left_keynodes_child_fabric) 
        num_of_nodes_right_side = len(self.right_keynodes_child_fabric) 
        # for keynodes on the left side
        # before for loop, add the starting node on the first course
        starting_nodes_coor_on_first_course = ((self.left_keynodes_child_fabric[0][0], self.left_keynodes_child_fabric[0][1]))
        starting_nodes_coor.append(starting_nodes_coor_on_first_course)
        for i in range(1, num_of_nodes_left_side):
            curr_left_keynode = self.left_keynodes_child_fabric[i]
            last_left_keynode = self.left_keynodes_child_fabric[i-1]
            # if wale_id keeps the same between this course range, for courses in between, only need to increment the course_id for 
            # starting node 
            if curr_left_keynode[1] - last_left_keynode[1] == 0:
                wale_id = last_left_keynode[1]
                for course_id in range(last_left_keynode[0] + 1, curr_left_keynode[0] + 1):
                    starting_nodes_coor.append((course_id, wale_id))
            # if wale_id changes between this course range, for courses in between, also need to increment the wale_id by 
            # "wale_change_per_course" for starting node 
            elif curr_left_keynode[1] - last_left_keynode[1] != 0:
                wale_id = last_left_keynode[1]
                width_change_left = (curr_left_keynode[1] - last_left_keynode[1])
                height_increase_left = (curr_left_keynode[0] - last_left_keynode[0])
                wale_change_per_course = int(width_change_left / height_increase_left)
                for course_id in range(last_left_keynode[0] + 1, curr_left_keynode[0] + 1):
                    wale_id += wale_change_per_course
                    starting_nodes_coor.append((course_id, wale_id))
        # same for keynodes on the right side
        ending_nodes_coor_on_first_course = ((self.right_keynodes_child_fabric[0][0], self.right_keynodes_child_fabric[0][1]))
        ending_nodes_coor.append(ending_nodes_coor_on_first_course)
        for i in range(1, num_of_nodes_right_side):
            curr_right_keynode = self.right_keynodes_child_fabric[i]
            last_right_keynode = self.right_keynodes_child_fabric[i-1]
            if curr_right_keynode[1] - last_right_keynode[1] == 0:
                wale_id = last_right_keynode[1]
                for course_id in range(last_right_keynode[0] + 1, curr_right_keynode[0] + 1):
                    ending_nodes_coor.append((course_id, wale_id))
            elif curr_right_keynode[1] - last_right_keynode[1] != 0:
                wale_id = last_right_keynode[1]
                width_change_right = (curr_right_keynode[1] - last_right_keynode[1])
                height_increase_right = (curr_right_keynode[0] - last_right_keynode[0])
                wale_change_per_course = int(width_change_right / height_increase_right)
                for course_id in range(last_right_keynode[0] + 1, curr_right_keynode[0] + 1):
                    wale_id += wale_change_per_course
                    ending_nodes_coor.append((course_id, wale_id))
        print(f'starting_nodes_coor is {starting_nodes_coor}, ending_nodes_coor is {ending_nodes_coor}')

        #derive node_to_course_and_wale from above starting_nodes_coor and ending_nodes_coor
        node = 0
        node_to_course_and_wale = {}
        for i in range(len(starting_nodes_coor)):
            staring_node_wale_id = starting_nodes_coor[i][1]
            ending_node_wale_id = ending_nodes_coor[i][1]
            course_id = starting_nodes_coor[i][0]
            if i % 2 == 0:
                for wale_id in range(staring_node_wale_id, ending_node_wale_id + self.wale_dist, self.wale_dist):
                    node_to_course_and_wale[node] = (course_id, wale_id)
                    node += 1
            elif i % 2 == 1:
                for wale_id in range(ending_node_wale_id, staring_node_wale_id - self.wale_dist, -self.wale_dist):
                    node_to_course_and_wale[node] = (course_id, wale_id)
                    node += 1
        print(f'node_to_course_and_wale is {node_to_course_and_wale}')
        self.child_knitgraph.node_to_course_and_wale = node_to_course_and_wale
        #connect nodes on yarn
        for node in node_to_course_and_wale.keys():
            loop_id, loop = self.child_knitgraph_demo_yarn.add_loop_to_end()
            self.child_knitgraph.node_on_front_or_back[loop_id] = 'f' if self.is_front_patch == True else 'b'
            self.child_knitgraph.add_loop(loop)
        #get course_to_loop_ids
        course_to_loop_ids = {}
        course_id_start = starting_nodes_coor_on_first_course[0]
        course_id_end = starting_nodes_coor[-1][0]
        for course_id in range(course_id_start, course_id_end + 1):
            course_to_loop_ids[course_id] = []
        for node in self.child_knitgraph.graph.nodes:
            course_id = node_to_course_and_wale[node][0]
            course_to_loop_ids[course_id].append(node)
        print(f'course_to_loop_ids is {course_to_loop_ids}')
        self.child_knitgraph.course_to_loop_ids = course_to_loop_ids
        if max([*self.child_knitgraph.course_to_loop_ids.keys()]) >= max([*self.parent_knitgraph.course_to_loop_ids.keys()]):
            raise ErrorException(f"the height of child fabric exceeds that of parent fabric")
        #reverse node_to_course_and_wale to get course_and_wale_to_node
        course_and_wale_to_node = {}
        course_and_wale_to_node = {tuple(v): k for k, v in node_to_course_and_wale.items()}
        self.child_knitgraph_course_and_wale_to_node = course_and_wale_to_node
        #connect node stitches
        course_ids_before_final_course = [*course_to_loop_ids.keys()][:-1]
        for course_id in course_ids_before_final_course:
            for node in course_to_loop_ids[course_id]:
                wale_id = node_to_course_and_wale[node][1]
                #find upper neighbor node
                if (course_id + 1, wale_id) in course_and_wale_to_node.keys():
                    child_loop = course_and_wale_to_node[(course_id + 1, wale_id)]
                    self.child_knitgraph.connect_loops(node, child_loop)
        KnitGraph_Visualizer = knitGraph_visualizer(knit_graph = self.child_knitgraph)
        KnitGraph_Visualizer.visualize()
             
    def read_connectivity_from_knitgraph(self):
        """
        transform edge_data_list where connectivity is expressed in terms of node id into coor_connectivity where connectivity is
        expressed in terms of coordinate in formart of (course_id, wale_id). This transform is needed because we are going to 
        change the node order to represent the correct knitting operation order when knitting a handle, thus at each coor, the node
        id would change, that's why we need to update node_to_course_and_wale for both parent graph and child graph.
        """
        parent_knitgraph_edge_data_list = self.parent_knitgraph.graph.edges(data=True)
        child_knitgraph_edge_data_list = self.child_knitgraph.graph.edges(data=True)
        for edge_data in parent_knitgraph_edge_data_list:
            node = edge_data[1]
            node_coor = self.parent_knitgraph.node_to_course_and_wale[node]
            predecessor = edge_data[0]
            predecessor_coor = self.parent_knitgraph.node_to_course_and_wale[predecessor]
            attr_dict = edge_data[2]
            self.parent_knitgraph_coors_connectivity.append([predecessor_coor, node_coor, attr_dict])
        for edge_data in child_knitgraph_edge_data_list:
            node = edge_data[1]
            node_coor = self.child_knitgraph.node_to_course_and_wale[node]
            predecessor = edge_data[0]
            predecessor_coor = self.child_knitgraph.node_to_course_and_wale[predecessor]
            attr_dict = edge_data[2]
            self.child_knitgraph_coors_connectivity.append([predecessor_coor, node_coor, attr_dict])
            
    def get_course_id_to_wale_ids(self):
        for course_id in [*self.parent_knitgraph.course_to_loop_ids.keys()]:
            start_node = self.parent_knitgraph.course_to_loop_ids[course_id][0]
            last_node = self.parent_knitgraph.course_to_loop_ids[course_id][-1]
            start_wale_id = self.parent_knitgraph.node_to_course_and_wale[start_node][1]
            last_wale_id = self.parent_knitgraph.node_to_course_and_wale[last_node][1]
            self.parent_knitgraph_course_id_to_wale_ids[course_id] = []
            if course_id % 2 == 0:
                for wale_id in range(start_wale_id, last_wale_id+self.wale_dist, self.wale_dist):
                    self.parent_knitgraph_course_id_to_wale_ids[course_id].append(wale_id)
            if course_id % 2 == 1:
                for wale_id in range(start_wale_id, last_wale_id-self.wale_dist, -self.wale_dist):
                    self.parent_knitgraph_course_id_to_wale_ids[course_id].append(wale_id)
        #for child graph
        for i, course_id in enumerate([*self.child_knitgraph.course_to_loop_ids.keys()]):
            start_node = self.child_knitgraph.course_to_loop_ids[course_id][0]
            last_node = self.child_knitgraph.course_to_loop_ids[course_id][-1]
            start_wale_id = self.child_knitgraph.node_to_course_and_wale[start_node][1]
            last_wale_id = self.child_knitgraph.node_to_course_and_wale[last_node][1]
            self.child_knitgraph_course_id_to_wale_ids[course_id] = []
            if i % 2 == 0:
                for wale_id in range(start_wale_id, last_wale_id+self.wale_dist, self.wale_dist):
                    self.child_knitgraph_course_id_to_wale_ids[course_id].append(wale_id)
            if i % 2 == 1:
                for wale_id in range(start_wale_id, last_wale_id-self.wale_dist, -self.wale_dist):
                    self.child_knitgraph_course_id_to_wale_ids[course_id].append(wale_id)

    def build_rows_on_parent_graph_just_above_splitting_course_id(self):
        #here we can clear old self.parent_knitgraph._node_to_course_and_wale since we don't use it anymore hereafter
        self.parent_knitgraph.node_to_course_and_wale = {}
        start_course_id = [*self.parent_knitgraph_course_id_to_wale_ids.keys()][0]
        stop_course_id = [*self.child_knitgraph.course_to_loop_ids.keys()][0]
        for course_id in range(start_course_id, stop_course_id + 1):
            for i in range(len(self.parent_knitgraph_course_id_to_wale_ids[course_id])):
                loop_id, loop = self.sheet_yarn.add_loop_to_end()
                self.handle_graph.add_loop(loop)
                wale_id = self.parent_knitgraph_course_id_to_wale_ids[course_id][i]
                self.parent_knitgraph.node_to_course_and_wale[loop_id] = (course_id, wale_id)
                self.parent_knitgraph_course_and_wale_to_node[(course_id, wale_id)] = loop_id
                self.handle_graph.node_on_front_or_back[loop_id] = 'f' if self.is_front_patch == False else 'b'
    
    def grow_one_row(self, course_id, on_parent_graph: bool):
        if on_parent_graph == True:
            # update course and wale info of each node for parent graph 
            self.parent_knitgraph.course_to_loop_ids[course_id] = []
            for i in range(len(self.parent_knitgraph_course_id_to_wale_ids[course_id])):
                loop_id, loop = self.sheet_yarn.add_loop_to_end()
                self.handle_graph.add_loop(loop)
                wale_id = self.parent_knitgraph_course_id_to_wale_ids[course_id][i]
                self.parent_knitgraph.node_to_course_and_wale[loop_id] = (course_id, wale_id)
                self.parent_knitgraph_course_and_wale_to_node[(course_id, wale_id)] = loop_id
                self.parent_knitgraph.course_to_loop_ids[course_id].append(loop_id)
                self.handle_graph.node_on_front_or_back[loop_id] = 'f' if self.is_front_patch == False else 'b'
        elif on_parent_graph == False:
            # update course and wale info of each node for child graph.
            self.child_knitgraph.course_to_loop_ids[course_id] = []
            for i in range(len(self.child_knitgraph_course_id_to_wale_ids[course_id])):
                loop_id, loop = self.handle_yarn.add_loop_to_end()
                self.handle_graph.add_loop(loop)
                wale_id = self.child_knitgraph_course_id_to_wale_ids[course_id][i]
                self.child_knitgraph.node_to_course_and_wale[loop_id] = (course_id, wale_id)
                self.child_knitgraph_course_and_wale_to_node[(course_id, wale_id)] = loop_id
                self.child_knitgraph.course_to_loop_ids[course_id].append(loop_id)
                self.handle_graph.node_on_front_or_back[loop_id] = 'f' if self.is_front_patch == True else 'b'
    
    def get_split_nodes_on_each_edge_on_child_fabric(self):
        """
        this is used to get the keynodes of child fabric, (i.e., what we called split node in branch structure) 
        and organized in segments. like each edge mapped to the keynodes on this edge, so this dict would of course have repetitive nodes.
        """
        #ordered from bottom to top, just like the order we enter the keynodes for polygon on each side
        edge_nodes_smaller_wale_side_child: Dict[int: List[int]] = {} 
        edge_nodes_bigger_wale_side_child: Dict[int: List[int]] = {}
        num_of_nodes_left_side = len(self.left_keynodes_child_fabric)
        num_of_nodes_right_side = len(self.right_keynodes_child_fabric)
        j = 0
        for i in range(1, num_of_nodes_left_side):
            edge_nodes_smaller_wale_side_child[i-1] = [] # i-1 represents how the edge is indexed. Specifically, first edge would be indexed as 0 and so on so forth.
            curr_left_keynode = self.left_keynodes_child_fabric[i]
            curr_course_id = curr_left_keynode[0]
            last_left_keynode = self.left_keynodes_child_fabric[i-1] 
            last_course_id = last_left_keynode[0]
            # here we change from course_id % 2 to j % 2 because we want the first course in in the direction of 
            # left to right to make it consistent with machine in direction.
            for course_id in range(last_course_id, curr_course_id+1):
                if j % 2 == 0:
                    smaller_wale_edge_nodes = self.child_knitgraph.course_to_loop_ids[course_id][0]
                elif j % 2 == 1:
                    smaller_wale_edge_nodes = self.child_knitgraph.course_to_loop_ids[course_id][-1]
                edge_nodes_smaller_wale_side_child[i-1].append(smaller_wale_edge_nodes)
                j += 1
        j = 0
        for i in range(1, num_of_nodes_right_side):
            edge_nodes_bigger_wale_side_child[i-1] = [] # i-1 represents how the edge is indexed. Specifically, first edge would be indexed as 0 and so on so forth.
            curr_right_keynode = self.right_keynodes_child_fabric[i]
            curr_course_id = curr_right_keynode[0]
            last_right_keynode = self.right_keynodes_child_fabric[i-1]
            last_course_id = last_right_keynode[0]
            for course_id in range(last_course_id, curr_course_id+1):
                if j % 2 == 0:
                    bigger_wale_edge_nodes = self.child_knitgraph.course_to_loop_ids[course_id][-1]
                elif j % 2 == 1:
                    bigger_wale_edge_nodes = self.child_knitgraph.course_to_loop_ids[course_id][0]
                edge_nodes_bigger_wale_side_child[i-1].append(bigger_wale_edge_nodes)
                j += 1
        print(f'edge nodes (i.e. split nodes) of each edges on smaller wale side on child knitgraph is {edge_nodes_smaller_wale_side_child}, edge nodes (i.e. split nodes) of each edges on bigger wale side on child knitgraph is {edge_nodes_bigger_wale_side_child}')
        return edge_nodes_smaller_wale_side_child, edge_nodes_bigger_wale_side_child
                 
    def get_mirror_nodes_on_each_edge_on_parent_fabric(self, edge_nodes_smaller_wale_side_child, edge_nodes_bigger_wale_side_child):
        """
        this is used to get root nodes and mirror nodes of branch structure (characterize split operation) 
        """
        mirror_nodes_smaller_wale_side_parent: Dict[int: List[int]] = {}
        mirror_nodes_bigger_wale_side_parent: Dict[int: List[int]] = {}
        search_max_width = self.wale_dist
        for edge_index in edge_nodes_bigger_wale_side_child.keys():
            mirror_nodes_bigger_wale_side_parent[edge_index] = []
            edge_nodes = edge_nodes_bigger_wale_side_child[edge_index]
            for edge_node in edge_nodes:
                course_id = self.child_knitgraph.node_to_course_and_wale[edge_node][0]
                wale_id = self.child_knitgraph.node_to_course_and_wale[edge_node][1]
                # for efficiency, we only need to perform below once.
                if edge_node == edge_nodes[0]:
                    for wale_id_offset in range(search_max_width):
                        target_wale_id = wale_id + wale_id_offset
                        if (course_id, target_wale_id) in self.parent_knitgraph_course_and_wale_to_node:
                            if wale_id_offset == 0:
                                raise ErrorException(f'wale_id of child fabric can not be the same as parent fabric, otherwise child fabric will not be able to achieve texturized pattern')
                            self.wale_id_offset = wale_id_offset
                            break
                if (course_id, wale_id+wale_id_offset) not in self.parent_knitgraph_course_and_wale_to_node:
                    raise ErrorException(f'cannot find mirror node at {(course_id, wale_id+wale_id_offset)}')
                mirror_nodes_bigger_wale_side_parent[edge_index].append(self.parent_knitgraph_course_and_wale_to_node[(course_id, wale_id+wale_id_offset)])
        for edge_index in edge_nodes_smaller_wale_side_child.keys():
            mirror_nodes_smaller_wale_side_parent[edge_index] = []
            edge_nodes = edge_nodes_smaller_wale_side_child[edge_index]
            for edge_node in edge_nodes:
                course_id = self.child_knitgraph.node_to_course_and_wale[edge_node][0]
                wale_id = self.child_knitgraph.node_to_course_and_wale[edge_node][1]
                if (course_id, wale_id+wale_id_offset) not in self.parent_knitgraph_course_and_wale_to_node:
                    raise ErrorException(f'cannot find mirror node at {(course_id, wale_id+wale_id_offset)}')
                mirror_nodes_smaller_wale_side_parent[edge_index].append(self.parent_knitgraph_course_and_wale_to_node[(course_id, wale_id+wale_id_offset)])
        print(f'mirror nodes on parent knitgraph that correspond to edge nodes of each edge on smaller wale side on child knitgraph is {mirror_nodes_smaller_wale_side_parent}, \
            mirror nodes on parent knitgraph that correspond to edge nodes of each edge on bigger wale side on child knitgraph is {mirror_nodes_bigger_wale_side_parent}')
        return mirror_nodes_smaller_wale_side_parent, mirror_nodes_bigger_wale_side_parent

    def find_parent_coors(self, child_coor: Tuple[int, int], knitgraph_connectivity: List[Tuple]):
        parent_coors = []
        for connectivity in knitgraph_connectivity:
            if child_coor == connectivity[1]:
                parent_coors.append(connectivity[0])
        return parent_coors

    def get_root_nodes_on_each_edge_on_parent_fabric(self, mirror_nodes_smaller_wale_side_parent, mirror_nodes_bigger_wale_side_parent, edge_nodes_smaller_wale_side_child, edge_nodes_bigger_wale_side_child):
        """
        this is used to get root nodes of branch structure (characterize split operation).
        """
        #the dict structure would be like {edge_index: {(mirror_node1, split node1):[all root nodes], (mirror_node2, split node2):[all root nodes]}}
        root_nodes_smaller_wale_side_parent: Dict[int: Dict[Tuple[int, int]: List[int]]] = {} 
        root_nodes_bigger_wale_side_parent: Dict[int: Dict[Tuple[int, int]: List[int]]] = {}
        for edge_index in mirror_nodes_bigger_wale_side_parent.keys():
            root_nodes_bigger_wale_side_parent[edge_index] = {}
            mirror_nodes = mirror_nodes_bigger_wale_side_parent[edge_index]
            split_nodes = edge_nodes_bigger_wale_side_child[edge_index]
            for mirror_node, split_node in zip(mirror_nodes, split_nodes):
                parent_nodes = []
                mirror_node_coor = self.parent_knitgraph.node_to_course_and_wale[mirror_node]
                parent_coors = self.find_parent_coors(child_coor = mirror_node_coor, knitgraph_connectivity = self.parent_knitgraph_coors_connectivity)
                if len(parent_coors) <= 0:
                    raise ErrorException(f'this mirror node {mirror_node} can not form a branch structure because it has no parent')
                for parent_coor in parent_coors:
                    parent_nodes.append(self.parent_knitgraph_course_and_wale_to_node[parent_coor])
                root_nodes_bigger_wale_side_parent[edge_index][(mirror_node, split_node)] = parent_nodes
        for edge_index in mirror_nodes_smaller_wale_side_parent.keys():
            root_nodes_smaller_wale_side_parent[edge_index] = {}
            mirror_nodes = mirror_nodes_smaller_wale_side_parent[edge_index]
            split_nodes = edge_nodes_smaller_wale_side_child[edge_index]
            for mirror_node, split_node in zip(mirror_nodes, split_nodes):
                parent_nodes = []
                mirror_node_coor = self.parent_knitgraph.node_to_course_and_wale[mirror_node]
                parent_coors = self.find_parent_coors(child_coor = mirror_node_coor, knitgraph_connectivity = self.parent_knitgraph_coors_connectivity)
                if len(parent_coors) <= 0:
                    raise ErrorException(f'this mirror node {mirror_node} can not form a branch structure because it has no parent')
                for parent_coor in parent_coors:
                    parent_nodes.append(self.parent_knitgraph_course_and_wale_to_node[parent_coor])
                root_nodes_smaller_wale_side_parent[edge_index][(mirror_node, split_node)] = parent_nodes
        print(f'root nodes on parent knitgraph that correspond to edge nodes of each edge on smaller wale side on child knitgraph is {root_nodes_smaller_wale_side_parent}, root nodes on parent knitgraph that correspond to edge nodes of each edge on bigger wale side on child knitgraph is {root_nodes_bigger_wale_side_parent}')
        return root_nodes_smaller_wale_side_parent, root_nodes_bigger_wale_side_parent
    
    def connect_stitches_on_knitgraph(self):
        first_course_to_split = [*self.child_knitgraph.course_to_loop_ids.keys()][0]
        last_course_to_split = [*self.child_knitgraph.course_to_loop_ids.keys()][-1]
        bed = 'b' if self.is_front_patch == True else 'f'
        for (parent_coor, child_coor, attr_dict) in self.parent_knitgraph_coors_connectivity:
            parent_node = self.parent_knitgraph_course_and_wale_to_node[parent_coor]
            child_node = self.parent_knitgraph_course_and_wale_to_node[child_coor]
            if (first_course_to_split <= self.parent_knitgraph.node_to_course_and_wale[child_node][0] <= last_course_to_split) and \
                (self.handle_graph.node_on_front_or_back[parent_node] == self.handle_graph.node_on_front_or_back[child_node] == bed):
                pull_direction = Pull_Direction.BtF
            else:
                pull_direction = attr_dict['pull_direction']
            depth = attr_dict['depth']
            parent_offset = attr_dict['parent_offset']
            self.handle_graph.connect_loops(parent_node, child_node, pull_direction = pull_direction, depth = depth, parent_offset = parent_offset)
        for (parent_coor, child_coor, attr_dict) in self.child_knitgraph_coors_connectivity:
            parent_node = self.child_knitgraph_course_and_wale_to_node[parent_coor]
            child_node = self.child_knitgraph_course_and_wale_to_node[child_coor]
            pull_direction = attr_dict['pull_direction']
            depth = attr_dict['depth']
            parent_offset = attr_dict['parent_offset']
            # pull_direction = pull_direction.opposite() since when we view the knitgraph created, we view from the back side of the child fabric.
            self.handle_graph.connect_loops(parent_node, child_node, pull_direction = Pull_Direction.BtF, depth = depth, parent_offset = parent_offset)
    
    def reconnect_branches_on_the_side(self, root_nodes_smaller_wale_side_parent, root_nodes_bigger_wale_side_parent):
        """"
        this is used to update the connecting edges for all branch structures on the sides.
        """
        # first iterate over edge_connection_left_side to see which edge to connect
        num_of_left_edges = len(root_nodes_smaller_wale_side_parent)
        for edge_index in range(num_of_left_edges):
            for mirror_node, split_node in [*root_nodes_smaller_wale_side_parent[edge_index].keys()]:
                root_nodes = root_nodes_smaller_wale_side_parent[edge_index][(mirror_node, split_node)]
                for root_node in root_nodes:
                    # self.handle_graph.connect_loops(root_node, mirror_node, pull_direction = Pull_Direction.BtF)
                    self.handle_graph.connect_loops(root_node, split_node, pull_direction = Pull_Direction.BtF, parent_offset = self.wale_id_offset)
        # then iterate over edge_connection_right_side to see which edge to connect
        num_of_right_edges = len(root_nodes_bigger_wale_side_parent)
        for edge_index in range(num_of_right_edges):
            for mirror_node, split_node in [*root_nodes_bigger_wale_side_parent[edge_index].keys()]:
                root_nodes = root_nodes_bigger_wale_side_parent[edge_index][(mirror_node, split_node)]
                for root_node in root_nodes:
                    # self.handle_graph.connect_loops(root_node, mirror_node, pull_direction = Pull_Direction.BtF)
                    self.handle_graph.connect_loops(root_node, split_node, pull_direction = Pull_Direction.BtF, parent_offset = self.wale_id_offset)

    def build_handle_graph(self) -> Knit_Graph:   
        self.generate_polygon_from_keynodes()
        self.read_connectivity_from_knitgraph()
        self.get_course_id_to_wale_ids()
        #first grow rows just above splitting_course_id on parent fabric
        self.build_rows_on_parent_graph_just_above_splitting_course_id()
        #clear old self.child_knitgraph.node_to_course_and_wale
        self.child_knitgraph.node_to_course_and_wale = {}
        self.grow_one_row(course_id = [*self.child_knitgraph.course_to_loop_ids.keys()][0], on_parent_graph = False)
        #grow the whole graph by adding one row to parent fabric, then adding one row to child fabric, until reaching the end of child fabric
        print('self.child_knitgraph.course_to_loop_ids.keys()', self.child_knitgraph.course_to_loop_ids.keys())
        for course_id in [*self.child_knitgraph.course_to_loop_ids.keys()][1:]:
            self.grow_one_row(course_id, on_parent_graph = True)
            self.grow_one_row(course_id, on_parent_graph = False)
        last_course_id_child_fabric = [*self.child_knitgraph.course_to_loop_ids.keys()][-1]
        last_course_id_parent_fabric = [*self.parent_knitgraph.course_to_loop_ids.keys()][-1]
        #continue to grow row on parent fabric one by one
        for course_id in range(last_course_id_child_fabric + 1, last_course_id_parent_fabric + 1):
            self.grow_one_row(course_id, on_parent_graph = True)
        #get updated course_and_wale_to_node on child knitgraph and parent knitgraph
        # self.parent_knitgraph_course_and_wale_to_node = {tuple(v): k for k, v in self.parent_knitgraph._node_to_course_and_wale.items()}
        # self.child_knitgraph_course_and_wale_to_node = {tuple(v): k for k, v in self.child_knitgraph.node_to_course_and_wale.items()}
        #merge node_to_course_and_wale on parent_knitgraph and child_knitgraph
        self.handle_graph.node_to_course_and_wale = self.parent_knitgraph.node_to_course_and_wale|self.child_knitgraph.node_to_course_and_wale
        #see if connect edges
        edge_nodes_smaller_wale_side_child, edge_nodes_bigger_wale_side_child = self.get_split_nodes_on_each_edge_on_child_fabric()
        mirror_nodes_smaller_wale_side_parent, mirror_nodes_bigger_wale_side_parent = self.get_mirror_nodes_on_each_edge_on_parent_fabric(edge_nodes_smaller_wale_side_child, edge_nodes_bigger_wale_side_child)
        root_nodes_smaller_wale_side_parent, root_nodes_bigger_wale_side_parent = self.get_root_nodes_on_each_edge_on_parent_fabric(mirror_nodes_smaller_wale_side_parent, mirror_nodes_bigger_wale_side_parent, edge_nodes_smaller_wale_side_child, edge_nodes_bigger_wale_side_child)
        self.connect_stitches_on_knitgraph()
        self.reconnect_branches_on_the_side(root_nodes_smaller_wale_side_parent, root_nodes_bigger_wale_side_parent)
        return self.handle_graph
  