from typing import Optional, List, Dict, Tuple
from knit_graphs.Yarn import Yarn
from knit_graphs.Knit_Graph import Knit_Graph
from debugging_tools.final_knit_graph_viz import knitGraph_visualizer
from debugging_tools.simple_knitgraph_generator import *

class Polygon_Generator:
    def __init__(self, left_keynodes_child_fabric, right_keynodes_child_fabric, gauge: float = 1):
        """
        :param left_keypoints: List of (course_id, wale_id) of the spiky points on the left side of the pattern.
        :param right_keypoints: List of (course_id, wale_id) of the spiky points on the right side of the pattern.
        (Note that the keypoints should be enter in order of from bottom to top for each side, and we assume the origin
        of the pattern is (0, 0). )
        """
        self.is_polygon = True
        self.gauge = gauge
        self.wale_dist = int(1/self.gauge)
        self.left_keynodes_child_fabric: List[Tuple[int, int]] = left_keynodes_child_fabric
        self.right_keynodes_child_fabric: List[Tuple[int, int]] = right_keynodes_child_fabric
        self._knit_graph: Knit_Graph = Knit_Graph()
        self.yarn: Yarn
        # self._loop_id_to_course: Dict[int, float]
        self.course_to_loop_ids: Dict[float, List[int]]
        self.node_to_course_and_wale: Dict[int, Tuple[int, int]]
        self.node_on_front_or_back: Dict[int, str] = {}
        self.course_and_wale_to_node: Dict[Tuple[int, int], int]
        self.starting_nodes_coor: List[Tuple[int, int]]
        self.ending_nodes_coor: List[Tuple[int, int]]
        

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
        assert first_keynode_left[0] == first_keynode_right[0], f'first keynode on the left and right do not share the same course_id'
        assert last_keynode_left[0] == last_keynode_right[0], f'last keynode on the left and right do not share the same course_id'
        #
        num_of_nodes_left_side = len(self.left_keynodes_child_fabric)
        num_of_nodes_right_side = len(self.right_keynodes_child_fabric)
        for i in range(1, num_of_nodes_left_side):
            curr_left_keynode = self.left_keynodes_child_fabric[i]
            last_left_keynode = self.left_keynodes_child_fabric[i-1] 
            width_change_left = curr_left_keynode[1] - last_left_keynode[1]
            increase_height_left = curr_left_keynode[0] - last_left_keynode[0]
            #check if any other keynodes might be missed in between 
            if width_change_left % increase_height_left != 0:
                print(f'some keynodes might exist bewtween given keynodes {last_left_keynode} and {curr_left_keynode} on the left side if these two keynodes are entered correctly')
                exit()
        for i in range(1, num_of_nodes_right_side):    
            curr_right_keynode = self.right_keynodes_child_fabric[i]
            last_right_keynode = self.right_keynodes_child_fabric[i-1]
            width_change_right = curr_right_keynode[1] - last_right_keynode[1]
            increase_height_right = curr_right_keynode[0] - last_right_keynode[0]
            if width_change_right % increase_height_right != 0:
                print(f'some keynodes might exist bewtween given keynodes {last_right_keynode} and {curr_right_keynode} on the right side if these two keynodes are entered correctly')
                exit()
                
    def generate_polygon_from_keynodes(self, carrier_id: int, yarn_id: str):
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
        print(f'starting_nodes_coor in polygon_knitgraph is {starting_nodes_coor}, ending_nodes_coor in polygon_knitgraph is {ending_nodes_coor}')
        #assign to self attribute in case they are needed in hole_generator()
        self.starting_nodes_coor = starting_nodes_coor
        self.ending_nodes_coor = ending_nodes_coor
        #derive node_to_course_and_wale from above starting_nodes_coor and ending_nodes_coor
        node = 0
        node_to_course_and_wale = {}
        for i in range(len(starting_nodes_coor)):
            staring_node_wale_id = starting_nodes_coor[i][1]
            ending_node_wale_id = ending_nodes_coor[i][1]
            course_id = starting_nodes_coor[i][0]
            if course_id % 2 == 0:
                for i in range(staring_node_wale_id, ending_node_wale_id + 1):
                    wale_id = i*self.wale_dist
                    node_to_course_and_wale[node] = (course_id, wale_id) 
                    node += 1
            elif course_id % 2 == 1:
                for i in range(ending_node_wale_id, staring_node_wale_id - 1, -1):
                    wale_id = i*self.wale_dist
                    node_to_course_and_wale[node] = (course_id, wale_id)
                    node += 1
        self.node_to_course_and_wale = node_to_course_and_wale
        print(f'node_to_course_and_wale in polygon_knitgraph is {node_to_course_and_wale}')
        #connect nodes on yarn
        self.yarn = Yarn(yarn_id, self._knit_graph, carrier_id=carrier_id)
        self._knit_graph.add_yarn(self.yarn)
        for node in node_to_course_and_wale.keys():
            loop_id, loop = self.yarn.add_loop_to_end()
            self._knit_graph.add_loop(loop)
            self.node_on_front_or_back[loop_id] = 'f'
        #get course_to_loop_ids
        course_to_loop_ids = {}
        course_id_start = starting_nodes_coor_on_first_course[0]
        course_id_end = starting_nodes_coor[-1][0]
        for course_id in range(course_id_start, course_id_end + 1):
            course_to_loop_ids[course_id] = []
        for node in self._knit_graph.graph.nodes:
            course_id = node_to_course_and_wale[node][0]
            course_to_loop_ids[course_id].append(node)
        self.course_to_loop_ids = course_to_loop_ids
        print(f'course_to_loop_ids in polygon_knitgraph is {course_to_loop_ids}')
        #reverse node_to_course_and_wale to get course_and_wale_to_node
        course_and_wale_to_node = {}
        course_and_wale_to_node = {tuple(v): k for k, v in node_to_course_and_wale.items()}
        self.course_and_wale_to_node = course_and_wale_to_node
        print(f'course_and_wale_to_node in polygon_knitgraph is {self.course_and_wale_to_node}')
        #connect node stitches
        course_ids_before_final_course = [*course_to_loop_ids.keys()][:-1]
        for course_id in course_ids_before_final_course:
            for node in course_to_loop_ids[course_id]:
                wale_id = node_to_course_and_wale[node][1]
                #find upper neighbor node
                if (course_id + 1, wale_id) in course_and_wale_to_node.keys():
                    child_loop = course_and_wale_to_node[(course_id + 1, wale_id)]
                    self._knit_graph.connect_loops(node, child_loop)
        return self._knit_graph
