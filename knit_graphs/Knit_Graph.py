"""The graph structure used to represent knitted objects"""
from enum import Enum
from typing import Dict, Optional, List, Tuple, Union, Set

import networkx

from knit_graphs.Loop import Loop
from knit_graphs.Yarn import Yarn
from knitting_machine.Machine_State import Yarn_Carrier


class Pull_Direction(Enum):
    """An enumerator of the two pull directions of a loop"""
    BtF = "BtF"
    FtB = "FtB"

    def opposite(self):
        """
        :return: returns the opposite pull direction of self
        """
        if self is Pull_Direction.BtF:
            return Pull_Direction.FtB
        else:
            return Pull_Direction.BtF

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

class Knit_Graph:
    """
    A class to knitted structures
    ...

    Attributes
    ----------
    graph : networkx.DiGraph
        the directed-graph structure of loops pulled through other loops
    loops: Dict[int, Loop]
        A map of each unique loop id to its loop
    yarns: Dict[str, Yarn]
         A list of Yarns used in the graph
    """

    def __init__(self, yarn_start_direction: Optional[str] = 'right to left', gauge: Optional[int] = 1): 
        self.graph: networkx.DiGraph = networkx.DiGraph()
        self.loops: Dict[int, Loop] = {}
        self.last_loop_id: int = -1
        self.yarns: Dict[str, Yarn] = {}
        self.gauge: float = gauge
        self.wale_dist: int = int(1/self.gauge)
        self.object_type: str
        self.loop_ids_to_course: Dict[int, int] = {}
        self.course_to_loop_ids: Dict[int, List[int]] = {}
        self.course_to_loop_ids_including_slip: Dict[int, List[int]] = {}
        self.loop_ids_to_wale: Dict[int, int] = {}
        self.wale_to_loop_ids: Dict[int, List[int]] = {}
        self.node_to_course_and_wale: Dict[int, Tuple[int, int]] = {}
        self.node_on_front_or_back: Dict[int, str] = {}
        self.course_and_wale_and_bed_to_node: Dict[((int, int), str), int] = {}
        self.yarn_start_direction: str = yarn_start_direction

        self.loops_on_front_part_of_the_tube: Set[int] = set()
        self.loops_on_back_part_of_the_tube: Set[int] = set()
        
        self.yarn_over_loop_to_loop_index: Dict[int, int] = {}

        self.course_id_to_walking_direction: Dict[int, str] = {}

        self.courses_to_min_wale_on_front: Dict[int, int] = {}
        self.courses_to_min_wale_on_back: Dict[int, int] = {}
        self.courses_to_max_wale_on_front: Dict[int, int] = {}
        self.courses_to_max_wale_on_back: Dict[int, int] = {}

        self.courses_to_number_of_left_leaning_front_half: Dict[int, int] = {}
        self.courses_to_number_of_right_leaning_front_half: Dict[int, int] = {}
        self.courses_to_number_of_left_leaning_back_half: Dict[int, int] = {}
        self.courses_to_number_of_right_leaning_back_half: Dict[int, int] = {}

        self.courses_to_max_loop_id_left_leaning_front_half: Dict[int, int] = {}
        self.courses_to_max_loop_id_right_leaning_front_half: Dict[int, int] = {}
        self.courses_to_max_loop_id_left_leaning_back_half: Dict[int, int] = {}
        self.courses_to_max_loop_id_right_leaning_back_half: Dict[int, int] = {}

        self.course_to_loops_on_front_part_of_the_tube: Dict[int, List[int]] = {}
        self.course_to_loops_on_back_part_of_the_tube: Dict[int, List[int]] = {}

        self.course_to_row: Dict[int, bool] = {} 

    def add_loop_to_front_part(self, loop_id: int):
        self.loops_on_front_part_of_the_tube.add(loop_id)

    def add_loop_to_back_part(self, loop_id: int):
        self.loops_on_back_part_of_the_tube.add(loop_id)
    
    def add_index_for_yarn_over_loop(self, loop_id, index):
        self.yarn_over_loop_to_loop_index[loop_id] = index

    def add_loop(self, loop: Loop):
        """
        :param loop: the loop to be added in as a node in the graph
        """
        # below we can see "loop" is added as an attribute in add_node, corresponds to the get_item() down below
        self.graph.add_node(loop.loop_id, loop=loop)
        assert loop.yarn_id in self.yarns, f"No yarn {loop.yarn_id} in this graph"
      
        if loop not in self.yarns[loop.yarn_id]:  # make sure the loop is on the yarn specified
            self.yarns[loop.yarn_id].add_loop_to_end(loop_id=None, loop=loop)
           
        self.loops[loop.loop_id] = loop

    def add_yarn(self, yarn: Yarn):
        """
        :param yarn: the yarn to be added to the graph structure
        """
        self.yarns[yarn.yarn_id] = yarn

    def connect_loops(self, parent_loop_id: int, child_loop_id: int,
                      pull_direction: Pull_Direction = Pull_Direction.BtF,
                      stack_position: Optional[int] = None, depth: int = 0, parent_offset: int = 0):
        """
        Creates a stitch-edge by connecting a parent and child loop
        :param parent_offset: The direction and distance, oriented from the front, to the parent_loop
        :param depth: -1, 0, 1: The crossing depth in a cable over other stitches. 0 if Not crossing other stitches
        :param parent_loop_id: the id of the parent loop to connect to this child
        :param child_loop_id:  the id of the child loop to connect to the parent
        :param pull_direction: the direction the child is pulled through the parent
        :param stack_position: The position to insert the parent into, by default add on top of the stack
        """
        assert parent_loop_id in self, f"parent loop {parent_loop_id} is not in this graph"
        assert child_loop_id in self, f"child loop {child_loop_id} is not in this graph"
        self.graph.add_edge(parent_loop_id, child_loop_id, pull_direction=pull_direction, depth=depth, parent_offset=parent_offset)
        child_loop = self[child_loop_id]
        parent_loop = self[parent_loop_id]
        # print(child_loop, parent_loop)
        child_loop.add_parent_loop(parent_loop, stack_position)
    
    def get_courses(self) -> Tuple[Dict[int, int], Dict[int, List[int]]]:
        """
        :return: A dictionary of loop_ids to the course they are on,
        a dictionary or course ids to the loops on that course in the order of creation
        The first set of loops in the graph is on course 0.
        A course change occurs when a loop has a parent loop that is in the last course.
        """
        # loop_ids_to_course = {}
        # course_to_loop_ids = {}
        current_course_set = set()
        current_course = []
        course = 0
        #since given knit graph has only one yarn before being modified
        for loop_id in self.graph.nodes:
            no_parents_in_course = True
            for parent_id in self.graph.predecessors(loop_id):
                # print(f'predecessors is {[*self.graph.predecessors(loop_id)]}, loop_id is {loop_id}')
                if parent_id in current_course_set:
                    no_parents_in_course = False
                    break
            if no_parents_in_course:
                current_course_set.add(loop_id)
                current_course.append(loop_id)
            else:
                self.course_to_loop_ids[course] = current_course
                current_course = [loop_id]
                current_course_set = {loop_id}
                course += 1
            self.loop_ids_to_course[loop_id] = course
            # print(f'current_course_set is {current_course_set}')
        self.course_to_loop_ids[course] = current_course
        print(f'course_to_loop_ids in Knit_Graph is {self.course_to_loop_ids}')
        return self.loop_ids_to_course, self.course_to_loop_ids

    def get_wales(self) :
        print(f'self.yarn_over_loop_to_loop_index is {self.yarn_over_loop_to_loop_index}')
        yarns = [*self.yarns.values()]
        #since given knit graph has only one yarn before being modified
        yarn = yarns[0]
        # loop_ids_to_wale = {}
        # wale_to_loop_ids = {}
        first_course_loop_ids = self.course_to_loop_ids[0] 
        wale = 0
        assert (1/self.gauge).is_integer() == True, f'wrong gauge info'
        self.wale_dist = int(1/self.gauge)
        # print(f'self.wale_dist is {self.wale_dist}')
        for loop_id in first_course_loop_ids:
            self.loop_ids_to_wale[loop_id] = wale
            self.wale_to_loop_ids[wale] = [loop_id]
            # wale += 1
            wale += self.wale_dist
            # print(f'loop_id is {loop_id}, wale is {wale}')
        for course_id in [*self.course_to_loop_ids.keys()][1:]:
            next_row_loop_ids = self.course_to_loop_ids[course_id]
            for loop_id in next_row_loop_ids:
                self.has_parent_of_0_offset = False
                parent_ids = [*self.graph.predecessors(loop_id)]
                if len(parent_ids) > 0:
                    for parent_id in self.graph.predecessors(loop_id):
                        parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                        if parent_offset == 0:
                            wale = self.loop_ids_to_wale[parent_id]
                            self.loop_ids_to_wale[loop_id] = wale
                            if wale not in self.wale_to_loop_ids:
                                self.wale_to_loop_ids[wale] = []
                                self.wale_to_loop_ids[wale].append(loop_id)
                            else:
                                self.wale_to_loop_ids[wale].append(loop_id)
                            # print(f'loop id is {loop_id}, parent id is {parent_id}, wale is {wale}')
                            self.has_parent_of_0_offset = True
                            break
                    if self.has_parent_of_0_offset == False:
                        for parent_id in self.graph.predecessors(loop_id):
                            parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                            wale = self.loop_ids_to_wale[parent_id] - parent_offset*self.wale_dist
                            # if self.object_type == 'sheet':
                            #     wale = self.loop_ids_to_wale[parent_id] - parent_offset*self.wale_dist
                            # elif self.object_type == 'tube':
                            #     wale = self.loop_ids_to_wale[parent_id] + parent_offset*self.wale_dist
                            self.loop_ids_to_wale[loop_id] = wale
                            if wale not in self.wale_to_loop_ids:
                                self.wale_to_loop_ids[wale] = []
                                self.wale_to_loop_ids[wale].append(loop_id)
                            else:
                                self.wale_to_loop_ids[wale].append(loop_id)
                            break
                else:
                    #If its predecessor node on yarn has wale, then combined with corresponding course_id, its wale can be inferred
                    #Since a node on yarn always has one predecessor, except that starting node has 0 predecessor.
                    # yarn_predecessor = [*yarn.yarn_graph.predecessors(loop_id)][0]
                    # # yarn_successor = [*yarn.yarn_graph.successors(loop_id)][0]
                    # if yarn_predecessor in self.loop_ids_to_wale.keys():
                    #     pre_wale = self.loop_ids_to_wale[yarn_predecessor]
                    #     if self.object_type == 'sheet':
                    #         if course_id % 2 == 1:
                    #             wale = pre_wale - self.wale_dist
                    #             self.loop_ids_to_wale[loop_id] = wale
                    #         else: 
                    #             wale = pre_wale + self.wale_dist
                    #             self.loop_ids_to_wale[loop_id] = wale
                    #     elif self.object_type == 'tube':
                    #         wale = pre_wale + self.wale_dist
                    #         self.loop_ids_to_wale[loop_id] = wale
                    #     if wale not in self.wale_to_loop_ids:
                    #         self.wale_to_loop_ids[wale] = [loop_id]
                    #     else:
                    #         self.wale_to_loop_ids[wale].append(loop_id)
                    # else:
                    #     print(f'Error: wale of node {loop_id} cannot be determined')
                    #     exit()

                    #----#
                    if self.object_type == 'sheet':
                        if course_id % 2 == 1:
                            wale = self.loop_ids_to_wale[self.course_to_loop_ids[course_id-1][-1]] - self.yarn_over_loop_to_loop_index[loop_id]*self.wale_dist
                            self.loop_ids_to_wale[loop_id] = wale
                        else:
                            wale = self.loop_ids_to_wale[self.course_to_loop_ids[course_id-1][-1]] + self.yarn_over_loop_to_loop_index[loop_id]*self.wale_dist
                            self.loop_ids_to_wale[loop_id] = wale
                    else:
                        if loop_id in self.loops_on_front_part_of_the_tube:
                            wale = self.yarn_over_loop_to_loop_index[loop_id]*self.wale_dist
                            self.loop_ids_to_wale[loop_id] = wale
                        else:
                            mid_node =self.course_to_loop_ids[0][int(len(first_course_loop_ids)/2) - 1]
                            print(f'self.yarn_over_loop_to_loop_index[loop_id] is {self.yarn_over_loop_to_loop_index[loop_id]}')
                            wale = self.loop_ids_to_wale[mid_node] -1 - self.yarn_over_loop_to_loop_index[loop_id]*self.wale_dist
                            self.loop_ids_to_wale[loop_id] = wale
                    #----#
        print(f'in get_wale(), loop_ids_to_wale in KnitGraph is {self.loop_ids_to_wale}, wale_to_loop_ids in KnitGraph is {self.wale_to_loop_ids}')
        return self.loop_ids_to_wale, self.wale_to_loop_ids

    def get_node_bed(self):
        if self.object_type == 'sheet':
            for node in self.graph.nodes:
                self.node_on_front_or_back[node] = 'f'
        elif self.object_type == 'tube':
            for node in self.graph.nodes:
                if node in self.loops_on_front_part_of_the_tube:
                    self.node_on_front_or_back[node] = 'f'
                else:
                    self.node_on_front_or_back[node] = 'b'
        print(f'self.node_on_front_or_back in Knit Graph is {self.node_on_front_or_back}')
        return self.node_on_front_or_back

    def get_node_bed_for_courses(self):
        self.course_to_loop_ids_including_slip[0] = self.course_to_loop_ids[0]
        for course_id in [*self.course_to_loop_ids.keys()]:
            self.course_to_loops_on_back_part_of_the_tube[course_id] = []
            self.course_to_loops_on_front_part_of_the_tube[course_id] = []
            # for loop_id in self.course_to_loop_ids[course_id]:
            for loop_id in self.course_to_loop_ids_including_slip[course_id]:
                bed = self.node_on_front_or_back[loop_id]
                if bed == 'b':
                    self.course_to_loops_on_back_part_of_the_tube[course_id].append(loop_id)
                else:
                    self.course_to_loops_on_front_part_of_the_tube[course_id].append(loop_id)
        print(f'self.course_to_loops_on_front_part_of_the_tube in Knit Graph is {self.course_to_loops_on_front_part_of_the_tube}, \
              self.course_to_loops_on_back_part_of_the_tube in Knit Graph is {self.course_to_loops_on_back_part_of_the_tube}')
        return self.course_to_loops_on_front_part_of_the_tube, self.course_to_loops_on_back_part_of_the_tube

    def get_node_course_and_wale(self):
        """
        this used real wale id self.loop_ids_to_wale above to calculate the final wale id used for visualization for tube.
        """
        for node in self.graph.nodes:
            course = self.loop_ids_to_course[node]
            wale = self.loop_ids_to_wale[node]
            self.node_to_course_and_wale[node] = (course, wale)
        if self.object_type == 'tube':
            #-----deprecated as this not accommodate tube object with increase
            # first_course_loops = self.course_to_loop_ids[0] # first course loops is considered because there will be no slip for it.
            # mid_node_pos = int(len(first_course_loops)/2) - 1
            # mid_node = first_course_loops[mid_node_pos]
            # mid_node_wale = self.loop_ids_to_wale[mid_node]
            # last_node = first_course_loops[-1]
            # max_wale = self.loop_ids_to_wale[last_node]
            # #below is original version that works well except for tube with increase stitch
            # for node in self.graph.nodes:
            #     course = self.loop_ids_to_course[node]
            #     wale = self.loop_ids_to_wale[node]
            #     if wale > mid_node_wale:
            #         adjusted_wale = max_wale - wale -1 #-1 is because we use half gauging to avoid loop collision. And by doing this, the wale of the mirror
            #         #node on the back is always one wale smaller than that of corresponding node on the front.
            #         self.node_to_course_and_wale[node] = (course, adjusted_wale)
            #----deprecated-----
            #--- this version aims to accommodate tube object with increase---
            first_course_loop_ids = self.course_to_loop_ids[0] 
            mid_node_pos = int(len(first_course_loop_ids)/2) - 1
            mid_node = first_course_loop_ids[mid_node_pos]
            mid_node_wale = self.loop_ids_to_wale[mid_node]
            last_node = first_course_loop_ids[-1]
            max_wale = self.loop_ids_to_wale[last_node]
            #we do the wale adjustment only on the first course
            for node in first_course_loop_ids:
                course = self.loop_ids_to_course[node]
                wale = self.loop_ids_to_wale[node]
                if wale > mid_node_wale:
                    adjusted_wale = max_wale - wale -1 #-1 is because we use half gauging to avoid loop collision. And by doing this, the wale of the mirror
                    #node on the back is always one wale smaller than that of corresponding node on the front.
                    self.node_to_course_and_wale[node] = (course, adjusted_wale)
            #then for the remaining course, we use the adjusted wale to compute
            yarns = [*self.yarns.values()]
            #since given knit graph has only one yarn before being modified
            yarn = yarns[0]
            for course_id in [*self.course_to_loop_ids.keys()][1:]:
                next_row_loop_ids = self.course_to_loop_ids[course_id]
                for loop_id in next_row_loop_ids:
                    self.has_parent_of_0_offset = False
                    parent_ids = [*self.graph.predecessors(loop_id)]
                    if len(parent_ids) > 0:
                        #--------
                        # for parent_id in self.graph.predecessors(loop_id):
                        #     parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                        #     if parent_offset == 0:
                        #         wale = self.node_to_course_and_wale[parent_id][1]
                        #         self.node_to_course_and_wale[loop_id] = (course_id, wale)
                        #         # print(f'in tube wale recomputation, loop id is {loop_id}, parent id is {parent_id}, wale is {wale}')
                        #         self.has_parent_of_0_offset = True
                        #         break
                        # if self.has_parent_of_0_offset == False:
                        #     for parent_id in self.graph.predecessors(loop_id):
                        #         parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                        #         wale = self.node_to_course_and_wale[parent_id][1] - parent_offset*self.wale_dist
                        #         self.node_to_course_and_wale[loop_id] = (course_id, wale)
                        #         break
                        #---------
                        #------
                        for parent_id in self.graph.predecessors(loop_id):
                            parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                            wale = self.node_to_course_and_wale[parent_id][1] - parent_offset*self.wale_dist
                            print(f'loop_id is {loop_id}, parent id is {parent_id}, parent wale is {self.node_to_course_and_wale[parent_id][1]}, \
                                  original wale is {self.node_to_course_and_wale[loop_id][1]}, parent_offset is {parent_offset}, updated wale is {wale}')
                            self.node_to_course_and_wale[loop_id] = (course_id, wale)
                            break
                        #-------
                    else:
                        #If its predecessor node on yarn has wale, then combined with corresponding course_id, its wale can be inferred
                        #Since a node on yarn always has one predecessor, except that starting node has 0 predecessor.
                        # yarn_predecessor = [*yarn.yarn_graph.predecessors(loop_id)][0]
                        # # yarn_successor = [*yarn.yarn_graph.successors(loop_id)][0]
                        # if yarn_predecessor in self.node_to_course_and_wale.keys():
                        #     pre_wale = self.node_to_course_and_wale[yarn_predecessor][1]
                        #     if self.object_type == 'tube':
                        #         wale = pre_wale + self.wale_dist
                        #         self.node_to_course_and_wale[loop_id] = (course_id, wale)
                        # else:
                        #     print(f'Error: wale of node {loop_id} cannot be determined')
                        #     exit()
                        #----#  this is for the yarn over node (seem unnecessary anymore since we have done mid-node wale adjustment at the end of get_wale() above)
                        if loop_id in self.loops_on_front_part_of_the_tube:
                            wale = self.yarn_over_loop_to_loop_index[loop_id]*self.wale_dist
                        else:
                            wale = mid_node_wale -1 - self.yarn_over_loop_to_loop_index[loop_id]*self.wale_dist
                        #----#
                # #----move loops from one bed to another if the number of loops on both beds are not equal
                # n_f = len(self.course_to_loops_on_front_part_of_the_tube[course_id])
                # n_b = len(self.course_to_loops_on_back_part_of_the_tube[course_id])
                # if n_b > n_f:
                #     num_loops_on_one_bed = int((n_b+n_f)/2)
                #     right_end_wale_front = self.loop_ids_to_wale[self.course_to_loop_ids[course_id][0]] #c is course id 
                #     for i in range(n_b-num_loops_on_one_bed): #the number of loops that should be moved to the other bed
                #         loop = self.course_to_loop_ids[course_id][-1-i]
                        
                #         wale = right_end_wale_front-self.wale_dist
                #         right_end_wale_front = wale
                #         self.loop_ids_to_wale[loop] = wale
                #         self.node_to_course_and_wale[loop] = (course_id, wale)
                #         self.node_on_front_or_back[loop] = 'f'
                #         # self.course_to_loops_on_back_part_of_the_tube[course_id].remove(loop)
                #         # self.course_to_loops_on_front_part_of_the_tube[course_id].append(loop)
                # elif n_b < n_f:
                #     num_loops_on_one_bed = int((n_b+n_f)/2)
                #     for back_loop in self.course_to_loops_on_back_part_of_the_tube[course_id]:
                #         wale = self.node_to_course_and_wale[back_loop][1] - self.wale_dist*(n_f - num_loops_on_one_bed)
                #         print(f'back loop is {back_loop}, self.node_to_course_and_wale[back_loop][1] is {self.node_to_course_and_wale[back_loop][1]}, wale is {wale}')
                #         self.loop_ids_to_wale[back_loop] = wale
                #         self.node_to_course_and_wale[back_loop] = (course_id, wale)
                #     print(f'self.node_to_course_and_wale is {self.node_to_course_and_wale}, self.course_to_loops_on_back_part_of_the_tube[course_id] is {self.course_to_loops_on_back_part_of_the_tube[course_id]}')
                #     left_end_wale_back = self.node_to_course_and_wale[min(self.course_to_loops_on_back_part_of_the_tube[course_id])][1]
                #     print(f'left_end_wale_back is {left_end_wale_back}')
                #     for i in range(n_f - num_loops_on_one_bed):
                #         loop = self.course_to_loops_on_front_part_of_the_tube[course_id][-1-i]
                #         print(f'haha loop is {loop}')
                #         wale = left_end_wale_back+self.wale_dist
                #         left_end_wale_back = wale
                #         print(f'haha wale is {wale}')
                #         self.loop_ids_to_wale[loop] = wale
                #         self.node_to_course_and_wale[loop] = (course_id, wale)
                #         self.node_on_front_or_back[loop] = 'b'
                #         # self.course_to_loops_on_front_part_of_the_tube[course_id].remove(loop)
                #         # self.course_to_loops_on_back_part_of_the_tube[course_id].append(loop)
                # #------

                            
                #----
                # print(f'node_to_course_and_wale in KnitGraph before wale readjust is {self.node_to_course_and_wale}')
                #---adjust wale again if there are any leaning stitches that has mismatched parent offset for the first screening
                # if course_id in self.courses_to_number_of_left_leaning_front_half:
                #     number_of_left_leaning_front_half = self.courses_to_number_of_left_leaning_front_half[course_id]
                #     if number_of_left_leaning_front_half > 0:
                #         max_loop_id_left_leaning_front_half = self.courses_to_max_loop_id_left_leaning_front_half[course_id]
                #         parent_ids = [*self.graph.predecessors(max_loop_id_left_leaning_front_half)]
                #         max_parent_offset = 0
                #         for parent_id in parent_ids:
                #             if max_parent_offset < self.graph[parent_id][max_loop_id_left_leaning_front_half]['parent_offset']:
                #                 max_parent_offset = self.graph[parent_id][max_loop_id_left_leaning_front_half]['parent_offset']
                #                 print(f'in wale-redjust, max_parent_offset is {max_parent_offset}')
                #         for parent_id in parent_ids:
                #             parent_offset = self.graph[parent_id][max_loop_id_left_leaning_front_half]['parent_offset']
                #             if parent_offset not in [-1, 0]: #eg. if k2tog misrepresented as skpo in the first ver. of KnitGraph, then the p.o. would be [0, 1].
                #                 #then all the preceding loop ids in this course would need to be adjusted by decreasing offset by 1.
                #                 loop_ids_this_course = self.course_to_loop_ids[course_id]
                #                 parent_offset_gap = max_parent_offset - 0
                #                 for loop_id in loop_ids_this_course:
                #                     if loop_id in self.loops_on_front_part_of_the_tube:
                #                         wale = self.node_to_course_and_wale[loop_id][1] + parent_offset_gap*self.wale_dist
                #                         self.node_to_course_and_wale[loop_id] = (course_id, wale)
                #                     print(f'in wale-redjust, course id is {course_id}, loop_id is {loop_id}, max_loop_id_left_leaning_front_half is {max_loop_id_left_leaning_front_half}, \
                #                           max_parent_offset is {max_parent_offset}, updated wale is {wale}')
                # if course_id in self.courses_to_number_of_left_leaning_back_half:
                #     number_of_left_leaning_back_half = self.courses_to_number_of_left_leaning_back_half[course_id]
                #     if number_of_left_leaning_back_half > 0:
                #         max_loop_id_left_leaning_back_half = self.courses_to_max_loop_id_left_leaning_back_half[course_id]
                #         parent_ids = [*self.graph.predecessors(max_loop_id_left_leaning_back_half)]
                #         max_parent_offset = 0
                #         for parent_id in parent_ids:
                #             if max_parent_offset < self.graph[parent_id][max_loop_id_left_leaning_back_half]['parent_offset']:
                #                 max_parent_offset = self.graph[parent_id][max_loop_id_left_leaning_back_half]['parent_offset']
                #         for parent_id in parent_ids:
                #             # parent_offset = self.graph[parent_id][max_loop_id_left_leaning_back_half]['parent_offset'] #deprecate this bc parent offset might have been updated caused by the wale update above.
                #             parent_offset = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[max_loop_id_left_leaning_back_half][1])/self.wale_dist
                #             if parent_offset not in [-1, 0]: #eg. if k2tog misrepresented as skpo in the first ver. of KnitGraph, then the p.o. would be [0, 1].
                #                 #then all the preceding loop ids in this course would need to be adjusted by increasing offset by 1 (bc on the back half).
                #                 loop_ids_this_course = self.course_to_loop_ids[course_id]
                #                 parent_offset_gap = max_parent_offset - 0
                #                 for loop_id in loop_ids_this_course:
                #                     if loop_id in self.loops_on_back_part_of_the_tube:
                #                         wale = self.node_to_course_and_wale[loop_id][1] - parent_offset_gap*self.wale_dist
                #                         self.node_to_course_and_wale[loop_id] = (course_id, wale)   
                # if course_id in self.courses_to_number_of_right_leaning_back_half:
                #     number_of_right_leaning_back_half = self.courses_to_number_of_right_leaning_back_half[course_id]     
                #     if number_of_right_leaning_back_half > 0:
                #         max_loop_id_right_leaning_back_half = self.courses_to_max_loop_id_right_leaning_back_half[course_id]
                #         parent_ids = [*self.graph.predecessors(max_loop_id_right_leaning_back_half)]
                #         max_parent_offset = 0
                #         for parent_id in parent_ids:
                #             if max_parent_offset < self.graph[parent_id][max_loop_id_right_leaning_back_half]['parent_offset']:
                #                 max_parent_offset = self.graph[parent_id][max_loop_id_right_leaning_back_half]['parent_offset']
                #         for parent_id in parent_ids:
                #             # parent_offset = self.graph[parent_id][max_loop_id_right_leaning_back_half]['parent_offset']
                #             parent_offset = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[max_loop_id_right_leaning_back_half][1])/self.wale_dist
                #             if parent_offset not in [1, 0]: #eg. if k2tog misrepresented as skpo in the first ver. of KnitGraph, then the p.o. would be [0, 1].
                #                 #then all the preceding loop ids in this course would need to be adjusted by increasing offset by 1 (bc on the back half).
                #                 loop_ids_this_course = self.course_to_loop_ids[course_id]
                #                 parent_offset_gap = max_parent_offset - 1
                #                 for loop_id in loop_ids_this_course:
                #                     if loop_id in self.loops_on_back_part_of_the_tube:
                #                         wale = self.node_to_course_and_wale[loop_id][1] + parent_offset_gap*self.wale_dist
                #                         self.node_to_course_and_wale[loop_id] = (course_id, wale) 
                # if course_id in self.courses_to_number_of_right_leaning_front_half:
                #     number_of_right_leaning_front_half = self.courses_to_number_of_right_leaning_front_half[course_id]
                #     if number_of_right_leaning_front_half > 0:
                #         max_loop_id_right_leaning_front_half = self.courses_to_max_loop_id_right_leaning_front_half[course_id]
                #         parent_ids = [*self.graph.predecessors(max_loop_id_right_leaning_front_half)]
                #         max_parent_offset = 0
                #         for parent_id in parent_ids:
                #             if max_parent_offset < self.graph[parent_id][max_loop_id_right_leaning_front_half]['parent_offset']:
                #                 max_parent_offset = self.graph[parent_id][max_loop_id_right_leaning_front_half]['parent_offset']
                #         for parent_id in parent_ids:
                #             # parent_offset = self.graph[parent_id][max_loop_id_right_leaning_front_half]['parent_offset']
                #             parent_offset = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[max_loop_id_right_leaning_front_half][1])/self.wale_dist
                #             if parent_offset not in [1, 0]: #eg. if k2tog misrepresented as skpo in the first ver. of KnitGraph, then the p.o. would be [0, 1].
                #                 #then all the preceding loop ids in this course would need to be adjusted by decreasing offset by 1.
                #                 loop_ids_this_course = self.course_to_loop_ids[course_id]
                #                 parent_offset_gap = max_parent_offset - 0
                #                 for loop_id in loop_ids_this_course:
                #                     if loop_id in self.loops_on_front_part_of_the_tube:
                #                         wale = self.node_to_course_and_wale[loop_id][1] - parent_offset_gap*self.wale_dist
                #                         self.node_to_course_and_wale[loop_id] = (course_id, wale)
                #---
                
        #-------
        print(f'in get_node_course_and_wale(), node_to_course_and_wale in KnitGraph after wale redjust is {self.node_to_course_and_wale}')
        return self.node_to_course_and_wale

    def get_min_and_max_wale_id_on_course_on_bed(self):
        # for course_id, loop_ids in self.course_to_loop_ids_.items():
        self.course_to_loop_ids_including_slip[0] = self.course_to_loop_ids[0]
        print(f'self.course_to_loop_ids_including_slip is {self.course_to_loop_ids_including_slip}')
        for course_id, loop_ids in self.course_to_loop_ids_including_slip.items():
            max_wale_on_front = -10000
            min_wale_on_front = 10000
            max_wale_on_back = -10000
            min_wale_on_back = 10000
            for loop in loop_ids:
                if loop in self.node_on_front_or_back:
                    wale_id = self.node_to_course_and_wale[loop][1]
                    if self.node_on_front_or_back[loop] == 'f':
                        if wale_id > max_wale_on_front:
                            max_wale_on_front = wale_id
                        if wale_id < min_wale_on_front:
                            min_wale_on_front = wale_id
                    elif self.node_on_front_or_back[loop] == 'b':
                        if wale_id > max_wale_on_back:
                            max_wale_on_back = wale_id
                        if wale_id < min_wale_on_back:
                            min_wale_on_back = wale_id
            self.courses_to_min_wale_on_front[course_id] = min_wale_on_front
            self.courses_to_max_wale_on_front[course_id] = max_wale_on_front
            self.courses_to_min_wale_on_back[course_id] = min_wale_on_back
            self.courses_to_max_wale_on_back[course_id] = max_wale_on_back

    def update_min_and_max_wale_id_on_course_on_bed(self, course_id): #this function can't update the wale for those yo or slip nodes.
        for c_id in range(course_id, max([*self.course_to_loop_ids_including_slip.keys()])):
            next_row_loop_ids = self.course_to_loop_ids[c_id]
            for loop_id in next_row_loop_ids:
                self.has_parent_of_0_offset = False
                parent_ids = [*self.graph.predecessors(loop_id)]
                if len(parent_ids) > 0:
                    for parent_id in self.graph.predecessors(loop_id):
                        parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                        wale = self.node_to_course_and_wale[parent_id][1] - parent_offset*self.wale_dist
                        self.node_to_course_and_wale[loop_id] = (c_id, wale)
                        break
        print(f'in update_min_and_max_wale_id_on_course_on_bed, self.node_to_course_and_wale is {self.node_to_course_and_wale}')
        for c_id in range(course_id, max([*self.course_to_loop_ids_including_slip.keys()])):
            print(f'haha c_id is {c_id}, max([*self.course_to_loop_ids_including_slip.keys()]) is {max([*self.course_to_loop_ids_including_slip.keys()])}')
            loop_ids = self.course_to_loop_ids_including_slip[c_id]
        # for course_id, loop_ids in self.course_to_loop_ids_including_slip.items():
            max_wale_on_front = -10000
            min_wale_on_front = 10000
            max_wale_on_back = -10000
            min_wale_on_back = 10000
            for loop in loop_ids:
                if loop in self.node_on_front_or_back:
                    wale_id = self.node_to_course_and_wale[loop][1]
                    if self.node_on_front_or_back[loop] == 'f':
                        if wale_id > max_wale_on_front:
                            max_wale_on_front = wale_id
                        if wale_id < min_wale_on_front:
                            min_wale_on_front = wale_id
                    elif self.node_on_front_or_back[loop] == 'b':
                        if wale_id > max_wale_on_back:
                            max_wale_on_back = wale_id
                        if wale_id < min_wale_on_back:
                            min_wale_on_back = wale_id
            self.courses_to_min_wale_on_front[course_id] = min_wale_on_front
            self.courses_to_max_wale_on_front[course_id] = max_wale_on_front
            self.courses_to_min_wale_on_back[course_id] = min_wale_on_back
            self.courses_to_max_wale_on_back[course_id] = max_wale_on_back
        print(f'updated self.courses_to_min_wale_on_front is {self.courses_to_min_wale_on_front}, updated self.courses_to_max_wale_on_front is {self.courses_to_max_wale_on_front},\
              updated self.courses_to_min_wale_on_back is {self.courses_to_min_wale_on_back}, updated self.courses_to_max_wale_on_back is {self.courses_to_max_wale_on_back}')
    
    def bind_off_final_course(self): #though can be easily generailized to incorporate the bind off symbol in knitspeak
        loop_ids = sorted(self.course_to_loop_ids[max(*self.course_to_loop_ids.keys())])
        for i in range(len(loop_ids) - 1):
            # Retrieve adjacent elements
            loop1 = loop_ids[i]
            loop2 = loop_ids[i + 1]
            loop1_wale = self.node_to_course_and_wale[loop1][1]
            loop2_wale = self.node_to_course_and_wale[loop2][1]
            self.connect_loops(loop1, loop2, parent_offset = int((loop1_wale - loop2_wale)/self.wale_dist), pull_direction = Pull_Direction.BtF, depth = 0)
            

    # def update_wales_to_reduce_float(self):
    #     if self.object_type == 'tube':
    #         count_of_front_half_shift = 0
    #         for course_id in [*self.course_to_loop_ids.keys()][1:]:
    #             if self.courses_to_max_wale_on_back[course_id] > self.courses_to_max_wale_on_front[course_id]:
    #                 for loop_id in self.course_to_loop_ids[course_id]:
    #                     if loop_id in self.loops_on_back_part_of_the_tube:
    #                         #---
    #                         # print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] - (self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id]) - self.wale_dist} to reduce float')
    #                         # self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]-(int((self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id])/self.wale_dist)+1)*self.wale_dist)
    #                         #---
    #                         adjust_wale = self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id] + 1
    #                         print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] - adjust_wale} to reduce float')
    #                         self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]-adjust_wale)
    #                 # self.courses_to_min_wale_on_back[course_id] = self.courses_to_min_wale_on_back[course_id]-(int((self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id])/self.wale_dist)+1)*self.wale_dist
    #                 # self.courses_to_max_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]-(int((self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id])/self.wale_dist)+1)*self.wale_dist
    #                 self.courses_to_min_wale_on_back[course_id] = self.courses_to_min_wale_on_back[course_id]-adjust_wale
    #                 self.courses_to_max_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]-adjust_wale
    #             elif self.courses_to_max_wale_on_back[course_id] < self.courses_to_max_wale_on_front[course_id] - 1:
    #                 for loop_id in self.course_to_loop_ids[course_id]:
    #                     if loop_id in self.loops_on_back_part_of_the_tube:
    #                         # print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] - (self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id]) - self.wale_dist} to reduce float')
    #                         # self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]-(int((self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id])/self.wale_dist)+1)*self.wale_dist)
    #                         adjust_wale = self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id] - 1
    #                         print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] + adjust_wale}')
    #                         self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]+adjust_wale)
    #                 # self.courses_to_min_wale_on_front[course_id] = self.courses_to_min_wale_on_front[course_id]-(int((self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id])/self.wale_dist)+1)*self.wale_dist
    #                 # self.courses_to_max_wale_on_front[course_id] = self.courses_to_max_wale_on_front[course_id]-(int((self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id])/self.wale_dist)+1)*self.wale_dist
    #                 self.courses_to_min_wale_on_back[course_id] = self.courses_to_min_wale_on_back[course_id]+adjust_wale
    #                 self.courses_to_max_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]+adjust_wale
    #         # print(f'after float reduced, self.courses_to_min_wale_on_back is {self.courses_to_min_wale_on_back}, self.courses_to_max_wale_on_back is {self.courses_to_max_wale_on_back}')
    #         # print(f'after float reduced, self.courses_to_min_wale_on_front is {self.courses_to_min_wale_on_front}, self.courses_to_max_wale_on_front is {self.courses_to_max_wale_on_front}')
    #             if course_id+1 in self.courses_to_min_wale_on_front:
    #                 if  self.courses_to_min_wale_on_back[course_id] > self.courses_to_min_wale_on_front[course_id+1]: #+ 1:
    #                     count_of_front_half_shift += 1
    #                     # adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] - 1 if count_of_front_half_shift % 2 == 1 else self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1 - self.wale_dist
    #                     adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1 
    #                     for loop_id in self.course_to_loop_ids[course_id+1]:
    #                         if loop_id in self.loops_on_front_part_of_the_tube:
    #                             print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] + adjust_wale} to reduce float')
    #                             self.node_to_course_and_wale[loop_id] = (course_id+1, self.node_to_course_and_wale[loop_id][1] + adjust_wale)
    #                     self.courses_to_max_wale_on_front[course_id+1] = self.courses_to_max_wale_on_front[course_id+1] + adjust_wale
    #                     self.courses_to_min_wale_on_front[course_id+1] = self.courses_to_min_wale_on_front[course_id+1] + adjust_wale
    #                 elif self.courses_to_min_wale_on_back[course_id] < self.courses_to_min_wale_on_front[course_id+1] - 1:
    #                     # adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] - 1 if count_of_front_half_shift % 2 == 1 else self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1 - self.wale_dist
    #                     adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1
    #                     for loop_id in self.course_to_loop_ids[course_id+1]:
    #                         if loop_id in self.loops_on_front_part_of_the_tube:
    #                             print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] + adjust_wale} to reduce float')
    #                             self.node_to_course_and_wale[loop_id] = (course_id+1, self.node_to_course_and_wale[loop_id][1] + adjust_wale)
    #                     self.courses_to_max_wale_on_front[course_id+1] = self.courses_to_max_wale_on_front[course_id+1] + adjust_wale
    #                     self.courses_to_min_wale_on_front[course_id+1] = self.courses_to_min_wale_on_front[course_id+1] + adjust_wale
    
                
    #version 2 
    def update_wales_to_reduce_float(self):
        print(f'in update_wales_to_reduce_float(), before update, self.node_to_course_and_wale is {self.node_to_course_and_wale}')
        if self.object_type == 'tube':
            count_of_front_half_shift = 0
            for course_id in [*self.course_to_loop_ids.keys()][1:]:
                if self.courses_to_max_wale_on_back[course_id] > self.courses_to_max_wale_on_front[course_id]:
                    for loop_id in self.course_to_loop_ids[course_id]:
                        if loop_id in self.loops_on_back_part_of_the_tube:
                            #---
                            # print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] - (self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id]) - self.wale_dist} to reduce float')
                            # self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]-(int((self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id])/self.wale_dist)+1)*self.wale_dist)
                            #---
                            adjust_wale = self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id] + 1
                            print(f'c1: course id is {course_id}, loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] - adjust_wale} to reduce float')
                            self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]-adjust_wale)
                    # self.courses_to_min_wale_on_back[course_id] = self.courses_to_min_wale_on_back[course_id]-(int((self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id])/self.wale_dist)+1)*self.wale_dist
                    # self.courses_to_max_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]-(int((self.courses_to_max_wale_on_back[course_id] - self.courses_to_max_wale_on_front[course_id])/self.wale_dist)+1)*self.wale_dist
                    self.courses_to_min_wale_on_back[course_id] = self.courses_to_min_wale_on_back[course_id]-adjust_wale
                    self.courses_to_max_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]-adjust_wale
                elif self.courses_to_max_wale_on_back[course_id] < self.courses_to_max_wale_on_front[course_id] - 1:
                    print(f'c2:self.courses_to_max_wale_on_back[course_id] is {self.courses_to_max_wale_on_back[course_id]}, self.courses_to_max_wale_on_front[course_id] is {self.courses_to_max_wale_on_front[course_id]}')
                    print(f'c2: self.course_to_loop_ids[course_id] is {self.course_to_loop_ids[course_id]}')
                    for loop_id in self.course_to_loop_ids[course_id]:
                        if loop_id in self.loops_on_back_part_of_the_tube:
                            # print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] - (self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id]) - self.wale_dist} to reduce float')
                            # self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]-(int((self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id])/self.wale_dist)+1)*self.wale_dist)
                            adjust_wale = self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id] - 1
                            print(f'c2: course id is {course_id}, loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] + adjust_wale}')
                            self.node_to_course_and_wale[loop_id] = (course_id, self.node_to_course_and_wale[loop_id][1]+adjust_wale)
                    # self.courses_to_min_wale_on_front[course_id] = self.courses_to_min_wale_on_front[course_id]-(int((self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id])/self.wale_dist)+1)*self.wale_dist
                    # self.courses_to_max_wale_on_front[course_id] = self.courses_to_max_wale_on_front[course_id]-(int((self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_back[course_id])/self.wale_dist)+1)*self.wale_dist
                    self.courses_to_min_wale_on_back[course_id] = self.courses_to_min_wale_on_back[course_id]+adjust_wale
                    self.courses_to_max_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]+adjust_wale
            # print(f'after float reduced, self.courses_to_min_wale_on_back is {self.courses_to_min_wale_on_back}, self.courses_to_max_wale_on_back is {self.courses_to_max_wale_on_back}')
            # print(f'after float reduced, self.courses_to_min_wale_on_front is {self.courses_to_min_wale_on_front}, self.courses_to_max_wale_on_front is {self.courses_to_max_wale_on_front}')
                # if course_id+1 in self.courses_to_min_wale_on_front:
                    # if  self.courses_to_min_wale_on_back[course_id] > self.courses_to_min_wale_on_front[course_id+1]: #+ 1:
                    #     count_of_front_half_shift += 1
                    #     # adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] - 1 if count_of_front_half_shift % 2 == 1 else self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1 - self.wale_dist
                    #     adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1 
                    #     for loop_id in self.course_to_loop_ids[course_id+1]:
                    #         if loop_id in self.loops_on_front_part_of_the_tube:
                    #             print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] + adjust_wale} to reduce float')
                    #             self.node_to_course_and_wale[loop_id] = (course_id+1, self.node_to_course_and_wale[loop_id][1] + adjust_wale)
                    #     self.courses_to_max_wale_on_front[course_id+1] = self.courses_to_max_wale_on_front[course_id+1] + adjust_wale
                    #     self.courses_to_min_wale_on_front[course_id+1] = self.courses_to_min_wale_on_front[course_id+1] + adjust_wale
                    # elif self.courses_to_min_wale_on_back[course_id] < self.courses_to_min_wale_on_front[course_id+1] - 1:
                    #     # adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] - 1 if count_of_front_half_shift % 2 == 1 else self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1 - self.wale_dist
                    #     adjust_wale = self.courses_to_min_wale_on_back[course_id] - self.courses_to_min_wale_on_front[course_id+1] + 1
                    #     for loop_id in self.course_to_loop_ids[course_id+1]:
                    #         if loop_id in self.loops_on_front_part_of_the_tube:
                    #             print(f'loop id {loop_id} has wale updated from {self.node_to_course_and_wale[loop_id][1]} to {self.node_to_course_and_wale[loop_id][1] + adjust_wale} to reduce float')
                    #             self.node_to_course_and_wale[loop_id] = (course_id+1, self.node_to_course_and_wale[loop_id][1] + adjust_wale)
                    #     self.courses_to_max_wale_on_front[course_id+1] = self.courses_to_max_wale_on_front[course_id+1] + adjust_wale
                    #     self.courses_to_min_wale_on_front[course_id+1] = self.courses_to_min_wale_on_front[course_id+1] + adjust_wale

                #----move loops from one bed to another if the number of loops on both beds are not equal
                n_f = len(self.course_to_loops_on_front_part_of_the_tube[course_id])
                n_b = len(self.course_to_loops_on_back_part_of_the_tube[course_id])
                print(f'course_id is {course_id}, self.course_to_loops_on_front_part_of_the_tube is {self.course_to_loops_on_front_part_of_the_tube},\
                      self.course_to_loops_on_back_part_of_the_tube[course_id] is {self.course_to_loops_on_back_part_of_the_tube[course_id]}, n_b is {n_b}, n_f is {n_f}')
                if self.course_to_row[course_id] == False: #if this course is a round
                    if n_b > n_f+1:
                        num_loops_on_one_bed = int((n_b+n_f)/2)
                        right_end_wale_front = self.loop_ids_to_wale[self.course_to_loop_ids[course_id][0]] #c is course id 
                        for i in range(n_b-num_loops_on_one_bed): #the number of loops that should be moved to the other bed
                            loop = self.course_to_loop_ids[course_id][-1-i]
                            wale = right_end_wale_front-self.wale_dist
                            right_end_wale_front = wale
                            self.loop_ids_to_wale[loop] = wale
                            self.node_to_course_and_wale[loop] = (course_id, wale)
                            self.node_on_front_or_back[loop] = 'f'
                            # self.course_to_loops_on_back_part_of_the_tube[course_id].remove(loop)
                            # self.course_to_loops_on_front_part_of_the_tube[course_id].append(loop)
                        # self.courses_to_min_wale_on_back[course_id] = self.courses_to_max_wale_on_back[course_id]-self.wale_dist*(n_b-num_loops_on_one_bed)
                        # self.courses_to_min_wale_on_front[course_id] = wale

                    elif n_b < n_f - 1:
                        num_loops_on_one_bed = int((n_b+n_f)/2)
                        for back_loop in self.course_to_loops_on_back_part_of_the_tube[course_id]:
                            wale = self.node_to_course_and_wale[back_loop][1] - self.wale_dist*((n_f - num_loops_on_one_bed)*2)
                            print(f'back loop is {back_loop}, self.node_to_course_and_wale[back_loop][1] is {self.node_to_course_and_wale[back_loop][1]}, new wale is {wale}')
                            self.loop_ids_to_wale[back_loop] = wale
                            self.node_to_course_and_wale[back_loop] = (course_id, wale)
                        print(f'self.node_to_course_and_wale is {self.node_to_course_and_wale}, self.course_to_loops_on_back_part_of_the_tube[course_id] is {self.course_to_loops_on_back_part_of_the_tube[course_id]}')
                        left_end_wale_back = self.node_to_course_and_wale[min(self.course_to_loops_on_back_part_of_the_tube[course_id])][1]
                        print(f'left_end_wale_back is {left_end_wale_back}')
                        for i in range(n_f - num_loops_on_one_bed):
                            loop = self.course_to_loops_on_front_part_of_the_tube[course_id][-1-i]
                            print(f'loop on front that is moved to back is {loop}')
                            wale = left_end_wale_back+self.wale_dist
                            left_end_wale_back = wale
                            print(f'its wale now becomes {wale}')
                            self.loop_ids_to_wale[loop] = wale
                            self.node_to_course_and_wale[loop] = (course_id, wale)
                            self.node_on_front_or_back[loop] = 'b'
                            # self.course_to_loops_on_front_part_of_the_tube[course_id].remove(loop)
                            # self.course_to_loops_on_back_part_of_the_tube[course_id].append(loop)
                #         self.courses_to_max_wale_on_back[course_id] = wale
                #         self.courses_to_max_wale_on_front[course_id] = self.courses_to_max_wale_on_front[course_id]-(n_f - num_loops_on_one_bed)*self.wale_dist
                #         print(f'self.courses_to_max_wale_on_back[course_id] becomes {self.courses_to_max_wale_on_back[course_id]}, \
                #               self.courses_to_max_wale_on_front[course_id] is {self.courses_to_max_wale_on_front[course_id]}')
                # self.update_min_and_max_wale_id_on_course_on_bed(course_id)
                #------
        print(f'in update_wales_to_reduce_float(), self.node_to_course_and_wale is {self.node_to_course_and_wale}')

    def adjust_overall_slanting(self):
        #now that the float has been reduced, we need to adjust the overall slanting to ensure the knitgraph is not overly slanting towards 
        #either left or right side so that the racking needed will not exceed the racking bound inherent to our knitting machine.
        if self.object_type == 'tube':
            #temp1: start to account for right edge stitch on the back bed
            for course_id in [*self.course_to_loop_ids.keys()]:
                if (course_id+1) in self.course_to_loop_ids:
                    if (self.courses_to_min_wale_on_back[course_id+1] - self.courses_to_min_wale_on_back[course_id]) > self.wale_dist*2: #since racking bound is 4
                        wale_to_shift = self.wale_dist
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
                            self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] - wale_to_shift
            #consider left edge stitches (max wale) of front
            for course_id in [*self.course_to_loop_ids.keys()]:
                if (course_id+1) in self.course_to_loop_ids:
                    if abs(self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_front[course_id+1]) > self.wale_dist: #since racking bound is 4
                        print(f'self.courses_to_max_wale_on_front[course_id] is {self.courses_to_max_wale_on_front[course_id]},\
                               self.courses_to_max_wale_on_front[course_id+1]) is {self.courses_to_max_wale_on_front[course_id+1]},\
                              self.wale_dist is {self.wale_dist}')
                        wale_to_shift = self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_front[course_id+1]  #- 4
                        wale_to_shift = wale_to_shift + self.wale_dist if wale_to_shift > 0 else wale_to_shift - self.wale_dist
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            print(f'course_id+1 is {course_id+1}, next_course_id is {next_course_id}')
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                print(f'233-1 self.node_to_course_and_wale[loop_id][1] is {self.node_to_course_and_wale[loop_id][1]}, wale_to_shift is {wale_to_shift}, actual shift is {int(int(wale_to_shift/self.wale_dist)/2)*self.wale_dist}')
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] + int(int(wale_to_shift/self.wale_dist)/2)*self.wale_dist) #ori int(wale_to_shift/self.wale_dist/2)*self.wale_dist)
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] + int(int(wale_to_shift/self.wale_dist)/2)*self.wale_dist
                            self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] + int(int(wale_to_shift/self.wale_dist)/2)*self.wale_dist
                            self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] + int(int(wale_to_shift/self.wale_dist)/2)*self.wale_dist
                            self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] + int(int(wale_to_shift/self.wale_dist)/2)*self.wale_dist
            # consider right edge stitches (min wale) of front
            for course_id in [*self.course_to_loop_ids.keys()]:
                if (course_id+1) in self.course_to_loop_ids:
                    # if abs(self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) >= self.wale_dist*2: #since racking bound is 4
                    if abs(self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) > self.wale_dist*2: #since racking bound is 4
                        wale_to_shift = self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id] #- 4
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                print(f'233-2 self.node_to_course_and_wale[loop_id][1] is {self.node_to_course_and_wale[loop_id][1]}, wale_to_shift is {wale_to_shift}')
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - int(wale_to_shift/self.wale_dist/2)*self.wale_dist) 
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - int(wale_to_shift/self.wale_dist/2)*self.wale_dist
                            self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] - int(wale_to_shift/self.wale_dist/2)*self.wale_dist
                            self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - int(wale_to_shift/self.wale_dist/2)*self.wale_dist
                            self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] - int(wale_to_shift/self.wale_dist/2)*self.wale_dist
            # consider if max wale and min wale of front of the above course is all less or bigger than the current course 
            for course_id in [*self.course_to_loop_ids.keys()]:
                if (course_id+1) in self.course_to_loop_ids:
                    if (self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id])*(self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id])>0: #since racking bound is 4
                        if self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id] == self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id]:
                            wale_to_shift = self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]
                            for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                                for loop_id in self.course_to_loop_ids[next_course_id]:
                                    self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
                                    # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                                self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
                                self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] - wale_to_shift
                                self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
                                self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] - wale_to_shift
            # #temp1: start to account for edge stitch on the back bed (move to the first block above)
            # for course_id in [*self.course_to_loop_ids.keys()]:
            #     if (course_id+1) in self.course_to_loop_ids:
            #         if (self.courses_to_min_wale_on_back[course_id+1] - self.courses_to_min_wale_on_back[course_id]) > self.wale_dist*2: #since racking bound is 4
            #             wale_to_shift = self.wale_dist
            #             for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
            #                 for loop_id in self.course_to_loop_ids[next_course_id]:
            #                     self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
            #                     # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
            #                 self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
            #                 self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] - wale_to_shift
            #                 self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
            #                 self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] - wale_to_shift
            # temp2: if one max wale is the same but the other edge is exceeding the slanting limit 
            # (note: this neglects the case when min wale is the same while max wale difference exceeds the racking bound, we will add it later)
            for course_id in [*self.course_to_loop_ids.keys()]:
                if (course_id+1) in self.course_to_loop_ids:
                    if (self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id])== 0 and (self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) >= self.wale_dist*2: #since racking bound is 4
                        # if self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id] == self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id]:
                        wale_to_shift = self.wale_dist
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
                            self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] - wale_to_shift
        
        #-------work for sheet
        # if self.object_type == 'sheet':
        #     for course_id in [*self.course_to_loop_ids.keys()]:
        #         if (course_id+1) in self.course_to_loop_ids:
        #             if abs(self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) > self.wale_dist: #since racking bound is 4
        #                 offset = (self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) 
        #                 wale_to_shift = int(offset/(2)) 
        #                 print(f'course id is {course_id}, wale_to_shift is {wale_to_shift}')
        #                 for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
        #                     for loop_id in self.course_to_loop_ids[next_course_id]:
        #                         self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
        #                         # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
        #                     self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
        #                     self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
        #             elif abs(self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id]) > self.wale_dist: #since racking bound is 4
        #                 offset = (self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id]) 
        #                 wale_to_shift = int(offset/(2)) 
        #                 print(f'course id is {course_id}, wale_to_shift is {wale_to_shift}')
        #                 for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
        #                     for loop_id in self.course_to_loop_ids[next_course_id]:
        #                         self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
        #                         # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
        #                     self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
        #                     self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
        #------
                            
        print(f'self.course_to_row is {self.course_to_row}')
        # Initialize the minimum key to None
        min_row_id = None
        row_ids = []
        # Iterate over the dictionary
        for key, value in self.course_to_row.items():
            # Check if the value is True and update the minimum key accordingly
            if value:
                row_ids.append(key)
       
                # for course_id in [*self.course_to_loop_ids.keys()]:
                    # if (course_id+1) in self.course_to_loop_ids:
        if len(row_ids) != 0:
            min_row_id = min(row_ids)
            course_id = min_row_id-1
            print(f'in min_row_id, course id is {course_id}')
            for course_id in [*self.course_to_loop_ids.keys()][course_id:]:
                if (course_id+1) in self.course_to_loop_ids:
                    if abs(self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) > self.wale_dist: #since racking bound is 4
                        offset = (self.courses_to_min_wale_on_front[course_id+1] - self.courses_to_min_wale_on_front[course_id]) 
                        wale_to_shift = int(offset/(2)) 
                        print(f'course id is {course_id}, wale_to_shift is {wale_to_shift}')
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
                    elif abs(self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id]) > self.wale_dist: #since racking bound is 4
                        offset = (self.courses_to_max_wale_on_front[course_id+1] - self.courses_to_max_wale_on_front[course_id]) 
                        wale_to_shift = int(offset/(2)) 
                        print(f'course id is {course_id}, wale_to_shift is {wale_to_shift}')
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_front[next_course_id] = self.courses_to_max_wale_on_front[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_front[next_course_id] = self.courses_to_min_wale_on_front[next_course_id] - wale_to_shift
                    elif abs(self.courses_to_min_wale_on_back[course_id+1] - self.courses_to_min_wale_on_back[course_id]) > self.wale_dist:
                        offset = (self.courses_to_min_wale_on_back[course_id+1] - self.courses_to_min_wale_on_back[course_id]) 
                        wale_to_shift = int(offset/(2)) 
                        print(f'course id is {course_id}, wale_to_shift is {wale_to_shift}')
                        for next_course_id in [*self.course_to_loop_ids.keys()][course_id+1:]:
                            for loop_id in self.course_to_loop_ids[next_course_id]:
                                self.node_to_course_and_wale[loop_id] = (next_course_id, self.node_to_course_and_wale[loop_id][1] - wale_to_shift) 
                                # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
                            self.courses_to_max_wale_on_back[next_course_id] = self.courses_to_max_wale_on_back[next_course_id] - wale_to_shift
                            self.courses_to_min_wale_on_back[next_course_id] = self.courses_to_min_wale_on_back[next_course_id] - wale_to_shift

                        
    
    # @back up version 
    # def adjust_overall_slanting(self):
    #     #now that the float has been reduced, we need to adjust the overall slanting to ensure the knitgraph is not overly slanting towards 
    #     #either left or right side so that the racking needed will not exceed the racking bound inherent to our knitting machine.
    #     for course_id in [*self.course_to_loop_ids.keys()]:
    #         if (course_id+1) in self.course_to_loop_ids:
    #             if abs(self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_front[course_id+1]) >= self.wale_dist: #since racking bound is 4
    #                 wale_to_shift = self.courses_to_max_wale_on_front[course_id] - self.courses_to_max_wale_on_front[course_id+1] #- 4
    #                 for loop_id in self.course_to_loop_ids[course_id+1]:
    #                     print(f'233 self.node_to_course_and_wale[loop_id][1] is {self.node_to_course_and_wale[loop_id][1]}, wale_to_shift is {wale_to_shift}')
    #                     self.node_to_course_and_wale[loop_id] = (course_id+1, self.node_to_course_and_wale[loop_id][1] + int(wale_to_shift/self.wale_dist/2+1)*self.wale_dist) 
    #                     # self.node_to_course_and_wale[loop_id] = course_id+1, self.node_to_course_and_wale[loop_id][1] + wale_to_shift 
    #                 self.courses_to_max_wale_on_front[course_id+1] = self.courses_to_max_wale_on_front[course_id+1] + int(wale_to_shift/self.wale_dist/2+1)*self.wale_dist
    #                 self.courses_to_max_wale_on_back[course_id+1] = self.courses_to_max_wale_on_back[course_id+1] + int(wale_to_shift/self.wale_dist/2+1)*self.wale_dist
    #                 self.courses_to_min_wale_on_front[course_id+1] = self.courses_to_min_wale_on_front[course_id+1] + int(wale_to_shift/self.wale_dist/2+1)*self.wale_dist
    #                 self.courses_to_min_wale_on_back[course_id+1] = self.courses_to_min_wale_on_back[course_id+1] + int(wale_to_shift/self.wale_dist/2+1)*self.wale_dist

    def get_course_and_wale_and_bed_to_node(self):
        if self.object_type == 'tube':
            for node in self.node_on_front_or_back.keys():
                course_and_wale = self.node_to_course_and_wale[node]
                front_or_back = self.node_on_front_or_back[node]
                self.course_and_wale_and_bed_to_node[(course_and_wale, front_or_back)] = node
            return self.course_and_wale_and_bed_to_node

    def update_parent_offsets(self):  
        """
        update it to make all stitches consistent with the view -- comply with the only wale advancing direction, rather than the alternating yarn walking direction.
        We do this to avoid wrong parent-offset extracted in knitout interpreter, which would lead to failed conversion.
        """
        for loop_id in self.graph.nodes:
            parent_loops = [*self.graph.predecessors(loop_id)]
            if len(parent_loops) != 0:
                for parent_id in self.graph.predecessors(loop_id):
                    parent_offset = self.graph[parent_id][loop_id]['parent_offset']
                    #----
                    # if parent_offset != 0:
                    #     # print(f'loop id is {loop_id}, parent id is {parent_id}, original parent offset is {parent_offset}')
                    #     # we deprecated this because the actual wale_id we use to visualize graph is self.node_to_course_and_wale rather than self.loop_ids_to_wale.
                    #     # self.graph[parent_id][loop_id]['parent_offset'] =  int((self.loop_ids_to_wale[parent_id] - self.loop_ids_to_wale[loop_id])/self.wale_dist)
                    #     # print(f'wale of parent id {parent_id} is {self.loop_ids_to_wale[parent_id]}, wale of loop id {loop_id} is {self.loop_ids_to_wale[loop_id]}')
                    #     # self.graph[parent_id][loop_id]['parent_offset'] =  int((self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[loop_id][1])/self.wale_dist)
                    #     # above is deprecated because it does not work for stitch like point from b2 to f1.
                    #     updated_parent_offset = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[loop_id][1])/self.wale_dist
                    #     if parent_offset != updated_parent_offset:
                    #         print(f'offset update for loop id is {loop_id}! parent id is {parent_id}, original parent offset is {parent_offset}, updated parent offset is {updated_parent_offset}')
                    #     self.graph[parent_id][loop_id]['parent_offset'] = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[loop_id][1])/self.wale_dist
                    #     # print(f'wale of parent id {parent_id} is {self.node_to_course_and_wale[parent_id][1]}, wale of loop id {loop_id} is {self.node_to_course_and_wale[loop_id][1]}')
                    #----
                    updated_parent_offset = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[loop_id][1])/self.wale_dist
                    if parent_offset != updated_parent_offset:
                        print(f'offset update for loop id is {loop_id}! parent id is {parent_id}, parent wale is {self.node_to_course_and_wale[parent_id][1]}, \
                              loop wale is {self.node_to_course_and_wale[loop_id][1]}, original parent offset is {parent_offset}, updated parent offset is {updated_parent_offset}')
                    self.graph[parent_id][loop_id]['parent_offset'] = (self.node_to_course_and_wale[parent_id][1] - self.node_to_course_and_wale[loop_id][1])/self.wale_dist

    def get_carriers(self) -> List[Yarn_Carrier]:
        """
        :return: A list of yarn carriers that hold the yarns involved in this graph
        """
        return [yarn.carrier for yarn in self.yarns.values()]

    def __contains__(self, item):
        """
        :param item: the loop being checked for in the graph
        :return: true if the loop_id of item or the loop is in the graph
        """
        if type(item) is int:
            return self.graph.has_node(item)
        elif isinstance(item, Loop):
            return self.graph.has_node(item.loop_id)
        else:
            return False

    def __getitem__(self, item: int) -> Loop:
        """
        :param item: the loop_id being checked for in the graph
        :return: the Loop in the graph with the matching id
        """
        if item not in self:
            raise AttributeError
        else:
            return self.graph.nodes[item]["loop"]

