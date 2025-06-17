"""Script used to create knitout instructions from a knitgraph"""
from turtle import position
from typing import Dict, List, Optional, Tuple, Union
from knit_graphs.Knit_Graph import Knit_Graph, Pull_Direction
from knitting_machine.Machine_State import Machine_State, Needle, Pass_Direction, Yarn_Carrier
from knitting_machine.machine_operations import outhook
from knitting_machine.new_operation_sets import Carriage_Pass, Instruction_Type, Instruction_Parameters


class Knitout_Generator:
    """
    A class that is used to generate a single yarn knit-graph
    """

    def __init__(self, knit_graph: Knit_Graph):
        """
        :param knit_graph: the knitgraph used to generate instructions 
        :param node_to_course_and_wale: only applicable to tube 
        :param course_and_wale_and_bed_to_node: only applicable to tube 
        """
        self._knit_graph = knit_graph
        self.object_type: str = knit_graph.object_type
        self.gauge: float = knit_graph.gauge 
        self.wale_dist = int(1/self.gauge)
        # print(f'self.wale_dist is {self.wale_dist}')
        # self._carrier_set = [yarn.carrier for yarn in [*self._knit_graph.yarns.values()]]
        self._carrier_set = list(set([yarn.carrier for yarn in [*self._knit_graph.yarns.values()]]))
        # print('self._carrier_set', self._carrier_set, type(self._carrier_set))
        self.yarns = [*self._knit_graph.yarns.values()]
        self.old_courses_to_loop_id = knit_graph.course_to_loop_ids
        self.old_loop_id_to_courses = knit_graph.loop_ids_to_course
        self.already_used = False
        self._loop_id_to_courses, self._courses_to_loop_ids = knit_graph.get_courses()
        print(f'self._courses_to_loop_ids in knitout interpreter is {self._courses_to_loop_ids}')
        # because we have used bind-off to secure the bottom loops that has no child, so we actually updated the course_to_loop_ids by bind-off,
        # thus we need to get new one by invoke .get_courses().
        self.node_to_course_and_wale: Dict[int, Tuple[int, int]] = knit_graph.node_to_course_and_wale
        self.course_and_wale_to_node: Dict[Tuple[int, int], int] = {tuple(v): k for k, v in knit_graph.node_to_course_and_wale.items()}
        self.node_on_front_or_back = knit_graph.node_on_front_or_back

        # get the min wale and max wale of the whole knitgraph, which is used for guiding cast-on of new yarns
        # print(f'self.node_to_course_and_wale in knitout is {self.node_to_course_and_wale}')
        self.min_wale = min(self.node_to_course_and_wale.values(), key=lambda x: x[1])[1]
        self.max_wale = max(self.node_to_course_and_wale.values(), key=lambda x: x[1])[1]
        # 
        self.loop_id_to_carrier_id: Dict[int, int] = {}
        self.loop_id_to_carrier: Dict[int, Yarn_Carrier] = {}
        self.first_course_in_to_carrier: Dict[int, List[Yarn_Carrier]] = {}
        self.get_nodes_carrier_id()
        self.get_first_course_id_of_yarns_in()
        # 
        self.courses_to_min_wale_on_front: Dict[int, int] = {}
        self.courses_to_min_wale_on_back: Dict[int, int] = {}
        self.courses_to_max_wale_on_front: Dict[int, int] = {}
        self.courses_to_max_wale_on_back: Dict[int, int] = {}
        self.get_min_and_max_wale_id_on_course_on_bed()
        # 
        self.loop_id_to_knit_dir :Dict[int, str] = {}
        self.get_loop_id_to_knit_dir()
        # 
        self.carrier_to_first_dir: Dict[Yarn_Carrier, str] = {}
        self.get_carrier_to_first_dir()
        # 
        self.sort_passes_by_dir_per_course()
        # 
        self._sorted_courses = sorted([*self._courses_to_loop_ids.keys()])
        self._machine_state: Machine_State = Machine_State()
        self._carriage_passes: List[Carriage_Pass] = []
        self._instructions: List[str] = []
        self.nodes_on_patch_side: List[int] = []
        self.loop_ids_on_final_course_parent_knitgraph: Dict[int, List[int]] = {}
        self.final_course_parent_knitgraph: int = 0


    #get node carrier_id
    def get_nodes_carrier_id(self):
        for node in self._knit_graph.graph.nodes:
            #find carrier_id of the node
            #first identify the yarn of the node
            for yarn in self.yarns:
                if node in yarn:
                    carrier = yarn.carrier
                    carrier_id = yarn.carrier.carrier_ids
                    break
            #store node color property
            self.loop_id_to_carrier_id[node] = carrier_id
            self.loop_id_to_carrier[node] = carrier
        # print('self.loop_id_to_carrier_id', self.loop_id_to_carrier_id)
    
    def get_first_course_id_of_yarns_in(self):
        for yarn in self.yarns:
            yarn_nodes = yarn.yarn_graph.nodes
            first_yarn_node = min(yarn_nodes)
            print(f'in interpreter, yarn is {yarn}, first_yarn_node is {first_yarn_node}')
            course_id = self._loop_id_to_courses[first_yarn_node]
            carrier = yarn.carrier
            if course_id not in self.first_course_in_to_carrier:
                self.first_course_in_to_carrier[course_id] = [carrier]
            else:
                self.first_course_in_to_carrier[course_id].append(carrier)
        # print('self.first_course_in_to_carrier', self.first_course_in_to_carrier)

    # only needed for tube
    def get_min_and_max_wale_id_on_course_on_bed(self):
        # if self.object_type == 'tube':
        # print(f'self.node_to_course_and_wale in knitout is {self.node_to_course_and_wale}, len is {len(self.node_to_course_and_wale)}')
        for course_id, loop_ids in self._courses_to_loop_ids.items():
        # for course_id, loop_ids in self.old_courses_to_loop_id.items():
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
        # print(f'self.courses_to_min_wale_on_front is {self.courses_to_min_wale_on_front}, self.courses_to_max_wale_on_front is {self.courses_to_max_wale_on_front},\
        # self.courses_to_min_wale_on_back is {self.courses_to_min_wale_on_back}, self.courses_to_max_wale_on_back is {self.courses_to_max_wale_on_back}')

    def get_loop_id_to_knit_dir(self):
        # ****logic below is based on the assumption that the yarn walking direction of given knit_graph starts from left to right. so we would
        # need to revert the derived self.loop_id_to_knit_dir if the knit_graph starts from right to left. ****
        if self.object_type == 'tube':
            print(f'yarn.yarn_graph.nodes in Knitout interpreter is {self.yarns[0].yarn_graph.nodes}, self._knit_graph.graph.nodes is {self._knit_graph.graph.nodes}')
            for yarn in self.yarns:
                if len(yarn.yarn_graph.nodes) > 1: # that means this yarn will have at least one yarn edge.
                    for edges in yarn.yarn_graph.edges:
                        # print(f'yay edges is {edges}') #(0, 1), (1, 2), ...
                        prior_loop = edges[0]
                        next_loop = edges[1]
                        current_bed = self.node_on_front_or_back[prior_loop]
                        current_wale_id = self.node_to_course_and_wale[prior_loop][1]
                        next_bed = self.node_on_front_or_back[next_loop]
                        next_wale_id = self.node_to_course_and_wale[next_loop][1]
                        prior_loop_course_id = self._loop_id_to_courses[prior_loop]
                        if next_bed == current_bed:
                            if next_wale_id - current_wale_id > 0:
                                dir = '+'
                                if prior_loop not in self.loop_id_to_knit_dir.keys():
                                    self.loop_id_to_knit_dir[prior_loop] = dir
                                self.loop_id_to_knit_dir[next_loop] = dir
                            elif next_wale_id - current_wale_id < 0:
                                dir = '-'
                                if prior_loop not in self.loop_id_to_knit_dir.keys():
                                    self.loop_id_to_knit_dir[prior_loop] = dir
                                self.loop_id_to_knit_dir[next_loop] = dir
                            else:
                                # in this case, we would need the third node to help the dir.
                                if prior_loop in self.loop_id_to_knit_dir.keys():
                                    if len([*yarn.yarn_graph.successors(next_loop)]) > 0:
                                        the_third_loop =  [*yarn.yarn_graph.successors(next_loop)][0]
                                        if self.node_on_front_or_back[next_loop] == self.node_on_front_or_back[the_third_loop]:
                                            if self.node_to_course_and_wale[next_loop][1] < self.node_to_course_and_wale[the_third_loop][1]:
                                                dir = '+'
                                            elif self.node_to_course_and_wale[next_loop][1] > self.node_to_course_and_wale[the_third_loop][1]:
                                                dir = '-'
                                        else:
                                            next_loop_course_id = self._loop_id_to_courses[next_loop]
                                            if self.node_to_course_and_wale[next_loop][1] == self.courses_to_min_wale_on_front[next_loop_course_id] or \
                                                self.node_to_course_and_wale[next_loop][1] == self.courses_to_min_wale_on_back[next_loop_course_id]:
                                                dir = '-'
                                            elif self.node_to_course_and_wale[next_loop][1] == self.courses_to_max_wale_on_front[next_loop_course_id] or \
                                                self.node_to_course_and_wale[next_loop][1] == self.courses_to_max_wale_on_back[next_loop_course_id]:
                                                dir = '+'
                                    else:
                                        dir = self.loop_id_to_knit_dir[prior_loop]
                                        dir = '+' if dir == '-' else '-'
                                    self.loop_id_to_knit_dir[next_loop] = dir
                                else:
                                    self.loop_id_to_knit_dir[prior_loop] = '-' #bc first in dir is '-' on the machine
                                    self.loop_id_to_knit_dir[next_loop] = '+'  
                        elif next_bed != current_bed:
                            if prior_loop in self.loop_id_to_knit_dir.keys():
                                dir = self.loop_id_to_knit_dir[prior_loop]
                                dir = '+' if dir == '-' else '-'
                                self.loop_id_to_knit_dir[next_loop] = dir
                            else: 
                                if (self.node_on_front_or_back[prior_loop] == 'f' and self.node_to_course_and_wale[prior_loop][1] == self.courses_to_max_wale_on_front[prior_loop_course_id]) \
                                    or (self.node_on_front_or_back[prior_loop] == 'b' and self.node_to_course_and_wale[prior_loop][1] == self.courses_to_max_wale_on_back[prior_loop_course_id]):
                                    dir = '+'
                                    self.loop_id_to_knit_dir[prior_loop] = dir
                                    #dir = '+' if dir == '-' else '-'
                                    #self.loop_id_to_knit_dir[next_loop] = dir
                                    self.loop_id_to_knit_dir[next_loop] = '-'
                                elif (self.node_on_front_or_back[prior_loop] == 'b' and self.node_to_course_and_wale[prior_loop][1] == self.courses_to_min_wale_on_back[prior_loop_course_id]) \
                                    or (self.node_on_front_or_back[prior_loop] == 'f' and self.node_to_course_and_wale[prior_loop][1] == self.courses_to_min_wale_on_front[prior_loop_course_id]):
                                    dir = '-'
                                    self.loop_id_to_knit_dir[prior_loop] = dir
                                    # dir = '+' if dir == '-' else '-'
                                    # self.loop_id_to_knit_dir[next_loop] = dir
                                    self.loop_id_to_knit_dir[next_loop] = '+'
                else:
                    node = [*yarn.yarn_graph.nodes][0]
                    dir = '-' #(the direction that the carrier first comes in)
                    self.loop_id_to_knit_dir[node] = dir
        elif self.object_type == 'sheet':
            for yarn in self.yarns:
                if len(yarn.yarn_graph.nodes) > 1: # that means this yarn will have at least one yarn edge.
                    for edges in yarn.yarn_graph.edges:
                        # print(f'yay edges is {edges}') #(0, 1), (1, 2), ...
                        prior_loop = edges[0]
                        next_loop = edges[1]
                        current_wale_id = self.node_to_course_and_wale[prior_loop][1]
                        next_wale_id = self.node_to_course_and_wale[next_loop][1]
                        if next_wale_id - current_wale_id > 0:
                            dir = '+'
                            if prior_loop not in self.loop_id_to_knit_dir.keys():
                                self.loop_id_to_knit_dir[prior_loop] = dir
                            self.loop_id_to_knit_dir[next_loop] = dir
                
                        elif next_wale_id - current_wale_id < 0:
                            dir = '-'
                            if prior_loop not in self.loop_id_to_knit_dir.keys():
                                self.loop_id_to_knit_dir[prior_loop] = dir
                            self.loop_id_to_knit_dir[next_loop] = dir
             
                        elif next_wale_id - current_wale_id == 0:
                            if prior_loop in self.loop_id_to_knit_dir.keys():
                                dir = self.loop_id_to_knit_dir[prior_loop]
                                dir = '+' if dir == '-' else '-'
                                self.loop_id_to_knit_dir[next_loop] = dir
                            else:
                                self.loop_id_to_knit_dir[prior_loop] = '-'
                                self.loop_id_to_knit_dir[next_loop] = '+'     
                else:
                    node = [*yarn.yarn_graph.nodes][0]
                    dir = '-' #(the direction that the carrier first comes in)
                    self.loop_id_to_knit_dir[node] = dir
        # revert if yarn start from 'right to left'.
        if self._knit_graph.yarn_start_direction == 'right to left':
            for loop_id in self.loop_id_to_knit_dir:
                dir = self.loop_id_to_knit_dir[loop_id] 
                dir = '+' if dir == '-' else '-'
                self.loop_id_to_knit_dir[loop_id]  = dir
        # print(f'self.loop_id_to_knit_dir is {self.loop_id_to_knit_dir}')


    def get_carrier_to_first_dir(self):
        for yarn in self.yarns:
            yarn_nodes = yarn.yarn_graph.nodes
            carrier = yarn.carrier
            first_yarn_node = min(yarn_nodes)
            first_dir =  self.loop_id_to_knit_dir[first_yarn_node]
            self.carrier_to_first_dir[carrier] = first_dir
        # print(f'self.carrier_to_first_dir is {self.carrier_to_first_dir}')

    def sort_passes_by_dir_per_course(self):
        # self.courses_to_passes: Dict[int, Dict[str, List[int]]] = {}
        # example of return: self.courses_to_passes is 
        # {0: [['-', [0, 1, 2, 3, 4, 5]], ['+', [6, 7, 8, 9, 10, 11]]], 
        # 1: [['-', [12, 13, 14, 15, 16, 17]], ['+', [18, 19, 20, 21, 22, 23]]], 2: [['-', [24, 25, 26, 27, 28, 29]],
        #  ['+', [30, 31, 32, 33, 34, 35]]], 3: [['-', [36, 37, 38, 39, 40, 41]], ['+', [42, 43, 44, 45, 46, 47]]], 
        # 4: [['-', [48, 49, 50, 52, 53]], ['+', [54, 55, 56, 57, 58, 59]]], 5: [['+', [60, 61, 62]], ['-', [64, 65, 66, 67, 68, 69]], 
        # ['+', [70, 71]]], 6: [['-', [72]], ['+', [73, 74, 75, 76]], ['-', [77, 78, 79, 80, 81, 82]], ['+', [83]]], 
        # 7: [['-', [84]], ['+', [85, 86, 87, 88, 89]], ['-', [90, 91, 92, 93, 94, 95]]], 
        # 8: [['+', [96]], ['-', [97]], ['+', [98, 99, 100, 101, 102]], ['-', [103, 104, 105, 106, 107]]], 
        # 9: [['+', [108]], ['-', [109]], ['+', [110, 111, 112, 113, 114, 115]], ['-', [116, 117, 118, 119]]], 
        # 10: [['+', [120]], ['-', [121, 122]], ['+', [123, 124, 125, 126, 127, 128]], ['-', [129, 130, 131]]]}
        self.courses_to_passes: Dict[int, List[List[str, List[int]]]] = {}
        for course in self._courses_to_loop_ids:
            loops = self._courses_to_loop_ids[course]
            cur_dir = []
            same_pass = []
            pass_with_dir = []
            for i, loop in enumerate(loops):
                if loop in self.loop_id_to_knit_dir:
                    dirr = self.loop_id_to_knit_dir[loop]
                    if cur_dir == []:
                        cur_dir = [dirr]
                        same_pass.append(loop)
                    elif dirr == cur_dir[0]:
                        same_pass.append(loop)
                    elif dirr != cur_dir[0]:
                        passes_with_dir = self.split_pass_with_loops_on_two_beds(dir_loops_pair = [cur_dir[0], same_pass])
                        if passes_with_dir != None:
                            for each_pass_with_dir in passes_with_dir:
                                splited_passes_with_dir = self.split_pass_with_different_yarns(each_pass_with_dir)
                                knit_dir = splited_passes_with_dir[0]
                                splited_passes = splited_passes_with_dir[1]
                                for split_pass in splited_passes:
                                    pass_with_dir.append([knit_dir, split_pass])
                        else:
                            dir_loops_pair = [cur_dir[0], same_pass]
                            splited_passes_with_dir = self.split_pass_with_different_yarns(dir_loops_pair)
                            knit_dir = splited_passes_with_dir[0]
                            splited_passes = splited_passes_with_dir[1]
                            for split_pass in splited_passes:
                                pass_with_dir.append([knit_dir, split_pass])
                        cur_dir = [dirr]
                        same_pass = [loop]
                    if i==len(loops)-1 and len(same_pass)!=0:
                        passes_with_dir = self.split_pass_with_loops_on_two_beds(dir_loops_pair = [cur_dir[0], same_pass])
                        if passes_with_dir != None:
                            for each_pass_with_dir in passes_with_dir:
                                splited_passes_with_dir = self.split_pass_with_different_yarns(each_pass_with_dir)
                                knit_dir = splited_passes_with_dir[0]
                                splited_passes = splited_passes_with_dir[1]
                                for split_pass in splited_passes:
                                    pass_with_dir.append([knit_dir, split_pass])
                        else:
                            dir_loops_pair = [cur_dir[0], same_pass]
                            splited_passes_with_dir = self.split_pass_with_different_yarns(dir_loops_pair)
                            knit_dir = splited_passes_with_dir[0]
                            splited_passes = splited_passes_with_dir[1]
                            for split_pass in splited_passes:
                                pass_with_dir.append([knit_dir, split_pass])
            self.courses_to_passes[course] = pass_with_dir
            # print(i, cur_dir, dirr, same_pass, pass_with_dir)
        print(f'self.courses_to_passes is {self.courses_to_passes}')

    #below is used to reproduce the deprecated version of sort_passes_by_dir_per_course() where passes do not get split by bed and yarns further like above.
    def sort_passes_by_dir_per_course2(self):
        # self.courses_to_passes: Dict[int, Dict[str, List[int]]] = {}
        # example of return: self.courses_to_passes is 
        # {0: [['-', [0, 1, 2, 3, 4, 5]], ['+', [6, 7, 8, 9, 10, 11]]], 
        # 1: [['-', [12, 13, 14, 15, 16, 17]], ['+', [18, 19, 20, 21, 22, 23]]], 2: [['-', [24, 25, 26, 27, 28, 29]],
        #  ['+', [30, 31, 32, 33, 34, 35]]], 3: [['-', [36, 37, 38, 39, 40, 41]], ['+', [42, 43, 44, 45, 46, 47]]], 
        # 4: [['-', [48, 49, 50, 52, 53]], ['+', [54, 55, 56, 57, 58, 59]]], 5: [['+', [60, 61, 62]], ['-', [64, 65, 66, 67, 68, 69]], 
        # ['+', [70, 71]]], 6: [['-', [72]], ['+', [73, 74, 75, 76]], ['-', [77, 78, 79, 80, 81, 82]], ['+', [83]]], 
        # 7: [['-', [84]], ['+', [85, 86, 87, 88, 89]], ['-', [90, 91, 92, 93, 94, 95]]], 
        # 8: [['+', [96]], ['-', [97]], ['+', [98, 99, 100, 101, 102]], ['-', [103, 104, 105, 106, 107]]], 
        # 9: [['+', [108]], ['-', [109]], ['+', [110, 111, 112, 113, 114, 115]], ['-', [116, 117, 118, 119]]], 
        # 10: [['+', [120]], ['-', [121, 122]], ['+', [123, 124, 125, 126, 127, 128]], ['-', [129, 130, 131]]]}
        self.courses_to_passes: Dict[int, List[List[str, List[int]]]] = {}
        for course in self._courses_to_loop_ids:
            loops = self._courses_to_loop_ids[course]
            cur_dir = ''
            same_pass = []
            pass_with_dir = []
            for i, loop in enumerate(loops):
                if loop in self.loop_id_to_knit_dir:
                    dirr = self.loop_id_to_knit_dir[loop]
                    if cur_dir == '':
                        cur_dir = dirr
                        same_pass.append(loop)
                    elif dirr == cur_dir:
                        same_pass.append(loop)
                    elif dirr != cur_dir:
                        pass_with_dir.append([cur_dir, same_pass])
                        cur_dir = dirr
                        same_pass = [loop]
                    if i==len(loops)-1 and len(same_pass)!=0:
                        pass_with_dir.append([cur_dir, same_pass])
            self.courses_to_passes[course] = pass_with_dir
            # print(i, cur_dir, dirr, same_pass, pass_with_dir)
        print(f'self.courses_to_passes is {self.courses_to_passes}')


    #below is used to reproduce the deprecated version of sort_passes_by_dir_per_course() where passes get split by bed and but not by yarns further like above.
    def sort_passes_by_dir_per_course3(self):
        # self.courses_to_passes: Dict[int, Dict[str, List[int]]] = {}
        # example of return: self.courses_to_passes is 
        # {0: [['-', [0, 1, 2, 3, 4, 5]], ['+', [6, 7, 8, 9, 10, 11]]], 
        # 1: [['-', [12, 13, 14, 15, 16, 17]], ['+', [18, 19, 20, 21, 22, 23]]], 2: [['-', [24, 25, 26, 27, 28, 29]],
        #  ['+', [30, 31, 32, 33, 34, 35]]], 3: [['-', [36, 37, 38, 39, 40, 41]], ['+', [42, 43, 44, 45, 46, 47]]], 
        # 4: [['-', [48, 49, 50, 52, 53]], ['+', [54, 55, 56, 57, 58, 59]]], 5: [['+', [60, 61, 62]], ['-', [64, 65, 66, 67, 68, 69]], 
        # ['+', [70, 71]]], 6: [['-', [72]], ['+', [73, 74, 75, 76]], ['-', [77, 78, 79, 80, 81, 82]], ['+', [83]]], 
        # 7: [['-', [84]], ['+', [85, 86, 87, 88, 89]], ['-', [90, 91, 92, 93, 94, 95]]], 
        # 8: [['+', [96]], ['-', [97]], ['+', [98, 99, 100, 101, 102]], ['-', [103, 104, 105, 106, 107]]], 
        # 9: [['+', [108]], ['-', [109]], ['+', [110, 111, 112, 113, 114, 115]], ['-', [116, 117, 118, 119]]], 
        # 10: [['+', [120]], ['-', [121, 122]], ['+', [123, 124, 125, 126, 127, 128]], ['-', [129, 130, 131]]]}
        self.courses_to_passes: Dict[int, List[List[str, List[int]]]] = {}
        for course in self._courses_to_loop_ids:
            loops = self._courses_to_loop_ids[course]
            cur_dir = ''
            same_pass = []
            pass_with_dir = []
            for i, loop in enumerate(loops):
                if loop in self.loop_id_to_knit_dir:
                    dirr = self.loop_id_to_knit_dir[loop]
                    if cur_dir == '':
                        cur_dir = dirr
                        same_pass.append(loop)
                    elif dirr == cur_dir:
                        same_pass.append(loop)
                    elif dirr != cur_dir:
                        passes_with_dir = self.split_pass_with_loops_on_two_beds(dir_loops_pair = [cur_dir, same_pass])
                        if passes_with_dir != None:
                            for each_pass_with_dir in passes_with_dir:
                                pass_with_dir.append(each_pass_with_dir)
                        else:
                            dir_loops_pair = [cur_dir, same_pass]
                            pass_with_dir.append(dir_loops_pair)
                        cur_dir = dirr
                        same_pass = [loop]
                    if i==len(loops)-1 and len(same_pass)!=0:
                        passes_with_dir = self.split_pass_with_loops_on_two_beds(dir_loops_pair = [cur_dir, same_pass])
                        if passes_with_dir != None:
                            for each_pass_with_dir in passes_with_dir:
                                pass_with_dir.append(each_pass_with_dir)
                        else:
                            dir_loops_pair = [cur_dir, same_pass]
                            pass_with_dir.append(dir_loops_pair)
            self.courses_to_passes[course] = pass_with_dir
            # print(i, cur_dir, dirr, same_pass, pass_with_dir)
        print(f'self.courses_to_passes is {self.courses_to_passes}')

    def split_pass_with_loops_on_two_beds(self, dir_loops_pair: List[Union[str, List[int]]]): #we need this function to address the challenge described in slides pp.270.
        knit_dir = dir_loops_pair[0]
        same_pass = dir_loops_pair[1]
        front_bed_pass = []
        back_bed_pass = []
        is_front_bed = False
        is_back_bed = False
        for loop in same_pass:
            if self.node_on_front_or_back[loop] == 'f':
                is_front_bed = True
            if self.node_on_front_or_back[loop] == 'b':
                is_back_bed = True
        if is_front_bed == True and is_back_bed == True:
            for loop in same_pass:
                bed = self.node_on_front_or_back[loop]
                if bed == 'f':
                    front_bed_pass.append(loop)
                else:
                    back_bed_pass.append(loop)
            dir_front_loops_pair = [knit_dir, front_bed_pass]
            dir_back_loops_pair = [knit_dir, back_bed_pass]
            return (dir_front_loops_pair, dir_back_loops_pair) if min(front_bed_pass) < min(back_bed_pass) else (dir_back_loops_pair, dir_front_loops_pair)
        return None
    
    def split_pass_with_different_yarns(self, dir_loops_pair: List[Union[str, List[int]]]):
        """
        # further split passes with different yarns, so that we can get the updated parent_needle position 
        # before we knit child fabric because by this we can separate them into different passes.
        """
        knit_dir = dir_loops_pair[0]
        same_pass = dir_loops_pair[1]
        carrier_id_to_passes: Dict[int, List[int]] = {}
        for loop in same_pass:
            carrier_id = self.loop_id_to_carrier_id[loop]
            if carrier_id not in carrier_id_to_passes:
                carrier_id_to_passes[carrier_id] = [loop]
            else:
                carrier_id_to_passes[carrier_id].append(loop)
        return [knit_dir, [*carrier_id_to_passes.values()]]

    def move_stray_loops_back_home(self):
        # this logic works for ribbing tube and pocket on tube.
        # for each course:
        #   loops_not_home_yet = []
        #   same_target_bed = False #a flag to show if any pass with the same target bed exists for the same course
        #   conflicted_passes = []
        #   for each passes in this course:
        #       xfer the loops in this pass if needed
        #       knit the loops in this pass
        #       if pass in conflicted_passes:
        #           conflicted_passes.remove(pass)
        #           assert len(conflicted_passes) == 0, f'conflicted_passes do not get to empty'
        #           move the loops_not_home_yet home (back to the bed it should be finally at)
        #       if loops in this pass is not in the bed it should be finally at: (we use self.node_on_front_or_back here to find target bed)
        #           loops_not_home_yet = [loops]
        #           target_bed = the bed it should be finally at
        #           if no passes left in this course:
        #               move the loops_not_home_yet home (back to the bed it should be finally at)
        #               loops_not_home_yet = []    
        #           elif passes left in this course:
        #               for each pass in passes left in this course:
        #                   if any loop in this pass is on the same target_bed:
        #                       then don't move the loops_not_home_yet home
        #                       same_target_bed = True
        #                       #note that as there are at most three layers in all of our supported knitted objects, so conflicted_passes
        #                       #has one pass at most   
        #                       conflicted_passes.append(pass) (mark the conflicted pass) 
        #                       assert len(conflicted_passes) == 1, f'conflicted_passes has one pass at most given the range of supported knitted objects in our pipeline'
        #                       break;
        #               if same_target_bed == False:
        #                   then we can safely move the loops_not_home_yet home
        #                   loops_not_home_yet = []
        #   assert len(conflicted_passes) == 0, f'conflicted_passes do not get to empty'
        xxx

    def get_range_of_bed_for_the_pass(self, loop_ids_this_pass: List[int]):
        min_wale = self.node_to_course_and_wale[loop_ids_this_pass[0]][1]
        max_wale = self.node_to_course_and_wale[loop_ids_this_pass[0]][1]
        for loop_id in loop_ids_this_pass:
            wale = self.node_to_course_and_wale[loop_id][1]
            if wale<min_wale:
                min_wale = wale
            elif wale > max_wale:
                max_wale = wale
        return min_wale, max_wale

    def generate_instructions(self):
        """
        Generates the instructions for this knitgraph
        """
        self._add_header()
        # get carrier to use for the very first course loops
        carriers = self.first_course_in_to_carrier[0]
        for carrier in carriers:
            self._cast_on(carrier, is_interlock=False)
        for course in self._sorted_courses:
            # bring in new yarns in the order they are used
            if course > 0:  # not cast on
                if course in self.first_course_in_to_carrier.keys():
                    carriers = self.first_course_in_to_carrier[course]
                    for carrier in carriers:
                        self._cast_on(carrier)   
                passes = self.courses_to_passes[course]
                self._knit_and_split_row(passes, course)
                # pass_direction = pass_direction.opposite() #move inside _knit_and_split_row()
                #----
                if course == self.final_course_parent_knitgraph and self.final_course_parent_knitgraph != 0:
                    print(f'final course on parent knitgraph is {course}')
                    self.drop_loops_on_final_course_on_parentKnitgraph(course)
                #----
        for carrier in self._carrier_set:
            self._instructions.append(outhook(self._machine_state, carrier))
        self._drop_loops()


    def _knit_and_split_row(self, passes: List[List[Union[str, List[int]]]], course_number: int):
        """
        Adds the knit instructions for the given loop ids.
        Transfers to make these loops are also executed
        :param passes: [['-', [0, 1, 2, 3, 4, 5]], ['+', [6, 7, 8, 9, 10, 11]]]
        :param course_number: the course identifier for comments only
        """
        loops_not_home_yet = []
        conflicted_passes = []
        # move here: trial block
        # ----- we can't do this like below otherwise tangling will happen without the proper segregration of loops into different passes.
        # all_loop_id_to_target_needle = []
        # print(f'----start xfer-------')
        # for i, each_pass in enumerate(passes):
        #     loop_ids = each_pass[1]
        #     # Put xfer for row() below would cause some pattern that should be knittable become unknittable. See pp.277 in the slide. thus
        #     # we move it above.
        #     loop_id_to_target_needle, split_offsets = self._do_xfers_for_row(loop_ids, course_number)
        #     all_loop_id_to_target_needle.append(loop_id_to_target_needle)
        # print(f'----End xfer-------')
        # -------
        for i, each_pass in enumerate(passes):
            print(f'this pass is {each_pass}')
            knit_dir  = each_pass[0]
            loop_ids = each_pass[1]
            # Put xfer for row() below would cause some pattern that should be knittable become unknittable. See pp.277 in the slide. thus
            # we move it above. however, this unknittable knitgraph actually does not fall into the scope of what our pipeline considers as a tube object ---
            # the front layer and the back layer of a tube is connected (i.e. stitch edge that connect parent node and child node from two differnt beds
            # exists.), so our pass "navigation" algorithm still works well.
            loop_id_to_target_needle, yarn_over_loop_ids, split_offsets = self._do_xfers_for_row(loop_ids, course_number)
            # 
            print(f'-----start knit & split------')
            # loop_id_to_target_needle = all_loop_id_to_target_needle[i] #this is related to trial block
            knit_and_tuck_and_split_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            for loop_id, target_needle in loop_id_to_target_needle.items():          
                carrier = self.loop_id_to_carrier[loop_id]
                if loop_id in split_offsets:
                    offset = split_offsets[loop_id]
                    split_needle = target_needle.offset(offset).opposite()
                    knit_and_tuck_and_split_data[target_needle] = (Instruction_Parameters(target_needle, involved_loop=loop_id, needle_2 = split_needle, carrier=carrier), Instruction_Type.Split)
                elif loop_id in yarn_over_loop_ids:
                    knit_and_tuck_and_split_data[target_needle] = (Instruction_Parameters(target_needle, involved_loop=loop_id, carrier=carrier), Instruction_Type.Tuck)
                else:
                    knit_and_tuck_and_split_data[target_needle] = (Instruction_Parameters(target_needle, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)
            # print(f'course number is {course_number}, loop_id_to_target_needle is {loop_id_to_target_needle}, pass direction for this knit is {current_direction}')
            if knit_dir == '-':
                pass_direction = Pass_Direction.Right_to_Left
            elif knit_dir == '+':
                pass_direction = Pass_Direction.Left_to_Right
            carriage_pass = Carriage_Pass(pass_direction, knit_and_tuck_and_split_data, self._machine_state)
            # print('knit_and_tuck_and_split_data', knit_and_tuck_and_split_data)
            self._add_carriage_pass(carriage_pass, f"Knit & Tuck & Split course {course_number}")
            no_conflict = True
            # if each_pass in conflicted_passes:
            #     conflicted_passes.remove(each_pass)
            #     print(f'conflicted_pass {each_pass} has been removed, now conflicted_passes becomes {conflicted_passes}')
            #     # assert len(conflicted_passes) == 0, f'conflicted_passes do not get to empty'
            #     if len(conflicted_passes)==0:
            #         self.xfer_strayed_loops_back_home(loops_not_home_yet)
            #         loops_not_home_yet = []
            for loop_id in loop_ids:
                # because below can cause error sometimes, so we print sth here to help debugging
                print(f'loop_id is {loop_id} before is_strayed')
                is_strayed = not ((self.node_on_front_or_back[loop_id] == 'f') == self._machine_state.get_needle_of_loop(loop_id).is_front)
                if is_strayed:
                    loops_not_home_yet.append(loop_id)
            if len(loops_not_home_yet) > 0:      
                min_wale1, max_wale1 = self.get_range_of_bed_for_the_pass(loops_not_home_yet)
                if each_pass == passes[-1]:
                    print('error occurs here')
                    self.xfer_strayed_loops_back_home(loops_not_home_yet)
                    loops_not_home_yet = [] 
                else:
                    passes_remained = passes[i+1:]
                    for the_pass in passes_remained:
                        if len(loops_not_home_yet) > 0:  
                            loop_ids_this_pass = the_pass[1]
                            conflicted_loops = []
                            for loop_id in loop_ids_this_pass:
                                if self.node_on_front_or_back[loop_id] == self.node_on_front_or_back[loops_not_home_yet[0]]: #randomly pick a loop from loops_not_home_yet because all loops in this list should have the same target bed for all supported knit objects in our pipeline.
                                    conflicted_loops.append(loop_id)
                                    #note that as there are at most three layers in all of our supported knitted objects, so conflicted_passes
                                    #has one pass at most 
                            if len(conflicted_loops) > 0:  
                                min_wale2, max_wale2 = self.get_range_of_bed_for_the_pass(conflicted_loops)
                                if (min_wale1 < min_wale2 < max_wale1) or (min_wale2 < min_wale1 < max_wale2):
                                    if the_pass not in conflicted_passes: # we need this if statement, otherwise we would have duplicates in conflicted_passes.
                                        conflicted_passes.append(the_pass) 
                                        print(f'the pass put in conflicted_passes is {the_pass}')
                                        no_conflict = False
                        # if no_conflict == True: #update below
                        if no_conflict == True and len(conflicted_passes)==0:
                            self.xfer_strayed_loops_back_home(loops_not_home_yet)
                            loops_not_home_yet = [] 
                    # if len(conflicted_passes)==0:
                    #     self.xfer_strayed_loops_back_home(loops_not_home_yet)
                    #     loops_not_home_yet = []
            if each_pass in conflicted_passes:
                conflicted_passes.remove(each_pass)
                print(f'conflicted_pass {each_pass} has been removed, now conflicted_passes becomes {conflicted_passes}')
                # assert len(conflicted_passes) == 0, f'conflicted_passes do not get to empty' #this won't hold true when we build multiple pockets on the same side.
                if len(conflicted_passes)==0:
                    self.xfer_strayed_loops_back_home(loops_not_home_yet)
                    loops_not_home_yet = []
                
            print(f'----End Knit & Split-------')
        assert len(conflicted_passes) == 0, f'conflicted_passes do not get to empty'

    def _cast_on(self, carrier: Yarn_Carrier, is_interlock: bool = False):
        """
        Does a standard alternating tuck cast on then 2 stabilizing knit rows.
        for sheet, when self._knit_graph.yarn_start_direction == 'right to left", the first tuck direction should be from left to right,
        i.e., + when we take "reverse_knits" as the first course loops corresponding to our knitgraph in our setting below. That is to say,
        when self._knit_graph.yarn_start_direction == 'left to right", the first tuck direction should be from right to left,
        i.e., -.
        However, for tube, when self._knit_graph.yarn_start_direction == 'right to left", the first tuck direction should be from right 
        to left, i.e., - when we take "reverse_knits" as the first course loops corresponding to our knitgraph in our setting below. That is to say,
        when self._knit_graph.yarn_start_direction == 'left to right", the first tuck direction should be from left to right,
        i.e., +.
        """
        first_course_loops = self._courses_to_loop_ids[self._sorted_courses[0]]
        first_carrier_in_use = self._carrier_set[0]
        ordered_needles_to_tuck_on: List[int] = []
        first_tucks_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        second_tucks_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        reverse_knits: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        first_knit: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        if self.object_type == 'sheet':
            if carrier == first_carrier_in_use:
                for loop in first_course_loops:
                    needle_pos = self.node_to_course_and_wale[loop][1]
                    ordered_needles_to_tuck_on.append(needle_pos)
                if self._knit_graph.yarn_start_direction == 'right to left':
                    first_tuck_needles = ordered_needles_to_tuck_on[::2]
                else:
                    first_tuck_needles = ordered_needles_to_tuck_on[::-2]
                second_tuck_needles = list(set(ordered_needles_to_tuck_on) - set(first_tuck_needles))
                # print(f'1 self._knit_graph.yarn_start_direction is {self._knit_graph.yarn_start_direction}, \
                #     first_tuck_needles is {first_tuck_needles}, second_tuck_needles is {second_tuck_needles}')
                for needle_pos in first_tuck_needles:
                    needle_1 = Needle(True, needle_pos)
                    first_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                for needle_pos in second_tuck_needles:
                    needle_1 = Needle(True, needle_pos)   
                    second_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                if self._knit_graph.yarn_start_direction == 'right to left':
                    first_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_tucks_data, self._machine_state)
                    self._add_carriage_pass(first_pass, f"first pass for cast-on for {carrier}")
                    second_pass = Carriage_Pass(Pass_Direction.Right_to_Left, second_tucks_data, self._machine_state)
                    self._add_carriage_pass(second_pass, f"second pass for cast-on for {carrier}")
                    for needle_pos, loop_id in zip(sorted(ordered_needles_to_tuck_on, reverse=True), first_course_loops):
                        needle_1 = Needle(True, needle_pos)
                        reverse_knits[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Knit)   # note, fake loop_id
                        first_knit[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                    carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, reverse_knits, self._machine_state)
                    self._add_carriage_pass(carriage_pass, f"stabilize cast-on for {carrier}")
                    carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_knit, self._machine_state)
                    self._add_carriage_pass(carriage_pass, f"first row loops right after cast-on stabilization for {carrier}")
                else:
                    first_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_tucks_data, self._machine_state)
                    self._add_carriage_pass(first_pass, f"first pass for cast-on for {carrier}")
                    second_pass = Carriage_Pass(Pass_Direction.Left_to_Right, second_tucks_data, self._machine_state)
                    self._add_carriage_pass(second_pass, f"second pass for cast-on for {carrier}")
                    for needle_pos, loop_id in zip(ordered_needles_to_tuck_on, first_course_loops):
                        needle_1 = Needle(True, needle_pos)
                        reverse_knits[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Knit)   # note, fake loop_id
                        first_knit[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                    carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, reverse_knits, self._machine_state)
                    self._add_carriage_pass(carriage_pass, f"stabilize cast-on for {carrier}")
                    carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_knit, self._machine_state)
                    self._add_carriage_pass(carriage_pass, f"first row loops right after cast-on stabilization for {carrier}")
            elif carrier != first_carrier_in_use:
                # for other carriers, tuck on needles on the side to avoid messing the designed pattern, but note that tuck on which side is determined by the pass direction,
                # if ignore this, introducing a new yarn could fail
                if self.carrier_to_first_dir[carrier] == '-':
                    ordered_needles_to_tuck_on = [*range(self.max_wale+5, self.max_wale+15)]
                elif self.carrier_to_first_dir[carrier] == '+':
                    ordered_needles_to_tuck_on = [*range(self.min_wale-15, self.min_wale - 5)]
                first_tuck_needles = ordered_needles_to_tuck_on[::-2]
                second_tuck_needles = list(set(ordered_needles_to_tuck_on) - set(first_tuck_needles))
                # print(f'2 first_tuck_needles is {first_tuck_needles}, second_tuck_needles is {second_tuck_needles}')
                for needle_pos in first_tuck_needles:
                    needle_1 = Needle(True, needle_pos)
                    first_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                for needle_pos in second_tuck_needles:
                    needle_1 = Needle(True, needle_pos)   
                    second_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                first_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_tucks_data, self._machine_state)
                self._add_carriage_pass(first_pass, f"first pass for cast-on for {carrier}")
                second_pass = Carriage_Pass(Pass_Direction.Left_to_Right, second_tucks_data, self._machine_state)
                self._add_carriage_pass(second_pass, f"second pass for cast-on for {carrier}")
                for needle_pos in ordered_needles_to_tuck_on:
                    needle_1 = Needle(True, needle_pos)
                    reverse_knits[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Knit)   # note, fake loop_id
                    first_knit[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Knit)  
                carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, reverse_knits, self._machine_state)
                self._add_carriage_pass(carriage_pass, f"stabilize cast-on for {carrier}")
                carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_knit, self._machine_state)
                self._add_carriage_pass(carriage_pass, f"first row loops right after cast-on stabilization for {carrier}")
        elif self.object_type == 'tube':
            # first get the gauging info for first course of loops on the front bed and that on the back bed
            back_bed_needles_to_tuck_on = []
            first_course_back_loops = []
            front_bed_needles_to_tuck_on = []
            first_course_front_loops = []
            interlock_needles_to_tuck_on_first = []
            interlock_needles_to_tuck_on_second = []
            first_front_tucks_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            first_back_tucks_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            second_front_tucks_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            second_back_tucks_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            first_all_front: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            first_all_back: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            interlock_tuck_on_first_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            interlock_tuck_on_second_data: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            for loop_id in first_course_loops:
                needle_pos = self.node_to_course_and_wale[loop_id][1]
                bed = self.node_on_front_or_back[loop_id]
                if bed == 'b':
                    back_bed_needles_to_tuck_on.append(needle_pos) 
                    first_course_back_loops.append(loop_id)
                elif bed == 'f':
                    front_bed_needles_to_tuck_on.append(needle_pos)
                    first_course_front_loops.append(loop_id)
            if carrier == first_carrier_in_use and self.already_used == False:
                self.already_used = True
                #note that +2 is because we purposely put loops on front bed and on back bed on exclusive slot to work as half gauging.
                back_bed_needles_to_tuck_on = [i+2 for i in back_bed_needles_to_tuck_on]
                # below line might subject to change upon testing: if tuck on sent out warning, we will change to see if caused by this.
                needles_to_tuck_on_back_bed_first = back_bed_needles_to_tuck_on[::2]
                needles_to_tuck_on_back_bed_second = list(set(back_bed_needles_to_tuck_on) - set(needles_to_tuck_on_back_bed_first))
                if self._knit_graph.yarn_start_direction == 'right to left':
                    #note that +2 is because we purposely put loops on front bed and on back bed on exclusive slot to work as half gauging.
                    #back_bed_needles_to_tuck_on = [i+2 for i in back_bed_needles_to_tuck_on]
                    needles_to_tuck_on_front_bed_first = front_bed_needles_to_tuck_on[::-2]
                    needles_to_tuck_on_front_bed_second = list(set(front_bed_needles_to_tuck_on) - set(needles_to_tuck_on_front_bed_first))
                    interlock_needles_to_tuck_on_first = sorted(needles_to_tuck_on_front_bed_first + needles_to_tuck_on_back_bed_second)
                    interlock_needles_to_tuck_on_second = sorted(needles_to_tuck_on_front_bed_second + needles_to_tuck_on_back_bed_first)
                else:
                    needles_to_tuck_on_front_bed_first = front_bed_needles_to_tuck_on[::2]
                    needles_to_tuck_on_front_bed_second = list(set(front_bed_needles_to_tuck_on) - set(needles_to_tuck_on_front_bed_first))
                print(f'needles_to_tuck_on_front_bed_first is {needles_to_tuck_on_front_bed_first}, needles_to_tuck_on_front_bed_second is {needles_to_tuck_on_front_bed_second}\
                    , needles_to_tuck_on_back_bed_first is {needles_to_tuck_on_back_bed_first}, needles_to_tuck_on_back_bed_second is {needles_to_tuck_on_back_bed_second},\
                      interlock_needles_to_tuck_on_first is {interlock_needles_to_tuck_on_first}, interlock_needles_to_tuck_on_second is {interlock_needles_to_tuck_on_second}')
                if is_interlock == False:
                    for needle_pos in needles_to_tuck_on_front_bed_first:
                        needle_1 = Needle(True, needle_pos)
                        first_front_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                    for needle_pos in needles_to_tuck_on_back_bed_first:
                        needle_1 = Needle(False, needle_pos)
                        first_back_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                    for needle_pos in needles_to_tuck_on_front_bed_second:
                        needle_1 = Needle(True, needle_pos)
                        second_front_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                    for needle_pos in needles_to_tuck_on_back_bed_second:
                        needle_1 = Needle(False, needle_pos)
                        second_back_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                    if self._knit_graph.yarn_start_direction == 'right to left':
                        first_pass_front = Carriage_Pass(Pass_Direction.Right_to_Left, first_front_tucks_data, self._machine_state)
                        self._add_carriage_pass(first_pass_front, f"first front cast-on for {carrier}")
                        first_pass_back = Carriage_Pass(Pass_Direction.Left_to_Right, first_back_tucks_data, self._machine_state)
                        self._add_carriage_pass(first_pass_back, f"first back cast-on for {carrier}")
                        second_pass_front = Carriage_Pass(Pass_Direction.Right_to_Left, second_front_tucks_data, self._machine_state)
                        self._add_carriage_pass(second_pass_front, f"second front cast-on for {carrier}")
                        second_pass_back = Carriage_Pass(Pass_Direction.Left_to_Right, second_back_tucks_data, self._machine_state)
                        self._add_carriage_pass(second_pass_back, f"second back cast-on for {carrier}")
                        for needle_pos, loop_id in zip(sorted(front_bed_needles_to_tuck_on, reverse = True), first_course_front_loops):
                            needle_1 = Needle(True, needle_pos)
                            first_all_front[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                        for needle_pos, loop_id in zip(sorted(back_bed_needles_to_tuck_on), first_course_back_loops):
                            needle_1 = Needle(False, needle_pos)
                            first_all_back[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                        carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_all_front, self._machine_state)
                        self._add_carriage_pass(carriage_pass, f"first row loops on front bed for for {carrier}")
                        carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_all_back, self._machine_state)
                        self._add_carriage_pass(carriage_pass, f"first row loops on back bed for {carrier}")
                    else:
                        first_pass_front = Carriage_Pass(Pass_Direction.Left_to_Right, first_front_tucks_data, self._machine_state)
                        self._add_carriage_pass(first_pass_front, f"first front cast-on for {carrier}")
                        first_pass_back = Carriage_Pass(Pass_Direction.Right_to_Left, first_back_tucks_data, self._machine_state)
                        self._add_carriage_pass(first_pass_back, f"first back cast-on for {carrier}")
                        second_pass_front = Carriage_Pass(Pass_Direction.Left_to_Right, second_front_tucks_data, self._machine_state)
                        self._add_carriage_pass(second_pass_front, f"second front cast-on for {carrier}")
                        second_pass_back = Carriage_Pass(Pass_Direction.Right_to_Left, second_back_tucks_data, self._machine_state)
                        self._add_carriage_pass(second_pass_back, f"second back cast-on for {carrier}")
                        for needle_pos, loop_id in zip(front_bed_needles_to_tuck_on, first_course_front_loops):
                            needle_1 = Needle(True, needle_pos)
                            first_all_front[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                        for needle_pos, loop_id in zip(back_bed_needles_to_tuck_on, first_course_back_loops):
                            needle_1 = Needle(False, needle_pos)
                            first_all_back[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                        carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_all_front, self._machine_state)
                        self._add_carriage_pass(carriage_pass, f"first row loops on front bed for for {carrier}")
                        carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_all_back, self._machine_state)
                        self._add_carriage_pass(carriage_pass, f"first row loops on back bed for {carrier}")
                else: #if is_interlock == True
                    if self._knit_graph.yarn_start_direction == 'right to left':
                        for needle_pos in interlock_needles_to_tuck_on_first:
                            if needle_pos in front_bed_needles_to_tuck_on: 
                                needle_1 = Needle(True, needle_pos)
                            else:
                                needle_1 = Needle(False, needle_pos)
                            interlock_tuck_on_first_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                        for needle_pos in sorted(interlock_needles_to_tuck_on_second, reverse=True):
                            if needle_pos in front_bed_needles_to_tuck_on: 
                                needle_1 = Needle(True, needle_pos)
                            else:
                                needle_1 = Needle(False, needle_pos)
                            interlock_tuck_on_second_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                        first_pass_interlock = Carriage_Pass(Pass_Direction.Right_to_Left, interlock_tuck_on_first_data, self._machine_state)
                        self._add_carriage_pass(first_pass_interlock, f"first front interlock cast-on for {carrier}")
                        second_pass_interlock = Carriage_Pass(Pass_Direction.Left_to_Right, interlock_tuck_on_second_data, self._machine_state)
                        self._add_carriage_pass(second_pass_interlock, f"first back interlock cast-on for {carrier}")
                        for needle_pos, loop_id in zip(sorted(front_bed_needles_to_tuck_on, reverse = True), first_course_front_loops):
                            needle_1 = Needle(True, needle_pos)
                            first_all_front[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                        for needle_pos, loop_id in zip(sorted(back_bed_needles_to_tuck_on), first_course_back_loops):
                            needle_1 = Needle(False, needle_pos)
                            first_all_back[needle_1] = (Instruction_Parameters(needle_1, involved_loop=loop_id, carrier=carrier), Instruction_Type.Knit)  
                        carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_all_front, self._machine_state)
                        self._add_carriage_pass(carriage_pass, f"first row loops on front bed for for {carrier}")
                        carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_all_back, self._machine_state)
                        self._add_carriage_pass(carriage_pass, f"first row loops on back bed for {carrier}")
            else: #elif carrier != first_carrier_in_use:
                # for other carriers, tuck on needles on the side to avoid messing the designed pattern, but note that tuck on which side is determined by the pass direction,
                # if ignore this, introducing a new yarn could fail
                # different from sheet, for tube, for a course there can be two opposite yarn walking direction, which makes pass_direction useless here, thus we introduce
                # two functions above to get the knitting direction of both each loop and each new yarn, which is 
                # stored in self.carrier_to_first_knit_dir to decide the position in "ordered_needles_to_tuck_on".
                if self.carrier_to_first_dir[carrier] == '-':
                    ordered_needles_to_tuck_on = [*range(self.max_wale+5, self.max_wale+15)]
                elif self.carrier_to_first_dir[carrier] == '+':
                    ordered_needles_to_tuck_on = [*range(self.min_wale-15, self.min_wale - 5)]
                first_tuck_needles = ordered_needles_to_tuck_on[::-2]
                second_tuck_needles = list(set(ordered_needles_to_tuck_on) - set(first_tuck_needles))
                # print(f'2 first_tuck_needles is {first_tuck_needles}, second_tuck_needles is {second_tuck_needles}')
                for needle_pos in first_tuck_needles:
                    needle_1 = Needle(True, needle_pos)
                    first_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                for needle_pos in second_tuck_needles:
                    needle_1 = Needle(True, needle_pos)   
                    second_tucks_data[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Tuck)  # note, fake loop_id
                first_pass = Carriage_Pass(Pass_Direction.Right_to_Left, first_tucks_data, self._machine_state)
                self._add_carriage_pass(first_pass, f"first pass for cast-on for {carrier}")
                second_pass = Carriage_Pass(Pass_Direction.Left_to_Right, second_tucks_data, self._machine_state)
                self._add_carriage_pass(second_pass, f"second pass for cast-on for {carrier}")
                for needle_pos in ordered_needles_to_tuck_on:
                    needle_1 = Needle(True, needle_pos)
                    reverse_knits[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Knit)   # note, fake loop_id
                    first_knit[needle_1] = (Instruction_Parameters(needle_1, involved_loop=-1, carrier=carrier), Instruction_Type.Knit)  
                carriage_pass = Carriage_Pass(Pass_Direction.Right_to_Left, reverse_knits, self._machine_state)
                self._add_carriage_pass(carriage_pass, f"stabilize cast-on for {carrier}")
                carriage_pass = Carriage_Pass(Pass_Direction.Left_to_Right, first_knit, self._machine_state)
                self._add_carriage_pass(carriage_pass, f"first row loops right after cast-on stabilization for {carrier}")

    def _drop_loops(self):
        """
        Drops all loops off the machine
        """
        drops: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        second_drops: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        # for needle_pos in range(0, self._machine_state.needle_count):
        for needle_pos in range(int(-self._machine_state.needle_count/2), int(self._machine_state.needle_count/2)):
            front_needle = Needle(is_front=True, position=needle_pos)
            back_needle = Needle(is_front=False, position=needle_pos)
            dropped_front = False
            if len(self._machine_state[front_needle]) > 0:  # drop on loops on front
                drops[front_needle] = (Instruction_Parameters(front_needle), Instruction_Type.Drop)
                dropped_front = True
            if len(self._machine_state[back_needle]) > 0:
                if dropped_front:
                    second_drops[back_needle] = (Instruction_Parameters(back_needle), Instruction_Type.Drop)
                else:
                    # drops[back_needle] = (Instruction_Parameters(front_needle), Instruction_Type.Drop)
                    drops[back_needle] = (Instruction_Parameters(back_needle), Instruction_Type.Drop)
        # print(f'drops is {drops}, second_drops is {second_drops}')
        carriage_pass = Carriage_Pass(None, drops, self._machine_state)
        self._add_carriage_pass(carriage_pass, "Drop KnitGraph")
        # self._add_carriage_pass(carriage_pass)
        carriage_pass = Carriage_Pass(None, second_drops, self._machine_state)
        self._add_carriage_pass(carriage_pass)

    def drop_loops_on_final_course_on_parentKnitgraph(self, course):
        drops_for_final_course_parent_knitgraph: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        print(f'self.loop_ids_on_final_course_parent_knitgraph is {self.loop_ids_on_final_course_parent_knitgraph}')
        for loop_id in self.loop_ids_on_final_course_parent_knitgraph[course]:
            needle = self._machine_state.get_needle_of_loop(loop_id)
            drops_for_final_course_parent_knitgraph[needle] = (Instruction_Parameters(needle), Instruction_Type.Drop)
        carriage_pass = Carriage_Pass(None, drops_for_final_course_parent_knitgraph, self._machine_state)
        print(f'drops_for_final_course_parent_knitgraph is {drops_for_final_course_parent_knitgraph}')
        self._add_carriage_pass(carriage_pass, "Drop final course on parent KnitGraph")


    def xfer_strayed_loops_back_home(self, strayed_loop_ids: List[int]):
        if len(strayed_loop_ids) > 0:
            print('---doing xfer_strayed_loops_back_home---')
            xfers: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
            for loop_id in strayed_loop_ids:
                current_needle = self._machine_state.get_needle_of_loop(loop_id)
                target_needle = current_needle.opposite()
                xfers[current_needle] = (Instruction_Parameters(needle_1 = current_needle, needle_2 = target_needle), Instruction_Type.Xfer)
            carriage_pass = Carriage_Pass(None, xfers, self._machine_state)
            self._add_carriage_pass(carriage_pass, "xfer strayed loops back home")

    def _do_xfers_for_row(self, loop_ids: List[int], course_number: int) -> Dict[int, Needle]:
        """
        Completes all the xfers needed to prepare a row
        :param loop_ids: the loop ids of a single course
        :param direction: the direction that the loops will be knit in
        :return:
        """
        loop_id_to_target_needle, yarn_over_loop_ids, parent_loops_to_needles, lace_offsets, front_cable_offsets, back_cable_offsets, split_offsets, bind_off_loops, \
            split_nodes, parents_on_child_fabric_for_closetop_decrease = self._find_target_needles(loop_ids, course_number)
        self._do_decrease_transfers(parents_on_child_fabric_for_closetop_decrease, parent_loops_to_needles, lace_offsets)
        self._do_cable_transfers(parent_loops_to_needles, front_cable_offsets, back_cable_offsets)
        self._do_knit_purl_xfers(loop_id_to_target_needle, split_nodes)
        # after performing xfers above as needed, to avoid the Error Message "with the command to pass the yarn end between yarn holding hook and yarn inserting hook [R10, 15],
        # set the racking 0.5 pitch or 1/4 pitch for left.", we need to add "rack 0;" to return the back bed to zero position.
        if self._machine_state.racking != 0:
            carriage_pass = Carriage_Pass(None, {}, self._machine_state, only_racking = True)
            self._add_carriage_pass(carriage_pass, "Rack to return back bed home")
        return loop_id_to_target_needle, yarn_over_loop_ids, split_offsets

    def _find_target_needles(self, loop_ids: List[int], course_number: int) -> \
            Tuple[Dict[int, Needle], Dict[int, Needle], Dict[int, int], Dict[int, int], Dict[int, int], Dict[int, int], List[int], List[int]]:
        """
        Finds target needle information needed to do transfers
        :param loop_ids: the loop ids of a single course
        :param direction: the direction that the loops will be knit in
        :return: Loops mapped to target needles to be knit on,
        parent loops mapped to current needles,
        parent loops mapped to their offsets in a decrease
        parent loops mapped to their offsets in the front of cables
        parent loops mapped to their offsets in the back of cables
        """
        parent_loops_to_needles: Dict[int, Needle] = {}  # key loop_ids to the needle they are currently on
        loop_id_to_target_needle: Dict[int, Needle] = {}  # key loop_ids to the needle they need to be on to knit
        yarn_over_loop_ids: List[int] = [] #for yarn over loops, we need to do tuck rather than knit to avoid collapsed stitch. 
        # .... i.e., self._knit_graph.graph[parent_id][loop_id]["parent_offset"]
        parents_to_offsets: Dict[int, int] = {}  # key parent loop_ids to their offset from their child
        # .... only include loops that cross in front. i.e., self._knit_graph.graph[parent_id][loop_id]["depth"] > 0
        front_cable_offsets: Dict[int, int] = {}  # key parent loop_id to the offset to their child
        # .... only include loops that cross in back. i.e., self._knit_graph.graph[parent_id][loop_id]["depth"] < 0
        back_cable_offsets: Dict[int, int] = {}  # key parent loop_id to the offset to their child
        # .... only includes parents involved in a decrease
        decrease_offsets: Dict[int, int] = {}  # key parent loop_id to the offset to their child
        # Dict[mirror_node: offset between rootnode and mirror_node], and 
        # store dict[split_node: offset between rootnode and splitnode] because offset between split node and root node is always 0 in our setting.
        split_offsets: Dict[int, int] = {} 
        # split_nodes stores split nodes 
        split_nodes: List[int] = []
        # .... only includes parents involved in a bindoff
        bind_off_loops: List[int] = []
        # this is used for the case where close top happens for pocket, those parent loops on the child fabric does not need to
        # be xferred to the opposite bed, then rack and get xferred back to the original bed. They only need to rack and get 
        # xferred to the opposite bed. Otherwise, with the first procedure, knit_purl_xfer will be activated to get them back to the
        # opposite bed, which is not only a waste of carriage for two more, but also can lead to mess up. See 
        parents_on_child_fabric_for_closetop_decrease = []
        print(f'loop ids in convertor is {loop_ids}')
        for loop_id in loop_ids:  # find target needle locations of each loop in the course
            parent_ids = [*self._knit_graph.graph.predecessors(loop_id)]
            #get the loop on the final course on the parent knitgraph, so that we can drop them before knitting remaining straps for example (which might be 
            # the reason that cause incomlete strap).
            successors = [*self._knit_graph.graph.successors(loop_id)]
            if len(successors) == 0 and self._knit_graph.loops[loop_id].yarn_id == 'parent_yarn':
                if course_number not in self.loop_ids_on_final_course_parent_knitgraph:
                    self.loop_ids_on_final_course_parent_knitgraph[course_number] = []
                self.loop_ids_on_final_course_parent_knitgraph[course_number].append(loop_id)
                self.final_course_parent_knitgraph = course_number
            if len(parent_ids) > 0:
                for parent_id in parent_ids:  # find current needle of all parent loops
                    parent_needle = self._machine_state.get_needle_of_loop(parent_id)
                    assert parent_needle is not None, f"Parent loop {parent_id} is not held on a needle"
                    parent_loops_to_needles[parent_id] = parent_needle
                # detect split: if a parent node has two child nodes that are on two different yarns.
                is_split = False
                is_mirror_node = False
                is_split_node = False
                for parent_id in parent_ids:
                    # get parent successors
                    successors = [*self._knit_graph.graph.successors(parent_id)]
                    if len(successors) > 1:
                        #because when number of successors > 1, it can only be 2 caused by split.
                        assert len(successors) == 2, f'wrong number of successors: {len(successors)}' 
                        # because split node and mirror node are supposed to be on two different yarns.
                        successors0 = self._knit_graph.loops[successors[0]]
                        successors1 = self._knit_graph.loops[successors[1]]
                        assert successors0.yarn_id != successors1.yarn_id, f'split node and mirror node are supposed to be on two different yarns'
                        is_split = True
                # because both split node and mirror node would satisfy the above condition, i.e., is_split would become True, thus we need to
                # determine if it is a split node or mirror node below.
                if is_split == True: 
                    #detect the mirror node in split
                    if self._knit_graph.loops[loop_id].yarn_id == 'parent_yarn': #then this loop is a mirror node instead of a split node in a split, 
                        is_mirror_node = True
                        # get the target needle of the mirror node
                        parent_needle = parent_loops_to_needles[parent_id]
                        pull_direction = self._knit_graph.graph[parent_id][loop_id]["pull_direction"]
                        if pull_direction == Pull_Direction.FtB:
                            if self.node_on_front_or_back[parent_id] == 'f': 
                                    front_bed = False
                            elif self.node_on_front_or_back[parent_id] == 'b': 
                                front_bed = True
                        elif pull_direction == Pull_Direction.BtF:
                            if self.node_on_front_or_back[parent_id] == 'f': 
                                    front_bed = True
                            elif self.node_on_front_or_back[parent_id] == 'b': 
                                front_bed = False
                        # the reason why we set position for target_needle below using "position=parent_needle.position" rather than
                        # parent_offset then offset_needle.position is to avoid the error. todo: need to update to work for decrease case
                        # where randomly pick a parent node and take its needle might lead to incorrect position detection of loop id.
                        # target_needle = Needle(is_front=front_bed, position=parent_needle.position) #original version
                        # debug version
                        if self._knit_graph.yarn_start_direction == 'right to left':  
                            if self.node_on_front_or_back[loop_id]=='f':
                                parent_offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                            else:
                                parent_offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                        offset_needle = parent_needle.offset(parent_offset)
                        target_needle = Needle(is_front=front_bed, position=offset_needle.position)
                        loop_id_to_target_needle[loop_id] = target_needle
                        # get the other successor, i.e., split node
                        for successor in successors:
                            if self._knit_graph.loops[successor].yarn_id == 'pocket_yarn' or self._knit_graph.loops[successor].yarn_id == 'handle_yarn' or ('strap_yarn' in self._knit_graph.loops[successor].yarn_id):
                                if self._knit_graph.yarn_start_direction == 'right to left':   
                                    split_offset = int(-self._knit_graph.graph[parent_id][successor]["parent_offset"]*1)
                                else:
                                    split_offset = int(self._knit_graph.graph[parent_id][successor]["parent_offset"]*1)
                                # split_offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*1) #here *1 not *self.wale_dist is because special unlike common decrease
                        split_offsets[loop_id] = split_offset
                        print(f'branch catched--loop id {loop_id} is a mirror node, and split offset is {split_offset}, parent_needle is {parent_needle}, target_needle is {target_needle}')
                    # detect the split node in split
                    elif self._knit_graph.loops[loop_id].yarn_id == 'pocket_yarn' or self._knit_graph.loops[loop_id].yarn_id == 'handle_yarn' or ('strap_yarn' in self._knit_graph.loops[loop_id].yarn_id): #then this loop is a split node instead of a mirror node in a split
                        is_split_node = True
                        # method 1
                        # parent_needle = parent_loops_to_needles[parent_id]
                        # parent_needle = self._machine_state.get_needle_of_loop(parent_id) #original version
                        if len(parent_ids) > 1: #usually true for split nodes on the second row and above for pocket/handle/strap patch.
                            for parent_id in parent_ids:
                                if self._knit_graph.loops[parent_id].yarn_id in ['pocket_yarn', 'handle_yarn'] or ('strap_yarn' in self._knit_graph.loops[parent_id].yarn_id):
                                    parent_needle = self._machine_state.get_needle_of_loop(parent_id) 
                                    break
                        else:
                            parent_needle = self._machine_state.get_needle_of_loop(parent_id)#to make parent_needle detection more robust here for the case where we purposely didn't divide each pass further by yarn, (so there might a pass loops from multiple yarns), if there are also 
                        # split involved in this pass, let's say we are building a pocket and a loop on f2 is xfer to b3 after splitting, that is to say, the corresponding split node should be also knit on b3, however, with the above detection method, let's say the parent_id above happens to 
                        # be the root node rather than the parent node that is also on the same pocket patch (if any), then target needle below would be f2, leading to a mismatch needle position when knit this split node. Thus, we change the detection method into "if parent node on the patch exist,
                        # use this parent node rather than the root node" like above
                        target_needle = parent_needle
                        loop_id_to_target_needle[loop_id] = target_needle
                        split_nodes.append(loop_id)
                        # method 2: will fail for pk case
                        # parent_needle = parent_loops_to_needles[parent_id]
                        # parent_offset =  self._knit_graph.graph[parent_id][loop_id]["parent_offset"]
                        # offset_needle = parent_needle.offset(parent_offset)
                        # bed = self.node_on_front_or_back[loop_id]
                        # target_needle = Needle(is_front = (bed == 'f'), position=offset_needle.position)
                        # loop_id_to_target_needle[loop_id] = target_needle
                        # method 3: will fail for strap case
                        # if self._knit_graph.yarn_start_direction == 'right to left':   
                        #     position = self.courses_to_max_wale_on_front[self._loop_id_to_courses[loop_id]] - self.node_to_course_and_wale[loop_id][1]
                        # else:
                        #     position = self.node_to_course_and_wale[loop_id][1]
                        # bed = self.node_on_front_or_back[loop_id]
                        # target_needle = Needle(is_front = (bed == 'f'), position=position)
                        # loop_id_to_target_needle[loop_id] = target_needle
                        self.nodes_on_patch_side.append(loop_id)
                        print(f'branch catched--loop id {loop_id} is a split node, parent_id is {parent_id}, parent_needle is {parent_needle}, target_needle is {target_needle}')
            # detect yarn-over
            if len(parent_ids) == 0:  # yarn-over, yarn overs are made on front bed
                # from below snippet we can see that using wale to identify position of target needle is quite tedious; but we can't 
                # use parent_needle to identify target needle here because yarn over loop has no parent..
                # below doesn't work for the case where we do special cable on the first course resulted from hole creation on the second
                # course. so we use get_yarn_over_needle_position().
                #we can only use this assuming that the object is same width vertically.
                # front_max = max([*self.courses_to_max_wale_on_front.values()])
                # back_max = max([*self.courses_to_max_wale_on_back.values()])
                front_max = self.courses_to_max_wale_on_front[0]
                back_max = self.courses_to_max_wale_on_back[0]
                max_wale = front_max if front_max > back_max else back_max
                if self._knit_graph.yarn_start_direction == 'right to left':    
                    position = max_wale - self.node_to_course_and_wale[loop_id][1]
                else:
                    position = self.node_to_course_and_wale[loop_id][1]
                bed = self.node_on_front_or_back[loop_id]
                target_needle = Needle(is_front = (bed == 'f'), position=position)
                loop_id_to_target_needle[loop_id] = target_needle
                yarn_over_loop_ids.append(loop_id)
                print(f'yarn over detected! loop id is {loop_id}, target_needle is {target_needle}, position is {position}, max_wale is {max_wale}')
            # detect cable
            # if len(parent_ids) == 1 and is_split == False:  # knit, purl, may be in cable. This if condition is deprecated a stitch can be both a cable and part of a split.
            # see pp.322 in the slides. We use is_split == False as a filter here is because we don't want the edge between root nodes and split node be mistaken as cable.
            if len(parent_ids) == 1 and is_split_node == False:# knit, purl, may be in cable. the accurate filter should be this one.
                parent_id = [*parent_ids][0]
                # detect loop id on patch side that can easily disguise as decrease stitch because has two parents too (if we split two nodes to the same needle)
                if parent_id in self.nodes_on_patch_side:
                    self.nodes_on_patch_side.append(loop_id)
                pull_direction = self._knit_graph.graph[parent_id][loop_id]["pull_direction"]
                if self.node_on_front_or_back[loop_id] == self.node_on_front_or_back[parent_id]:
                    if pull_direction == Pull_Direction.FtB:
                        if self.node_on_front_or_back[parent_id] == 'f': 
                                front_bed = False
                        elif self.node_on_front_or_back[parent_id] == 'b': 
                            front_bed = True
                    elif pull_direction == Pull_Direction.BtF:
                        if self.node_on_front_or_back[parent_id] == 'f': 
                                front_bed = True
                        elif self.node_on_front_or_back[parent_id] == 'b': 
                            front_bed = False
                else: #this is applicable to the case where we have a cable stitch in which parent node and child node are on different beds.
                    if self.node_on_front_or_back[loop_id] == 'f': 
                        front_bed = True
                    elif self.node_on_front_or_back[loop_id] == 'b': 
                        front_bed = False
                parent_needle = parent_loops_to_needles[parent_id]
                if self._knit_graph.yarn_start_direction == 'right to left':  
                    if self.node_on_front_or_back[loop_id] == 'f':
                        parent_offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist) #here for c
                    else:
                        parent_offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist) #changed from + to -
                else:
                    parent_offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                offset_needle = parent_needle.offset(parent_offset)
                target_needle = Needle(is_front=front_bed, position=offset_needle.position)
                loop_id_to_target_needle[loop_id] = target_needle
                parents_to_offsets[parent_id] = parent_offset
                # if parent_offset != 0 and parent_needle.is_front == target_needle.is_front: #deprecated because not applicable to cable stitch crossing two beds.
                if parent_offset != 0:
                    cable_depth = self._knit_graph.graph[parent_id][loop_id]["depth"]
                    # update below to a warning rather than assertion, because for a decreased-tube, stitch on edge can disguise as cable stitch but the depth is 0, refer to
                    # pp. 219
                    # assert cable_depth != 0, f"cables must have a non-zero depth to cross at"
                    # if cable_depth != 0: #exclude this bc for tube with hole added, a cable-like stitch can occur with cable_depth = 0, leading no xfer to do xfer.
                    if cable_depth == 1:
                        print(f'front cable detected! loop id is {loop_id}, parent_offset is {parent_offset}, parent_id is {parent_id}, target_needle is {target_needle}')
                        front_cable_offsets[parent_id] = parent_offset #here not *self.wale_dist is because has done so above.
                    elif cable_depth == -1:
                        print(f'back cable detected! loop id is {loop_id}, parent_offset is {parent_offset}, parent_id is {parent_id}, target_needle is {target_needle}')
                        back_cable_offsets[parent_id] = parent_offset
                    else: #this is actually a k/p stitch with non-zero parent offset.
                        print(f'non-zero-po k/p stitch detected detected! loop id is {loop_id}, parent_offset is {parent_offset}, parent_id is {parent_id}, target_needle is {target_needle}')
                        decrease_offsets[parent_id] = parent_offset #they are not decrease by definition, but to avoid wrong yarn over occurs, we need to arrange their xfer to happen at the same time as decrease stitches.
                else:
                    print(f'zero-po k/p stitch detected! loop id is {loop_id}, parent_id is {parent_id}, parent_offset is {parent_offset}, target_needle is {target_needle}')
            # detect decrease
            is_bindoff: bool = False
            if len(parent_ids) > 1: # decrease, the bottom parent loop in the stack will be on the target needle
                # screen to get rid of fake decrease
                if self._knit_graph.loops[loop_id].yarn_id == 'pocket_yarn' or self._knit_graph.loops[loop_id].yarn_id == 'handle_yarn' or ('strap_yarn' in self._knit_graph.loops[loop_id].yarn_id):
                    actual_parents = []
                    for parent_id in parent_ids:
                        if self._knit_graph.loops[parent_id].yarn_id == 'pocket_yarn' or self._knit_graph.loops[parent_id].yarn_id == 'handle_yarn' or ('strap_yarn' in self._knit_graph.loops[parent_id].yarn_id):
                            actual_parents.append(parent_id)
                    parent_ids = actual_parents
                if len(parent_ids) > 1:
                    if self.node_to_course_and_wale[parent_ids[0]][0] != self.node_to_course_and_wale[parent_ids[1]][0]:
                        bind_off_loops.append(loop_id) 
                        is_bindoff = True
                    target_needle = None  # re-assigned on first iteration to needle of first parent
                    # this for loop is used to get target needle for the loop id, and we can achieve this by using only one of the parent loops,
                    # that's why we break the for loop immediately after we find the target needle for the first time.
                    for parent_id in parent_ids:
                        # print(f'in first for loop, parent id {parent_id} is on {self.node_on_front_or_back[parent_id]}, loop id {loop_id} is on \
                        #     {self.node_on_front_or_back[loop_id]}') #with this we can see 
                        parent_needle = parent_loops_to_needles[parent_id]
                        if self._knit_graph.yarn_start_direction == 'right to left':  
                            if self.node_on_front_or_back[loop_id] == 'f':
                                offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                            else:  
                                offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist) #changed from + to -
                                print(f'in decrease detection for back bed, loop id is {loop_id}, parent_id is {parent_id}, offset is {offset}')
                        else:
                            if self.node_on_front_or_back[loop_id] == 'f':
                                offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                            else:
                                offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                        offset_needle = parent_needle.offset(offset)
                        pull_direction = self._knit_graph.graph[parent_id][loop_id]["pull_direction"]
                        if pull_direction == Pull_Direction.FtB:
                            if self.node_on_front_or_back[parent_id] == 'f': 
                                    front_bed = False
                            elif self.node_on_front_or_back[parent_id] == 'b': 
                                front_bed = True
                        elif pull_direction == Pull_Direction.BtF:
                            if self.node_on_front_or_back[parent_id] == 'f': 
                                    front_bed = True
                            elif self.node_on_front_or_back[parent_id] == 'b': 
                                front_bed = False
                        target_needle = Needle(is_front=front_bed, position=offset_needle.position)
                        loop_id_to_target_needle[loop_id] = target_needle
                        break #we can put break here because for either bind-off or decrease, we can get the target needle by using any one of the parent needle
                    # this for loop is used to get decrease offset for the loop id
                    for parent_id in parent_ids:
                        # print(f'in second for loop, parent id {parent_id} is on {self.node_on_front_or_back[parent_id]}, loop id {loop_id} is on \
                        #     {self.node_on_front_or_back[loop_id]}')
                        if self._knit_graph.loops[parent_id].yarn_id == 'pocket_yarn': #no need to include "handle_yarn" here as we don't
                            # close top for handle.
                            parents_on_child_fabric_for_closetop_decrease.append(parent_id)
                        if self._knit_graph.yarn_start_direction == 'right to left':  
                            if self.node_on_front_or_back[loop_id] == 'f': #for both front and back bed, the sign is all '-' as below is because we have recalculate wale and use this updated wale to implement update_parent_offsets()
                                offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                            else:
                                offset = int(-self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist) #changed from + to -
                        else:
                            if self.node_on_front_or_back[loop_id] == 'f':
                                offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                            else:
                                offset = int(self._knit_graph.graph[parent_id][loop_id]["parent_offset"]*self.wale_dist)
                        print(f'in decrease detection, parent id is {parent_id}, offset is {offset}')
                        if offset != 0:
                            decrease_offsets[parent_id] = offset
                    if is_bindoff == True:
                        print(f'bind-off detected! loop id {loop_id}, parent_offset is {offset}, offset_needle is {offset_needle}, parent_needle is {parent_needle}, target_needle is {target_needle}')
                    else:
                        print(f'non-bind-off decrease detected! loop id {loop_id}, parent_offset is {offset}, offset_needle is {offset_needle}, parent_needle is {parent_needle}, target_needle is {target_needle}')
    
        print('loop_id_to_target_needle', loop_id_to_target_needle)
        print('parent_loops_to_needles', parent_loops_to_needles)
        print('decrease_offsets: Dict[parent_node: offset]', decrease_offsets)
        print('front_cable_offsets', front_cable_offsets)
        print('back_cable_offsets', back_cable_offsets)
        print('split_offsets: Dict[mirror_node: offset]', split_offsets)
        print('bind_off_loops', bind_off_loops)
        return loop_id_to_target_needle, yarn_over_loop_ids, parent_loops_to_needles, decrease_offsets, \
               front_cable_offsets, back_cable_offsets, split_offsets, bind_off_loops, split_nodes, parents_on_child_fabric_for_closetop_decrease
               
    def _do_decrease_transfers(self, parents_on_child_fabric_for_closetop_decrease, parent_loops_to_needles: Dict[int, Needle], decrease_offsets: Dict[int, int]):
        """
        Based on the school bus algorithm.
         Transfer all loops in decrease to the opposite side
         Bring the loops back to their offset needle in the order of offsets from negative to positive offsets
        Note that we are restricting our decreases to be offsets of 1 or -1 due to limitations of the machine.
        This is not a completely general method and does not guarantee stacking order of our decreases
        A more advanced method can be found at:
        https://textiles-lab.github.io/posts/2018/02/07/lace-transfers/
        This would require some changes to the code structure and is not recommended for assignment 2.
        :param parent_loops_to_needles: parent loops mapped to their current needle
        :param decrease_offsets: the offsets of parent loops to create decreases
        """
        xfers_to_holding_bed: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        # key needles currently holding the loops to the opposite needle to hold them for offset-xfers
        offset_to_xfers_to_target: Dict[int, Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]]] = {}
        # key offset values (-N...0..N) to starting needles to their target needle
        offset_to_xfers_to_target_for_child_fabric_to_closetop: Dict[int, Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]]] = {}
        # key offset values (-N...0..N) to starting needles to their target needle for parent nodes on the child fabric to do close-top.
        print(f'parents_on_child_fabric_for_closetop_decrease is {parents_on_child_fabric_for_closetop_decrease}')
        for parent_id, parent_needle in parent_loops_to_needles.items():
            if parent_id in decrease_offsets:  # this loop is involved in a decrease
                offset = decrease_offsets[parent_id]
                offset_needle = parent_needle.offset(offset)
                if parent_id in parents_on_child_fabric_for_closetop_decrease:
                    #no need to xfer to opposite without racking, which would be a waste of carriage
                    if offset not in offset_to_xfers_to_target_for_child_fabric_to_closetop:
                        offset_to_xfers_to_target_for_child_fabric_to_closetop[offset] = {}
                    offset_to_xfers_to_target_for_child_fabric_to_closetop[offset][parent_needle] = (Instruction_Parameters(parent_needle, involved_loop=self._machine_state.front_bed.held_loops[parent_needle.position] if parent_needle.is_front==True else self._machine_state.back_bed.held_loops[parent_needle.position], needle_2=offset_needle.opposite()), Instruction_Type.Xfer)
                else:
                    holding_needle = parent_needle.opposite()
                    xfers_to_holding_bed[parent_needle] = (Instruction_Parameters(parent_needle, involved_loop=self._machine_state.front_bed.held_loops[parent_needle.position] if parent_needle.is_front==True else self._machine_state.back_bed.held_loops[parent_needle.position], needle_2=holding_needle), Instruction_Type.Xfer)
                    if offset not in offset_to_xfers_to_target:
                        offset_to_xfers_to_target[offset] = {}
                    offset_to_xfers_to_target[offset][holding_needle] = (Instruction_Parameters(holding_needle, involved_loop=self._machine_state.front_bed.held_loops[parent_needle.position] if parent_needle.is_front==True else self._machine_state.back_bed.held_loops[parent_needle.position], needle_2=offset_needle), Instruction_Type.Xfer)
        carriage_pass = Carriage_Pass(None, xfers_to_holding_bed, self._machine_state)
        self._add_carriage_pass(carriage_pass, "send loops to decrease to back")
        # self._add_carriage_pass(carriage_pass)
        for offset in sorted(offset_to_xfers_to_target.keys()):
            offset_xfers = offset_to_xfers_to_target[offset]
            carriage_pass = Carriage_Pass(None, offset_xfers, self._machine_state)
            self._add_carriage_pass(carriage_pass, f"stack decreases with offset {offset}")
            # self._add_carriage_pass(carriage_pass)
        for offset in sorted(offset_to_xfers_to_target_for_child_fabric_to_closetop.keys()):
            offset_xfers = offset_to_xfers_to_target_for_child_fabric_to_closetop[offset]
            carriage_pass = Carriage_Pass(None, offset_xfers, self._machine_state)
            self._add_carriage_pass(carriage_pass, f"stack decreases with offset {offset} for parent nodes on child fabric to close top")
            # self._add_carriage_pass(carriage_pass)

    def _do_cable_transfers(self, parent_loops_to_needles: Dict[int, Needle], front_cable_offsets: Dict[int, int],
                            back_cable_offsets: Dict[int, int]):
        """
        Transfer all parent loops to back bed
        For front_cables:
            in order of offsets (i.e., 1, 2, 3) transfer to front
        for back_cables
            in order of offsets transfer to back
        :param parent_loops_to_needles: the parent loops mapped to their current needles
        :param front_cable_offsets: parent loops mapped to their offsets for the front of cables
        :param back_cable_offsets: parent loops mapped to their offsets for the back of cables
        """
        xfers_to_back: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        front_cable_xfers: Dict[int, Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]]] = {}
        back_cable_xfers: Dict[int, Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]]] = {}
        for parent_loop, parent_needle in parent_loops_to_needles.items():
            opposite_needle = parent_needle.opposite()
            if parent_loop in front_cable_offsets or parent_loop in back_cable_offsets:
                xfers_to_back[parent_needle] = (Instruction_Parameters(parent_needle, needle_2=opposite_needle), Instruction_Type.Xfer)
            if parent_loop in front_cable_offsets:
                offset = front_cable_offsets[parent_loop]
                if offset not in front_cable_xfers:
                    front_cable_xfers[offset] = {}
                offset_needle = parent_needle.offset(offset)
                front_cable_xfers[offset][opposite_needle] = (Instruction_Parameters(opposite_needle, needle_2=offset_needle), Instruction_Type.Xfer)
            elif parent_loop in back_cable_offsets:
                offset = back_cable_offsets[parent_loop]
                if offset not in back_cable_xfers:
                    back_cable_xfers[offset] = {}
                offset_needle = parent_needle.offset(offset)
                back_cable_xfers[offset][opposite_needle] = (Instruction_Parameters(opposite_needle, needle_2=offset_needle), Instruction_Type.Xfer)
        carriage_pass = Carriage_Pass(None, xfers_to_back, self._machine_state)
        self._add_carriage_pass(carriage_pass, "cables to back")
        for offset, xfer_params in front_cable_xfers.items():
            carriage_pass = Carriage_Pass(None, xfer_params, self._machine_state)
            self._add_carriage_pass(carriage_pass, f"front of cable at offset {offset} to front")
        for offset, xfer_params in back_cable_xfers.items():
            carriage_pass = Carriage_Pass(None, xfer_params, self._machine_state)
            self._add_carriage_pass(carriage_pass, f"back of cable at offset {offset} to front")

    # @this version is designed for strap, but will fail for hole on tube, so we are considering redesigning the rule for strap generation.
    # def _do_knit_purl_xfers(self, loop_id_to_target_needle: Dict[int, Needle]):
    #     """
    #     Transfers loops to bed needed for knit vs purl
    #     :param loop_id_to_target_needle: loops mapped to their target needles
    #     """
    #     kn_xfer = False
    #     xfers: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
    #     for loop_id, target_needle in loop_id_to_target_needle.items():
    #         yarn = self._knit_graph.loops[loop_id].yarn_id
    #         is_same_yarn = False
    #         opposite_needle = target_needle.opposite()
    #         loop_ids_on_opposite = self._machine_state[opposite_needle]
    #         if len(loop_ids_on_opposite) > 0:
    #             for loop_id in loop_ids_on_opposite:
    #                 if self._knit_graph.loops[loop_id].yarn_id == yarn:
    #                     is_same_yarn = True
    #             if is_same_yarn == True:
    #                 xfers[opposite_needle] = (Instruction_Parameters(opposite_needle, needle_2=target_needle), Instruction_Type.Xfer)
    #                 kn_xfer = True
    #     if kn_xfer == True:
    #         print('----doing knit_purl_xfers----')
    #     carriage_pass = Carriage_Pass(None, xfers, self._machine_state)
    #     self._add_carriage_pass(carriage_pass, "kp-transfers")

    def _do_knit_purl_xfers(self, loop_id_to_target_needle: Dict[int, Needle], split_nodes: List[int]):
        """
        Transfers loops to bed needed for knit vs purl
        :param loop_id_to_target_needle: loops mapped to their target needles
        """
        kn_xfer = False
        all_are_split = True
        xfers: Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = {}
        for loop_id, target_needle in loop_id_to_target_needle.items():
            opposite_needle = target_needle.opposite()
            loop_ids_on_opposite = self._machine_state[opposite_needle]
            if len(loop_ids_on_opposite) > 0:
                for loop_id in loop_ids_on_opposite:
                    if loop_id not in split_nodes:
                        all_are_split = False
                    if all_are_split == False:
                        xfers[opposite_needle] = (Instruction_Parameters(opposite_needle, needle_2=target_needle), Instruction_Type.Xfer)
                        kn_xfer = True
        if kn_xfer == True:
            print('----doing knit_purl_xfers----')
        carriage_pass = Carriage_Pass(None, xfers, self._machine_state)
        self._add_carriage_pass(carriage_pass, "kp-transfers")

    def _add_carriage_pass(self, carriage_pass: Carriage_Pass, first_comment="", comment=""):
        """
        Executes the carriage pass and adds it to the instructions
        :param carriage_pass: the carriage pass to be executed
        :param first_comment: a comment for the first instruction
        :param comment:  a comment for each instruction
        """
        if len(carriage_pass.needles_to_instruction_parameters_and_types) > 0 or carriage_pass.only_racking == True:
            self._carriage_passes.append(carriage_pass)
            self._instructions.extend(carriage_pass.write_instructions(first_comment, comment))

    def write_instructions(self, filename: str, generate_instructions: bool = True):
        """
        Writes the instructions from the generator to a knitout file
        :param filename: the name of the file including the suffix
        :param generate_instructions: True if the instructions still need to be generated
        """
        if generate_instructions:
            self.generate_instructions()
        with open(filename, "w") as file:
            file.writelines(self._instructions)

    def _add_header(self, position: str = "Center"):
        """
        Writes the header instructions for this knitgraph
        :param position: where to place the operations on the needle bed; Left, Center, Right,
         and Keep are standard values
        """
        self._instructions.extend([";!knitout-2\n",
                                   ";;Machine: SWG091N2\n",
                                   ";;Gauge: 5\n",
                                   ";;Width: 250\n",
                                   f";;Carriers: 1 2 3 4 5 6 7 8 9 10\n",
                                   f";;Position: {position}\n"])
