from typing import Optional, List, Dict, Tuple, Union
import networkx as nx
from knit_graphs.Yarn import Yarn
from knit_graphs.Knit_Graph import Knit_Graph, Pull_Direction
from debugging_tools.final_knit_graph_viz import knitGraph_visualizer
from debugging_tools.polygon_generator import Polygon_Generator
from debugging_tools.simple_knitgraph_generator import Simple_Knitgraph_Generator
from debugging_tools.exceptions import ErrorException
import warnings

class Hole_Generator_on_Sheet:
    """
    This is Hole_Generator works for sheet, we have a separate Hole_Generator used for tube.
    Compared to "Hole_Generator" version, this version can work on polygon shaped fabric rather then only a rectangle.
    Biggest assumption: the function currently only apply for hole that are rectagular and only one hole. More yarns are needed if 
    the above condition is not satisfied.
    """
    def __init__(self, yarns_and_holes_to_add: Dict[int, List[int]], knitgraph, simple_knitgraph_generator: Optional[Simple_Knitgraph_Generator] = None):
        # if simple_knitgraph_generator != None:
        #     self.is_polygon = False
        #     # as this is the hole generator for sheet
        #     # print(f'simple_knitgraph_generator.pattern is {simple_knitgraph_generator.pattern}')
        #     assert ('tube' in simple_knitgraph_generator.pattern or 'hat' in simple_knitgraph_generator.pattern) == False
        #     self._knit_graph: Knit_Graph = simple_knitgraph_generator.generate_knitgraph()
        #     self._knit_graph.node_to_course_and_wale =  simple_knitgraph_generator.node_to_course_and_wale
        #     self._knit_graph.course_and_wale_to_node = simple_knitgraph_generator.course_and_wale_to_node
        #     self._knit_graph.node_on_front_or_back = simple_knitgraph_generator.node_on_front_or_back
        #     self._knit_graph.loop_id_to_course: Dict[int, float]
        #     self._knit_graph.loop_id_to_course, self._knit_graph.course_to_loop_ids = self._knit_graph.get_courses()
        #     self._knit_graph.gauge = simple_knitgraph_generator.gauge
        # else:
        self._knit_graph: Knit_Graph = knitgraph
        self._knit_graph.node_to_course_and_wale = knitgraph.node_to_course_and_wale
        self._knit_graph.course_and_wale_to_node: Dict[Tuple[int, int], int]
        print(f'in hole sheet 0, knitgraph.node_on_front_or_back is {knitgraph.node_on_front_or_back}')
        self._knit_graph.node_on_front_or_back = knitgraph.node_on_front_or_back
        print(f'in hole sheet 1, self._knit_graph.node_on_front_or_back is {self._knit_graph.node_on_front_or_back}')
        self._knit_graph.loop_id_to_course: Dict[int, float] = self._knit_graph.loop_ids_to_course
        self._knit_graph.course_to_loop_ids: Dict[int, List[int]] = self._knit_graph.course_to_loop_ids
        self._knit_graph.gauge = knitgraph.gauge
        if self._knit_graph.object_type != 'sheet':
            raise ErrorException(f'wrong object type of parent knitgraph')
        self._knit_graph.object_type = 'sheet'
        assert self._knit_graph.course_to_loop_ids is not None
        assert self._knit_graph.node_to_course_and_wale is not None
        assert self._knit_graph.node_on_front_or_back is not None
        # assert self._knit_graph.course_and_wale_to_node is not None
        self.float_length = int(1/self._knit_graph.gauge) - 1
        self.wale_dist = int(1/self._knit_graph.gauge)
        self.graph_nodes: set[int] = set(self._knit_graph.graph.nodes)
        if len(self._knit_graph.yarns) != 1:
            raise ErrorException(f"This only supports modifying graphs that has only one yarn as input")
        #since given knit graph has only one yarn before being modified
        self._old_yarn: Yarn = [*self._knit_graph.yarns.values()][0]
        # assert the type of keys is integer instead of str, otherwise will throw an error when it comes to create new yarn object in bring the new yarns() below
        if set(map(type, yarns_and_holes_to_add.keys())) != {int}:
            raise ErrorException(f'yarn carrier id should be of integer type')
        # assert old yarn carrier is not in new carriers, otherwise cause confusion
        self.yarns_and_holes_to_add: Dict[int, List[int]] = yarns_and_holes_to_add
        self._new_carriers: List[int] = [*yarns_and_holes_to_add.keys()]
        for carrier_id in self._new_carriers:
            if carrier_id == self._old_yarn.carrier.carrier_ids:
                raise ErrorException(f'one of the carrier ids: {carrier_id} in provided yarn carriers for adding hole is the same as old yarn carrier id :{self._old_yarn.carrier.carrier_ids}')
        self.new_yarn_ids: List[str] = [str(new_yarn_id) for new_yarn_id in self._new_carriers]
        self._new_yarns: Dict[int, Yarn] = {}

        self.holes_size: Dict[int, Dict[str, int]] = {}
        self.holes_to_old_and_new_yarns: Dict[int, Dict[str, List[int]]] = {}  
        self.course_id_to_wale_ids: Dict[int, List[int]] 
        self.course_id_to_start_wale_id: Optional[Dict[int, int]]
        self.course_id_to_end_wale_id: Optional[Dict[int, int]]
        #pattern_height is the total number of courses 
        # self._pattern_height: int = len(self._knit_graph.course_to_loop_ids) #update to below
        print(f'self._knit_graph.course_to_loop_ids.keys() is {self._knit_graph.course_to_loop_ids.keys()}')
        self._pattern_height: int = max([*self._knit_graph.course_to_loop_ids.keys()]) + 1
        print(f'self._pattern_height is {self._pattern_height}')
        self.min_course_id = min([*self._knit_graph.course_to_loop_ids.keys()])

        self._hole_course_to_wale_ids: Dict[int, Dict[int, List[int]]] = {}
        self.course_id_to_smallest_hole_wale: Dict[int, int] = {}
        self.hole_index_to_course_id_to_new_yarn_wales: Dict[int, Dict[int, List[int]]] = {}
        self.course_to_hole_index: Dict[int, List[int]] = {}
        # note that below one is "real new yarn wales", different than the above "self.hole_index_to_course_id_to_new_yarn_wales"
        self.hole_index_to_course_id_to_real_new_yarn_wales: Dict[int, Dict[int, List[int]]] = {}
        self.sorted_hole_index: List = []

    def get_hole_size(self):
        """
        hole_start_course = self._pattern_height - 1
        :param hole_start_course: the minimal wale_id of any node in nodes_to_delete
        :param hole_end_course: the maximal course_id of any node in nodes_to_delete
        :param hole_start_wale: the minimal wale_id of any node in nodes_to_delete
        :param hole_end_wale: the maximal wale_id of any node in nodes_to_delete
        Assertion: number of unique wale id can not exceed 6 to make it a feasible to knit on knittimg machine taking into account racking constraint.
        """
        # wale_involved = set()
        # index starts from 0
        hole_index = 0 
        for hole in self.yarns_and_holes_to_add.values():
            self._hole_start_course: int = self._pattern_height - 1
            self._hole_end_course: int = 0
            self._hole_start_wale: int = 10000
            # since the smallest wale id can be less than 0, thus we update the initialization of hole_end_wale from 0 to -10000
            self._hole_end_wale: int = -10000
            self._hole_height: int = None
            self._hole_width: int = None
            # 
            self.holes_size[hole_index] = {}
            self.holes_size[hole_index]['hole_nodes'] = hole
            for node in hole:
                wale_id = self._knit_graph.node_to_course_and_wale[node][1]
                # wale_involved.add(wale_id)
                course_id = self._knit_graph.node_to_course_and_wale[node][0]
                if course_id > self._hole_end_course:
                    self._hole_end_course = course_id
                if course_id < self._hole_start_course:
                    self._hole_start_course = course_id
                if wale_id < self._hole_start_wale:
                    self._hole_start_wale = wale_id
                if wale_id > self._hole_end_wale:
                    self._hole_end_wale = wale_id
            #number of unique wale id can not exceed 6 to make it a feasible to knit on knittimg machine taking into account racking constraint
            # deprecated because now turn to bind-off on unstable hole nodes
            # assert len(wale_involved) <= 5, f'hole width is too large to achieve the racking bound by 2 on the machine'
            # cannot relax below constraints considering in our pipeline even though we have waste height for each knit object, otherwise yarn-over node would get wrong
            # target needle position with our pipeline.
            if self._hole_start_course <= 1:
                raise ErrorException(f'bind-off would fail if hole_start_course <= 1')
            if self._hole_end_course >= self._pattern_height - 1:
                raise ErrorException(f'hole height is too large that it is exceeding the knit graph border')
            self._hole_height = self._hole_end_course - self._hole_start_course + 1
            self._hole_width = (self._hole_end_wale - self._hole_start_wale) + self.wale_dist
            self.holes_size[hole_index]['hole_start_course'] = self._hole_start_course
            self.holes_size[hole_index]['hole_end_course'] = self._hole_end_course
            self.holes_size[hole_index]['hole_start_wale'] = self._hole_start_wale
            self.holes_size[hole_index]['hole_end_wale'] = self._hole_end_wale
            self.holes_size[hole_index]['hole_height'] = self._hole_height
            self.holes_size[hole_index]['hole_width'] = self._hole_width
            hole_index += 1
            # print(f'hole_start_course is {self._hole_start_course}, hole_end_course is {self._hole_end_course}, hole_start_wale is {self._hole_start_wale}, hole_end_wale is {self._hole_end_wale}')
        # organize the self.holes_size() by hole_start_course -- hole with smaller hole_start_course will be processed first in 
        # get_new_yarn_loop_ids_for_holes(). If there are more than one hole with the same hole_start_course, then see their hole_end_course,
        # those with bigger hole_end_course will be placed later.
        print(f'self.holes_size.items() is {self.holes_size.items()}, \
              [*self.holes_size.items()] is {[*self.holes_size.items()]}')
        dict_list = [*self.holes_size.items()]
        
            
        a = sorted(dict_list, key=lambda x:(x[1]['hole_start_course'], x[1]['hole_end_course']))
        # get the sorted index
        for dict in a:
            index= dict[0]
            self.sorted_hole_index.append(index) 
        print(f'a is {a}, sorted_hole_index is {self.sorted_hole_index}')
        print(f'holes_size is {self.holes_size}')
    
    # use self._hole_course_to_wale_ids inside the get_new_yarn_loop_ids()
    def get_hole_course_to_wale_ids(self):
        hole_index = 0
        for hole in self.yarns_and_holes_to_add.values():
            self._hole_course_to_wale_ids[hole_index] = {}
            for node in hole:
                course_id = self._knit_graph.node_to_course_and_wale[node][0]
                wale_id = self._knit_graph.node_to_course_and_wale[node][1]
                # print(f'node is {node}, course_id is {course_id}, wale_id is {wale_id}')
                if course_id not in self._hole_course_to_wale_ids[hole_index]:
                    self._hole_course_to_wale_ids[hole_index][course_id] = [wale_id]
                else:
                    self._hole_course_to_wale_ids[hole_index][course_id].append(wale_id)
            hole_index += 1
        # print(f'hole_course_to_wale_ids is {self._hole_course_to_wale_ids}')

    def hole_location_warnings(self):
        """
        check if any ready-to-be-hole node might break any special stitch or suspicious for lacking some property,
        signaling something might go wrong with the given knit graph.
        """
        for hole in self.yarns_and_holes_to_add.values():
            for node in hole: 
                #first, each node should have exactly one parent. 
                #If more than one, it is part of a decrease; If less than one, it itself is an increase.
                parent_ids = [*self._knit_graph.graph.predecessors(node)]
                child_ids = [*self._knit_graph.graph.successors(node)]
                if len(parent_ids) != 1:
                    # warnings.warn("xxx")
                    print(f'Warning: node {node} might break a special stitch for having {len(parent_ids)} parents')
                #Likewise, each node should have exactly one child (it can only be one or zero child).
                #If no child, it might be a node on top course/top border, which we do not consider. 
                #Or simply it can be an error node in the knit graph signaling something wrong with the program.
                if len(child_ids) != 1:
                    print(f'Error: node {node} is suspicious or is a node on border for for having {len(child_ids)} child')
                    exit()
                #Second, on knit graph, any edge related to the node must have a parent offset that is 0.
                #If not, it is part of decrease or cable.
                if len(parent_ids) == 1:
                    for parent_id in parent_ids:
                        parent_offset = self._knit_graph.graph[parent_id][node]["parent_offset"]
                        if parent_offset != 0:
                            print(f'Warning: node {node} might break a special stitch for having parent offset of {parent_offset}')
                #the above rule applies to child_offset too.
                if len(child_ids) != 0:
                    child_id = child_ids[0] # no "for child_id in child_ids[0]:" here because a node can have <= 1 child on the knit graph
                    child_offset = self._knit_graph.graph[node][child_id]["parent_offset"]
                    if child_offset != 0:
                        print(f'Warning: node {node} might break a special stitch for having child offset of {child_offset}')
                #Third, on yarn graph, the number of yarn edges related to the node must be 2
                #If less than one, it is either the start node or end node of the yarn, or a huge error when adding loop with the yarn :)
                yarn_parent_ids = [*self._old_yarn.yarn_graph.predecessors(node)]
                yarn_child_ids = [*self._old_yarn.yarn_graph.successors(node)]
                if len(yarn_parent_ids) != 1 or len(yarn_child_ids) != 1:
                    print(f'Warning: node {node} is suspicious for having no parent node or child node on yarn')
                #Fourth, on yarn graph, parent node and child node of the node should be on the same course
                #If not, it might be part of short row, or a node on the border. Currently, we do not consider add hole on border.
                if len(yarn_parent_ids) != 0 and len(yarn_child_ids) != 0:
                    parent_id = yarn_parent_ids[0]
                    child_id = yarn_child_ids[0]
                    if self._knit_graph.node_to_course_and_wale[parent_id][0] != self._knit_graph.node_to_course_and_wale[child_id][0]:
                        print(f'Error: node {node} might break a special stitch or a node on border for having parent node and child node on yarn graph that are not on the same course')
                        exit()

    def hole_location_errors(self):
        for hole in self.yarns_and_holes_to_add.values():
            for node in hole:
                #First, if a node has no child and is not a node on top course/top border 
                #it would be an error/unstable node in the knit graph signaling something wrong with the given knitgraph.
                parent_ids = [*self._knit_graph.graph.predecessors(node)]
                child_ids = [*self._knit_graph.graph.successors(node)]
                course_id = self._knit_graph.node_to_course_and_wale[node][0]
                top_course_id = self._pattern_height - 1
                if len(child_ids) < 1 and course_id != top_course_id:
                    print(f'Error: node {node} is suspicious for for having {len(child_ids)} child')
                    exit()
            #Second, on yarn graph, the number of yarn edges related to the node must be 2
            #If less than one, and is not the start node or end node of the yarn, it would be a huge error when adding loop with the yarn
            for node in self._old_yarn.yarn_graph.nodes:
                yarn_parent_ids = [*self._old_yarn.yarn_graph.predecessors(node)]
                yarn_child_ids = [*self._old_yarn.yarn_graph.successors(node)]
                # if node not in [0, len(self._old_yarn.yarn_graph.nodes)-1]: #update to below
                if  min(self._knit_graph.course_to_loop_ids[max([*self._knit_graph.course_to_loop_ids.keys()])]) > node > max(self._knit_graph.course_to_loop_ids[min([*self._knit_graph.course_to_loop_ids.keys()])]):
                    if len(yarn_parent_ids) != 1 or len(yarn_child_ids) != 1:
                        print(f'Error: node {node} is suspicious for having no parent node or child node on yarn')
                        exit()
  
    def remove_hole_nodes_from_graph(self):
        """
        remove the nodes for hole from both knit graph and yarn
        """
        print(f'in hole sheet 2, self._knit_graph.node_on_front_or_back in hole_on_sheet is {self._knit_graph.node_on_front_or_back}')
        for hole in self.yarns_and_holes_to_add.values():
            self._knit_graph.graph.remove_nodes_from(hole)
            self._old_yarn.yarn_graph.remove_nodes_from(hole)
            for hole_node in hole:
                del self._knit_graph.node_to_course_and_wale[hole_node]
                del self._knit_graph.node_on_front_or_back[hole_node] 
        self._knit_graph.course_and_wale_to_node = {v: k for k, v in self._knit_graph.node_to_course_and_wale.items()}
        # print(f'updated self._knit_graph.course_and_wale_to_node with hole nodes deleted is {self._knit_graph.course_and_wale_to_node}')

    def get_start_and_end_wale_id_per_course(self):
        course_id_to_start_wale_id = {}
        course_id_to_end_wale_id = {}
        for course_id in self._knit_graph.course_to_loop_ids.keys():
            if course_id % 2 == 0:
                start_keynode = self._knit_graph.course_to_loop_ids[course_id][0]
                start_wale_id = self._knit_graph.node_to_course_and_wale[start_keynode][1]
                end_keynode = self._knit_graph.course_to_loop_ids[course_id][-1]
                end_wale_id = self._knit_graph.node_to_course_and_wale[end_keynode][1]
                course_id_to_start_wale_id[course_id] = start_wale_id
                course_id_to_end_wale_id[course_id] = end_wale_id
            elif course_id % 2 == 1:
                start_keynode = self._knit_graph.course_to_loop_ids[course_id][-1]
                start_wale_id = self._knit_graph.node_to_course_and_wale[start_keynode][1]
                end_keynode = self._knit_graph.course_to_loop_ids[course_id][0]
                end_wale_id = self._knit_graph.node_to_course_and_wale[end_keynode][1]
                course_id_to_start_wale_id[course_id] = start_wale_id
                course_id_to_end_wale_id[course_id] = end_wale_id                 
        # if the more generalizable solution is required in the future as the project develop, use self._knit_graph.course_to_loop_ids and self._loop_id_to_wale to solve.
        self.course_id_to_start_wale_id = course_id_to_start_wale_id
        self.course_id_to_end_wale_id = course_id_to_end_wale_id

    def get_new_yarn_loop_ids_for_holes(self):
        """
        ----Only applicable to sheet case----
        Provided the hole_start_course, no matter what the yarn starting direction is, i.e., from left to right or from right
        to left, the loop ids that should be re-assigned to a new yarn can be determined by if the hole_start_course is an 
        odd number or even number, though the use of wale id and course id.
        """
        # wale_dist = self.float_length+1
        #for hole_index in [*self.holes_size.keys()]:
        real_odd_flag = 1 if self.min_course_id%2==0 else 0
        real_even_flag = 0 if self.min_course_id%2==0 else 1
        for hole_index in self.sorted_hole_index:
            new_yarn_course_to_loop_ids: Dict[float, List[int]]= {}
            old_yarn_course_to_margin_loop_ids: Dict[float, List[int]]= {}
            new_yarn_course_to_margin_loop_ids: Dict[float, List[int]]= {}
            hole_info = self.holes_size[hole_index] 
            self.holes_to_old_and_new_yarns[hole_index] = {}
            if hole_info['hole_start_course'] % 2 == 0:
                #new yarn spread between the hole_end_wale and the last wale_id, old yarn is between the wale_id = 0 to the hole_start_wale 
                for course_id in range(hole_info['hole_start_course'], hole_info['hole_end_course'] + 1):
                    smallest_wale_id = min(self._hole_course_to_wale_ids[hole_index][course_id])
                    biggest_wale_id = max(self._hole_course_to_wale_ids[hole_index][course_id])
                    #-----we don't need margin loop ids for now---
                    if (course_id, smallest_wale_id - self.wale_dist) not in self._knit_graph.course_and_wale_to_node.keys():
                        print(f'no node is found on the hole margin near the old yarn side {(course_id, smallest_wale_id - self.wale_dist)}')
                    else:
                        old_yarn_course_to_margin_loop_ids[course_id] = self._knit_graph.course_and_wale_to_node[(course_id, smallest_wale_id - self.wale_dist)]
                    if (course_id, biggest_wale_id + self.wale_dist) not in self._knit_graph.course_and_wale_to_node.keys():
                        print(f'no node is found on the hole margin near the new yarn side {(course_id, biggest_wale_id + self.wale_dist)}')   
                    else:
                        new_yarn_course_to_margin_loop_ids[course_id] = self._knit_graph.course_and_wale_to_node[(course_id, biggest_wale_id + self.wale_dist)]
                    #-----we don't need margin loop ids for now---
                    new_yarn_course_to_loop_ids[course_id] = []
                    if course_id % 2 == 0:
                        for wale_id in range(biggest_wale_id + self.wale_dist, self.course_id_to_end_wale_id[course_id] + self.wale_dist):
                            if (course_id, wale_id) in self._knit_graph.course_and_wale_to_node.keys():
                                new_yarn_course_to_loop_ids[course_id].append(self._knit_graph.course_and_wale_to_node[(course_id, wale_id)])
                    elif course_id % 2 == 1:
                        for wale_id in range(biggest_wale_id + self.wale_dist, self.course_id_to_end_wale_id[course_id] + self.wale_dist):
                            if (course_id, wale_id) in self._knit_graph.course_and_wale_to_node.keys():
                                new_yarn_course_to_loop_ids[course_id].insert(0, self._knit_graph.course_and_wale_to_node[(course_id, wale_id)])
                if hole_info['hole_height'] % 2 == 0:
                    pass
                elif hole_info['hole_height'] % 2 == 1:
                    for course_id in range(hole_info['hole_end_course'] + 1, self._pattern_height):
                        new_yarn_course_to_loop_ids[course_id] = self._knit_graph.course_to_loop_ids[course_id]
            if hole_info['hole_start_course'] % 2 == 1:
                #Contrary to the above,
                #new yarn spread between the wale_id = 0 to the hole_start_wale, old yarn is between the hole_end_wale and the last wale_id
                for course_id in range(hole_info['hole_start_course'], hole_info['hole_end_course'] + 1):
                    smallest_wale_id = min(self._hole_course_to_wale_ids[hole_index][course_id])
                    biggest_wale_id = max(self._hole_course_to_wale_ids[hole_index][course_id])
                    #-----we don't need margin loop ids for now---
                    if (course_id, biggest_wale_id + (self.wale_dist)) not in self._knit_graph.course_and_wale_to_node.keys():
                        print(f'no node is found on the hole margin near the old yarn side {(course_id, biggest_wale_id + (self.wale_dist))}')
                    else:
                        old_yarn_course_to_margin_loop_ids[course_id] = self._knit_graph.course_and_wale_to_node[(course_id, biggest_wale_id + (self.wale_dist))]
                    if  (course_id, smallest_wale_id - (self.wale_dist)) not in self._knit_graph.course_and_wale_to_node.keys():
                        print(f'no node is found on the hole margin near the new yarn side {(course_id, smallest_wale_id - (self.wale_dist))}')
                    else:
                        new_yarn_course_to_margin_loop_ids[course_id] = self._knit_graph.course_and_wale_to_node[(course_id, smallest_wale_id - (self.wale_dist))]
                    #-----we don't need margin loop ids for now---
                    new_yarn_course_to_loop_ids[course_id] = []
                    if course_id % 2 == 0:
                        for wale_id in range(self.course_id_to_start_wale_id[course_id], smallest_wale_id):
                            if (course_id, wale_id) in self._knit_graph.course_and_wale_to_node.keys():
                                new_yarn_course_to_loop_ids[course_id].append(self._knit_graph.course_and_wale_to_node[(course_id, wale_id)])
                    elif course_id % 2 == 1:
                        for wale_id in range(self.course_id_to_start_wale_id[course_id], smallest_wale_id):
                            if (course_id, wale_id) in self._knit_graph.course_and_wale_to_node.keys():
                                new_yarn_course_to_loop_ids[course_id].insert(0, self._knit_graph.course_and_wale_to_node[(course_id, wale_id)])
                if hole_info['hole_height'] % 2 == 0:
                    pass
                elif hole_info['hole_height'] % 2 == 1:
                    for course_id in range(hole_info['hole_end_course'] + 1, self._pattern_height):
                        new_yarn_course_to_loop_ids[course_id] = self._knit_graph.course_to_loop_ids[course_id]
            # print('old_yarn_course_to_margin_loop_ids', old_yarn_course_to_margin_loop_ids)
            # print('new_yarn_course_to_margin_loop_ids', new_yarn_course_to_margin_loop_ids)
            # print('new_yarn_course_to_loop_ids', new_yarn_course_to_loop_ids)
            # print(f'[*new_yarn_course_to_loop_ids.values()] is {[*new_yarn_course_to_loop_ids.values()]}')
            new_yarn_nodes = set(item for sublist in [*new_yarn_course_to_loop_ids.values()] for item in sublist) 
            self.holes_to_old_and_new_yarns[hole_index]['new_yarn_nodes'] = new_yarn_nodes
            self.holes_to_old_and_new_yarns[hole_index]['old_yarn_nodes'] = self.graph_nodes.difference(new_yarn_nodes).difference(set(hole_info['hole_nodes']))
        # get nodes on the old yarn
        real_old_yarn_nodes = self.holes_to_old_and_new_yarns[hole_index]['old_yarn_nodes']
        for hole_index in self.holes_to_old_and_new_yarns.keys():
            old_yarn_nodes = self.holes_to_old_and_new_yarns[hole_index]['old_yarn_nodes']
            real_old_yarn_nodes = real_old_yarn_nodes.intersection(old_yarn_nodes)
        print(f'in get_new_yarn_loop_ids_for_holes(), hole_index is {hole_index}, real_old_yarn_nodes is {real_old_yarn_nodes}')

        # get nodes for different new yarns
        hole_index_to_new_yarn_nodes = {}
        # 
        hole_index_pair_intersect = []
        for hole_index in self.holes_to_old_and_new_yarns.keys():
            real_new_yarn_nodes = self.holes_to_old_and_new_yarns[hole_index]['new_yarn_nodes']
            print(f'in get_new_yarn_loop_ids_for_holes(), before snip, hole_index is {hole_index}, real_new_yarn_nodes is {real_new_yarn_nodes}')
            # flag = False
            for hole_index_inside in self.holes_to_old_and_new_yarns.keys():
                other_new_yarn_nodes = self.holes_to_old_and_new_yarns[hole_index_inside]['new_yarn_nodes']
                if hole_index_inside == hole_index:
                    print(f'hole_index is {hole_index}, hole_index_inside is {hole_index_inside}, same new yarn nodes, continue')
                    # flag = True
                    continue
                else:
                    if len(real_new_yarn_nodes.intersection(other_new_yarn_nodes)) != 0:
                        # if real_new_yarn_nodes.issubset(other_new_yarn_nodes):
                        #     continue
                        # else:
                        #     if [hole_index, hole_index_inside] in hole_index_pair_intersect:
                        #         continue
                        #     real_new_yarn_nodes = real_new_yarn_nodes.difference(other_new_yarn_nodes)
                        #     hole_index_pair_intersect.append([hole_index_inside, hole_index])
                        if [hole_index, hole_index_inside] in hole_index_pair_intersect or [hole_index_inside, hole_index] in hole_index_pair_intersect:
                                print(f'hole_index is {hole_index}, hole_index_inside is {hole_index_inside}, snip has existed, continue')
                                continue
                        print(f'hole_index is {hole_index}, hole_index_inside is {hole_index_inside}, real_new_yarn_nodes is {real_new_yarn_nodes}, other_new_yarn_nodes is\
                              {other_new_yarn_nodes}, real_new_yarn_nodes.issubset(other_new_yarn_nodes) is {real_new_yarn_nodes.issubset(other_new_yarn_nodes)}')
                        if  real_new_yarn_nodes.issubset(other_new_yarn_nodes) == False:
                            real_new_yarn_nodes = real_new_yarn_nodes.difference(other_new_yarn_nodes)
                            print(f'hole_index is {hole_index}, hole_index_inside is {hole_index_inside}, updated real_new_yarn_nodes is {real_new_yarn_nodes}, other_new_yarn_nodes is\
                                {other_new_yarn_nodes}')
                            hole_index_pair_intersect.append([hole_index, hole_index_inside])
    
            # finally, we need to delete the all hole nodes if it is included on the real_new_yarn_nodes
            print(f'in get_new_yarn_loop_ids_for_holes(), after snip, hole_index is {hole_index}, real_new_yarn_nodes is {real_new_yarn_nodes}')
            # if flag == True:
            for hole in self.yarns_and_holes_to_add.values():
                for node in hole:
                    if node in real_new_yarn_nodes:
                        real_new_yarn_nodes.remove(node)
            hole_index_to_new_yarn_nodes[hole_index] = sorted(real_new_yarn_nodes)
        print(f'hole_index_to_new_yarn_nodes is {hole_index_to_new_yarn_nodes}')
        return real_old_yarn_nodes, hole_index_to_new_yarn_nodes

    def bring_new_yarn(self):
        """
        Create a new yarn with new carrier id.
        """
        hole_index = 0
        for new_yarn_id, carrier_id in zip(self.new_yarn_ids, self._new_carriers):
            new_yarn = Yarn(new_yarn_id, self._knit_graph, carrier_id=carrier_id)
            self._knit_graph.add_yarn(new_yarn)
            self._new_yarns[hole_index] = new_yarn
            hole_index += 1
    
    def remove_old_and_add_new_yarn(self, real_old_yarn_nodes, hole_index_to_new_yarn_nodes):    
        """
        remove loop_ids from old yarn and add loop_ids to new yarn.
        """        
        self._old_yarn.yarn_graph.remove_nodes_from(real_old_yarn_nodes)
        for hole_index in hole_index_to_new_yarn_nodes.keys():
            new_yarn_nodes = hole_index_to_new_yarn_nodes[hole_index]
            new_yarn = self._new_yarns[hole_index]
            self._old_yarn.yarn_graph.remove_nodes_from(new_yarn_nodes)
            for loop_id in new_yarn_nodes:
                child_id, loop = new_yarn.add_loop_to_end(loop_id = loop_id)
        # use this method makes it no need to invoke reconnect_old_yarn_at_margin()
        self._old_yarn.last_loop_id = None
        for loop_id in real_old_yarn_nodes:
            child_id, loop = self._old_yarn.add_loop_to_end(loop_id = loop_id)
    
    #@deprecated
    def connect_hole_edge_nodes(self):
        for hole_index in [*self.holes_size.keys()]:
            if len(self._hole_course_to_wale_ids[hole_index].keys()) > 1:
                # since now we allow hole of different shapes, hole edge node can be unstable because of this, refer to node 21 on pp. 52 of the sldies,
                # thus besides hole bottom nodes, we also need to examine the hole edge node on the hole_start_course to see if any of them needs to be connected
                hole_start_course = self.holes_size[hole_index]['hole_start_course']
                hole_edge_node_small_wale_id =  min(self._hole_course_to_wale_ids[hole_index][hole_start_course]) - (self.wale_dist)
                hole_edge_node_big_wale_id = max(self._hole_course_to_wale_ids[hole_index][hole_start_course]) + (self.wale_dist)
                # for hole_edge_node_small_wale and hole_edge_node_big_wale, the connected node should be 
                connected_node_small_wale_id_for_hole_edge = min(self._hole_course_to_wale_ids[hole_index][hole_start_course+1]) - (self.wale_dist)
                connected_node_big_wale_id_for_hole_edge = max(self._hole_course_to_wale_ids[hole_index][hole_start_course+1]) + (self.wale_dist)
                # hole edge node work as node to connect for unstable node (hole bottom nodes). hole edge node refer to nodes sit immediately right next to the hole nodes on first
                # row. More details please refer to pp. 168 
                hole_edge_node_small_wale_position = (hole_start_course, hole_edge_node_small_wale_id)
                hole_edge_node_big_wale_position = (hole_start_course, hole_edge_node_big_wale_id)
                connected_node_small_wale_for_hole_edge_position = (hole_start_course+1, connected_node_small_wale_id_for_hole_edge)
                connected_node_big_wale_for_hole_edge_position =  (hole_start_course+1, connected_node_big_wale_id_for_hole_edge)
                if hole_edge_node_small_wale_position in self._knit_graph.course_and_wale_to_node.keys():
                    node = self._knit_graph.course_and_wale_to_node[hole_edge_node_small_wale_position]
                    child_ids = [*self._knit_graph.graph.successors(node)] 
                    if len(child_ids) == 0:
                        parent_offset = hole_edge_node_small_wale_id - connected_node_small_wale_id_for_hole_edge
                        if connected_node_small_wale_for_hole_edge_position in self._knit_graph.course_and_wale_to_node.keys():
                            connected_node_small_wale_for_hole_edge = self._knit_graph.course_and_wale_to_node[connected_node_small_wale_for_hole_edge_position]
                            self._knit_graph.connect_loops(node, connected_node_small_wale_for_hole_edge, parent_offset = -parent_offset)
                        else:
                            print(f'no connected_node_small_wale_for_hole_edge is found at position {connected_node_small_wale_for_hole_edge}')
                if hole_edge_node_big_wale_position in self._knit_graph.course_and_wale_to_node.keys():
                    node = self._knit_graph.course_and_wale_to_node[hole_edge_node_big_wale_position]
                    child_ids = [*self._knit_graph.graph.successors(node)] 
                    if len(child_ids) == 0:
                        parent_offset = hole_edge_node_big_wale_id - connected_node_big_wale_id_for_hole_edge
                        if connected_node_big_wale_for_hole_edge_position in self._knit_graph.course_and_wale_to_node.keys():
                            connected_node_big_wale_for_hole_edge = self._knit_graph.course_and_wale_to_node[connected_node_big_wale_for_hole_edge_position]
                            print(f'child_ids is {child_ids}, node is {node}, connected_node_big_wale_for_hole_edge is {connected_node_big_wale_for_hole_edge}') 
                            self._knit_graph.connect_loops(node, connected_node_big_wale_for_hole_edge, parent_offset = -parent_offset)
                        else:
                            print(f'no connected_node_big_wale_for_hole_edge is found at position {connected_node_big_wale_for_hole_edge}')   
                        
    # currently, we only apply bind-off on the hole bottom nodes to stabilize them
    def bind_off(self):
        for hole_index in [*self.holes_size.keys()]:
            # first search for nodes that have no child on the hole bottom course (the course immediately below the hole area)
            # current version relaxing the racking constraint of up to 2 needle on beds
            # hole_bottom_course_id = self.holes_size[hole_index]['hole_start_course'] - 1
            for course_id in range(self.holes_size[hole_index]['hole_start_course'] - 1, self.holes_size[hole_index]['hole_start_course'] - 1 + self.holes_size[hole_index]['hole_height']):
                # then, connect them end to end, consistent with the yarn walking direction for that course
                bottom_nodes = []
                bottom_nodes = self._knit_graph.course_to_loop_ids[course_id]
                # then connect nodes that have no child to its nearest neighbor node
                # we sorted the nodes so that we can guarantee that small nodes is connected to the bigger nodes, which is consistent with bind-off. it can be reverted.
                sorted_bottom_nodes = sorted(bottom_nodes)
                # print(f'sorted_bottom_nodes for course_id: {hole_bottom_course_id+1} is {sorted_bottom_nodes}')
                for i in range(len(sorted_bottom_nodes)-1):
                    node = sorted_bottom_nodes[i]
                    # instead of using below method, we won't stop until finding the node to connect to acheive bind-off, if can't find any, throw an error.
                    # nearest_neighbor = sorted_bottom_nodes[i+1]
                    # if node not in self._knit_graph.graph.nodes or nearest_neighbor not in self._knit_graph.graph.nodes:
                    #     continue
                    if node in self._knit_graph.graph.nodes:
                        child_ids = [*self._knit_graph.graph.successors(node)] 
                        # print(f'node is {node},child_ids is {child_ids}')
                        if len(child_ids) == 0: # only connect node that have no child, i.e., unstable
                            for potential_node_to_connect in sorted_bottom_nodes[i+1:]:
                                if potential_node_to_connect not in self._knit_graph.graph.nodes:
                                    continue
                                else:
                                    parent_wale_id = self._knit_graph.node_to_course_and_wale[node][1]
                                    child_wale_id = self._knit_graph.node_to_course_and_wale[potential_node_to_connect][1]
                                    # todo: if the parent offset of bind_off is larger than 2, we will consider using connect_hole_edge_node(). But if the parent offset in connect_\
                                    # hole_edge_node is also larger than 2, we will send out a error and exit.
                                    # we use (parent_wale_id - child_wale_id)/self.wale_dist rather than (parent_wale_id - child_wale_id) above is 
                                    # because we will "parent_offset*self.wale_dist" in final_knitgraph_to_knitout.py again. 
                                    # below we perform bind-off safety check
                                    # first, get all the parent loops that are sitting on the course underneath the course that nearest_neighbor node is on
                                    if len([*self._knit_graph.graph.predecessors(potential_node_to_connect)]) != 0:
                                        predecessors = [*self._knit_graph.graph.predecessors(potential_node_to_connect)] 
                                        pull_direction = self._knit_graph.graph[predecessors[0]][potential_node_to_connect]['pull_direction']
                                        #----
                                        # for predecessor in predecessors:
                                        #     # this only applies to case where yarn starting direction is from right to left
                                        #     if course_id % 2 == 0:
                                        #         if self._knit_graph.graph[predecessor][potential_node_to_connect]['parent_offset'] > 0:
                                        #             raise ErrorException(f'bind-off safety check failed because loop {predecessor} has been dropped so can not be connected to loop {potential_node_to_connect}')
                                        #     else:
                                        #         if self._knit_graph.graph[predecessor][potential_node_to_connect]['parent_offset'] < 0:
                                        #             raise ErrorException(f'bind-off safety check failed because loop {predecessor} has been dropped so can not be connected to loop {potential_node_to_connect}')
                                        #----
                                        self._knit_graph.connect_loops(node, potential_node_to_connect, parent_offset = int((parent_wale_id - child_wale_id)/self.wale_dist), pull_direction = pull_direction)
                                    else:
                                        # then it is actually a single cable stitch (special, because no crossing between two or more stitches here), thus we need to set the depth as 1.
                                        pull_direction = Pull_Direction.BtF
                                        self._knit_graph.connect_loops(node, potential_node_to_connect, parent_offset = int((parent_wale_id - child_wale_id)/self.wale_dist), pull_direction = pull_direction, depth = 1)
                                    break
    def add_hole(self):
        #first determine the validity of the input hole
        # self.hole_shape_and_number_constraints()
        #return info including hole_start_wale, hole_end_wale, hole_start_course, hole_end_course, hole_height and hole_width.
        print(f'cp3, is {self._knit_graph.node_on_front_or_back}')
        self.get_hole_size()
        print(f'cp2, is {self._knit_graph.node_on_front_or_back}')
        #send out warning to user if special stitch might be broken or if hole node is set at places like top course.
        self.hole_location_errors()
        self.hole_location_warnings()
        # get course_to_wale_ids for hole area
        self.get_hole_course_to_wale_ids()
        print(f'cp1, is {self._knit_graph.node_on_front_or_back}')
        #remove nodes for hole from both knit graph and yarn graph.
        self.remove_hole_nodes_from_graph()
        #get the start wale id and end wale id for each course, which can be used in get_new_yarn_loop_ids() to get new yarn loop ids.
        self.get_start_and_end_wale_id_per_course()
        #get new yarn loop ids
        real_old_yarn_nodes, hole_index_to_new_yarn_nodes = self.get_new_yarn_loop_ids_for_holes()
        #create a new yarn object.
        self.bring_new_yarn()
        #remove nodes in "new_yarn_course_to_loop_ids" from old yarn and add these nodes to the new yarn.
        self.remove_old_and_add_new_yarn(real_old_yarn_nodes, hole_index_to_new_yarn_nodes) 
        #connect unstable (have no child loops) nodes on the edge of the hole to the nearest top neighbor to prevent them from falling off the parent loops,
        #leading the hole bigger and bigger.
        # self.connect_hole_edge_nodes()
        # to prevent hole deformation, we can also use the bind-off
        self.bind_off()
        # note that we only update (delete hole nodes on the self._knit_graph, we do not correspondingly update nodes in both self._knit_graph.node_on_front_or_back and self._knit_graph.node_to_course_and_wale)
        # KnitGraph_Visualizer = knitGraph_visualizer(self._knit_graph, node_on_front_or_back = self._knit_graph.node_on_front_or_back, node_to_course_and_wale = self._knit_graph.node_to_course_and_wale, object_type = 'sheet')
        # KnitGraph_Visualizer.visualize()
        return self._knit_graph



