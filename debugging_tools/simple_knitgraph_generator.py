"""Simple knitgraph generators used primarily for debugging"""
from typing import List, Optional, Tuple, Dict
from knit_graphs.Knit_Graph import Knit_Graph, Pull_Direction
from knit_graphs.Yarn import Yarn

class Simple_Knitgraph_Generator:
    def __init__(self, pattern: str, gauge: float, carrier: int = 3, width:Optional[int]= None, height:Optional[int] = None, bottom_height:Optional[int] = None, upper_height:Optional[int]= None, increase_gap:Optional[int]= None, increase_sts:Optional[int]= None, \
        rib_width:Optional[int]= None, body_width:Optional[int]= None, height_below_shoulder:Optional[int]= None, left_sleeve_width:Optional[int]= None, left_sleeve_height:Optional[int]= None, \
        right_sleeve_width:Optional[int]= None, right_sleeve_height:Optional[int]= None, height_above_shoulder:Optional[int]= None):
        self.knitGraph: Knit_Graph = Knit_Graph()
        self.knitGraph.node_to_course_and_wale: Dict[int, (int, int)]
        self.knitGraph.node_on_front_or_back: Dict[int, str]
        self.knitGraph.course_and_wale_to_node: Dict[(int, int), int]
        self.knitGraph.course_and_wale_and_bed_to_node: Dict[((int, int), str), int] = {}
        self.pattern: str = pattern
        self.width: int = width
        # if self.width != None:
        #     assert self.width % 2 == 0 #note that it is required the width for any tube should be an even number
        self.height: int = height
        self.carrier: int = carrier
        self.gauge: float = gauge
        self.bottom_height: int = bottom_height
        self.upper_height: int = upper_height
        self.increase_gap: int = increase_gap
        self.increase_sts: int = increase_sts
        self.rib_width: int = rib_width
        self.body_width: int = body_width
        # if self.body_width != None:
        #     assert self.body_width % 2 == 0
        self.height_below_shoulder: int = height_below_shoulder
        self.left_sleeve_width: int = left_sleeve_width
        # if self.left_sleeve_width != None:
        #     assert self.left_sleeve_width % 2 == 0
        self.left_sleeve_height: int = left_sleeve_height
        self.right_sleeve_width: int = right_sleeve_width
        # if self.right_sleeve_width != None:
        #     assert self.right_sleeve_width % 2 == 0
        self.right_sleeve_height: int = right_sleeve_height
        self.height_above_shoulder: int = height_above_shoulder

    def tube(self) -> Knit_Graph:
        """
        (width = 6, height = 6, carrier = 3, gauge  = 1)
        :param carrier:
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: a knitgraph of tube on one yarn of width stitches by height course
        """
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        self.knitGraph.add_yarn(yarn)
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        first_row = []
        wale_dist = int(1/self.gauge)
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        for _ in range(self.width-1, -1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (0, _*wale_dist+1)
            node_on_front_or_back[loop_id] = 'b'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
            
        prior_row = first_row
        for _ in range(1, self.height):
            next_row = []
            for parent_id in (prior_row):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
                if len(next_row) <= self.width:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
            prior_row = next_row
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        for node in self.knitGraph.node_on_front_or_back.keys():
            course_and_wale = self.knitGraph.node_to_course_and_wale[node]
            front_or_back = self.knitGraph.node_on_front_or_back[node]
            self.knitGraph.course_and_wale_and_bed_to_node[(course_and_wale, front_or_back)] = node
        return self.knitGraph

    def decrease_tube(self) -> Knit_Graph:
        """
        (width = 6, height = 3, carrier = 3, gauge = 0.5)
        assume the tube is continuously decreased only on each edge on left and right side.
        :param carrier:
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: a knitgraph of tube on one yarn of width stitches by height course
        """
        #height is actually the number of times the tube can be continuously decreased
        max_height = int((self.width+1)/2) 
        if self.height == None:
            self.height = max_height 
        assert self.height <= max_height, f'max height is {max_height}'
        wale_dist = int(1/self.gauge)
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        self.knitGraph.add_yarn(yarn)
        first_row = []
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        # first course 
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
        for _ in range(self.width-1, -1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist+1)
            node_on_front_or_back[loop_id] = 'b'

        prior_row = first_row
        course_width = self.width
        for _ in range(1, self.height): #starting from 1 is because we have consumed a course above for the first course
            next_row = []
            # number of child node would be 4 nodes fewer than that of prior course after decrease on two edge, front and back side.
            num_of_child = len(prior_row) - 4
            # parent nodes that do not sit on the edge location of each course
            non_edge_parent = prior_row[1:(course_width-1)] + prior_row[(course_width+1):-1]
            assert num_of_child == len(non_edge_parent), f"the tube is expected to have node in each coordinate, i.e., no hole"
            for parent_id in (non_edge_parent):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
                if len(next_row) <= course_width - 2:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                if parent_id == prior_row[1]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[0], child_id, parent_offset = -wale_dist, pull_direction = pull_direction)
            
                elif parent_id == prior_row[course_width+1]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[course_width], child_id, parent_offset = wale_dist, pull_direction = pull_direction)
                    
                elif parent_id == prior_row[course_width-2]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[course_width-1], child_id, parent_offset = wale_dist, pull_direction = pull_direction)
                
                elif parent_id == prior_row[-2]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[-1], child_id, parent_offset = -wale_dist, pull_direction = pull_direction)
                    
                else:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    
            prior_row = next_row
            course_width = course_width - 2
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        for node in self.knitGraph.node_on_front_or_back.keys():
            course_and_wale = self.knitGraph.node_to_course_and_wale[node]
            front_or_back = self.knitGraph.node_on_front_or_back[node]
            self.knitGraph.course_and_wale_and_bed_to_node[(course_and_wale, front_or_back)] = node
        return self.knitGraph

    def arrow_shaped_hat(self) -> Knit_Graph:
        """
        (width = 10, bottom_height = 5, upper_height = 3, carrier = 3, gauge = 0.5)
        :param carrier:
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: a knitgraph of tube on one yarn of width stitches by height course
        """
        assert self.bottom_height >=1, f'invalid bottom height'
        assert self.upper_height >=1, f'invalid upper height'
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        wale_dist = int(1/self.gauge)
        node_to_course_and_wale = {}
        node_on_front_or_back = {}

        self.knitGraph.add_yarn(yarn)
        first_row = []
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
        for _ in range(self.width-1, -1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist+1)
            node_on_front_or_back[loop_id] = 'b'

        prior_row = first_row
        for _ in range(1, self.bottom_height):
            next_row = []
            for parent_id in (prior_row):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                if len(next_row) <= self.width:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
            prior_row = next_row
        
        #height is actually the number of times the tube can be continuously decreased
        max_decrease_height = int((self.width+1)/2) - 1 
        assert self.upper_height <= max_decrease_height, f'upper height: {self.upper_height} is set too large to exceed the maximal allowed decrease height: {max_decrease_height}'
        course_width = self.width
        for _ in range(self.bottom_height, self.bottom_height + self.upper_height):
            next_row = []
            # number of child node would be 4 nodes fewer than that of prior course after decrease on two edge, front and back side.
            num_of_child = len(prior_row) - 4
            # parent nodes that do not sit on the edge location of each course
            non_edge_parent = prior_row[1:(course_width-1)] + prior_row[(course_width+1):-1]
            assert num_of_child == len(non_edge_parent), f"the tube is expected to have node in each coordinate, i.e., no hole"
            for parent_id in (non_edge_parent):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
                if len(next_row) <= course_width - 2:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                if parent_id == prior_row[1]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[0], child_id, parent_offset = -wale_dist, pull_direction = pull_direction)
                elif parent_id == prior_row[course_width+1]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[course_width], child_id, parent_offset = wale_dist, pull_direction = pull_direction)
                elif parent_id == prior_row[course_width-2]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[course_width-1], child_id, parent_offset = wale_dist, pull_direction = pull_direction)
                elif parent_id == prior_row[-2]:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    self.knitGraph.connect_loops(prior_row[-1], child_id, parent_offset = -wale_dist, pull_direction = pull_direction)
                else:
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
            prior_row = next_row
            course_width = course_width - 2
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        for node in self.knitGraph.node_on_front_or_back.keys():
            course_and_wale = self.knitGraph.node_to_course_and_wale[node]
            front_or_back = self.knitGraph.node_on_front_or_back[node]
            self.knitGraph.course_and_wale_and_bed_to_node[(course_and_wale, front_or_back)] = node
        return self.knitGraph

    def increased_tube(self) -> Knit_Graph:
        """
        (self, bottom_height: int, upper_height: int, width: int, increase_gap: int = 1, increase_sts: int = 1, carrier:int = 3, gauge: float = 0.5)
        :param bottom_height: the bottom is the part of tube with no width changes, i.e., no increase happens.
        :param upper_height: the upper is the part that we start increasing, note that we always start increase on the "first" course of the upper_height.
        :param increase_gap, increase takes place each increase_gap round. i.e., if increase_gap = 5, that means we increase once every 5 rounds.
        :param increase_sts: number of sts increased on each side (increase always takes place symmetrically)
        :return: A knit graph with a repeating columns of knits (back to front) then purls (front to back).
        """
        assert self.bottom_height >=1, f'invalid bottom height'
        wale_dist = int(1/self.gauge)
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        self.knitGraph.add_yarn(yarn)
        first_row = []
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        for _ in range(self.width-1, -1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'b'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)

        prior_row = first_row
        for _ in range(1, self.bottom_height):
            next_row = []
            for parent_id in (prior_row):
                child_id, child = yarn.add_loop_to_end()
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                # node_on_front_or_back[child_id] = 'f' if node_on_front_or_back[parent_id] == 'f' else 'b'
                node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                if len(next_row) <= self.width:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
            prior_row = next_row
        
        course_width = self.width
        i = self.increase_gap
        for _ in range(self.bottom_height, self.bottom_height+self.upper_height):
            next_row = []
            if i % self.increase_gap == 0:
                c = int(i / self.increase_gap)
                current_course_right_end = self.width + (c-1)*self.increase_sts - 1
                current_course_left_end = - (c-1)*self.increase_sts
                print(f'current_course_right_end is {current_course_right_end}, current_course_left_end is {current_course_left_end}')
                # front_bed_parents_right = prior_row[:width+c-1]
                # back_bed_parents = prior_row[width+c-1:width+c-1+(width+c-1)+1] 
                # front_bed_parents_left = prior_row[width+c-1+(width+c-1)+1:]
                front_bed_parents_right = prior_row[:current_course_right_end+1]
                back_bed_parents = prior_row[current_course_right_end+1:current_course_right_end+1+course_width] 
                front_bed_parents_left = prior_row[current_course_right_end+1+course_width:]
                print(f'front_bed_parents_right is {front_bed_parents_right}, back_bed_parents is {back_bed_parents}, front_bed_parents_left is {front_bed_parents_left}')
                for parent_id in (front_bed_parents_right):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (_, wale_id)
                    node_on_front_or_back[child_id] = 'f'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.BtF
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                for j in range(current_course_right_end+1, current_course_right_end+self.increase_sts+1): #because on both front and back bed
                    child_id, child = yarn.add_loop_to_end()
                    node_to_course_and_wale[child_id] = (_, j*wale_dist)
                    node_on_front_or_back[child_id] = 'f'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                for j in range(current_course_right_end+self.increase_sts, current_course_right_end, -1): #because on both front and back bed
                    child_id, child = yarn.add_loop_to_end()
                    node_to_course_and_wale[child_id] = (_, j*wale_dist)
                    node_on_front_or_back[child_id] = 'b'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                for parent_id in (back_bed_parents):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (_, wale_id)
                    node_on_front_or_back[child_id] = 'b'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.FtB
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                for j in range(current_course_left_end-1, current_course_left_end-1-self.increase_sts, -1): #because on both front and back bed
                    child_id, child = yarn.add_loop_to_end()
                    node_to_course_and_wale[child_id] = (_, j*wale_dist)
                    node_on_front_or_back[child_id] = 'b'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                for j in range(current_course_left_end-1-self.increase_sts+1, current_course_left_end, 1): #because on both front and back bed
                    child_id, child = yarn.add_loop_to_end()
                    node_to_course_and_wale[child_id] = (_, j*wale_dist)
                    node_on_front_or_back[child_id] = 'f'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                for parent_id in (front_bed_parents_left):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (_, wale_id)
                    node_on_front_or_back[child_id] = 'f'
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.BtF
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                prior_row = next_row
                course_width = course_width + self.increase_sts*2 #because on both left and right side
            else:
                for parent_id in (prior_row):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (_, wale_id)
                    # node_on_front_or_back[child_id] = 'f' if node_on_front_or_back[parent_id] == 'f' else 'b'
                    node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    if len(next_row) <= course_width:
                        pull_direction = Pull_Direction.BtF
                    else:
                        pull_direction = Pull_Direction.FtB
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                prior_row = next_row
            i += 1
        # print(f'node_to_course_and_wale in increased tube is {node_to_course_and_wale}, node_on_front_or_back is {node_on_front_or_back}')
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        for node in self.knitGraph.node_on_front_or_back.keys():
            course_and_wale = self.knitGraph.node_to_course_and_wale[node]
            front_or_back = self.knitGraph.node_on_front_or_back[node]
            self.knitGraph.course_and_wale_and_bed_to_node[(course_and_wale, front_or_back)] = node
        return self.knitGraph

    #current shirt version do not consider increased tube for sleeve as still hasn't identified a method to create a increased tube allowing for max customization.
    def shirt(self):
        """
        body_width = 6, height_below_shoulder = 6, left_sleeve_width = 2, left_sleeve_height = 2, \
        right_sleeve_width = 2, right_sleeve_height = 2, height_above_shoulder = 2, gauge = 0.5
        """
        wale_dist = int(1/self.gauge)
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        self.knitGraph.add_yarn(yarn)
        first_row = []
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        for _ in range(0, self.body_width):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        for _ in range(self.body_width-1, -1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (0, _*wale_dist+1)
            node_on_front_or_back[loop_id] = 'b'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        prior_row_body_part = first_row
        for _ in range(1, self.height_below_shoulder):
            next_row = []
            for parent_id in (prior_row_body_part):
                child_id, child = yarn.add_loop_to_end()
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                if len(next_row) <= self.body_width:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
            prior_row_body_part = next_row
        # start to build left sleeve
        # first build the first course
        cur_course_id = self.height_below_shoulder - 1
        first_row = []
        for _ in range(-1, -self.left_sleeve_width-1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (cur_course_id, _*wale_dist+1)
            node_on_front_or_back[loop_id] = 'b'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        for _ in range(-self.left_sleeve_width, 0):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (cur_course_id, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        # then build the remaining courses
        prior_row_left_sleeve = first_row
        print(f'prior_row_left_sleeve is {prior_row_left_sleeve}')
        # +1 is because we have built the first course above
        for _ in range(cur_course_id+1, cur_course_id+self.left_sleeve_height):
            next_row = []
            for parent_id in (prior_row_left_sleeve):
                child_id, child = yarn.add_loop_to_end()
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                # below is because for the left sleeve, the first half is on the back bed and the second half is on the front bed
                if len(next_row) <= self.left_sleeve_width:
                    pull_direction = Pull_Direction.FtB
                else:
                    pull_direction = Pull_Direction.BtF
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
            prior_row_left_sleeve = next_row
        # then knit back to right
        # prior_row is the last row of the body part, we only need the half on the front bed to knit back to right
        next_row_body_part_half_on_front = []
        loop_ids_num = len(prior_row_body_part)
        prior_row_body_part_half_on_front = prior_row_body_part[:int(loop_ids_num/2)]
        print(f'prior_row_body_part is {prior_row_body_part}')
        for parent_id in (prior_row_body_part_half_on_front):
            child_id, child = yarn.add_loop_to_end()
            wale_id = node_to_course_and_wale[parent_id][1]
            node_to_course_and_wale[child_id] = (_, wale_id)
            node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
            next_row_body_part_half_on_front.append(child_id)
            self.knitGraph.add_loop(child)
            pull_direction = Pull_Direction.BtF
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
        # start to build the right sleeve
        # first build the first course
        first_row = []
        cur_course_id = cur_course_id+self.left_sleeve_height-1
        for _ in range(self.body_width, self.body_width+self.right_sleeve_width):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (cur_course_id, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        for _ in range(self.body_width+self.right_sleeve_width-1, self.body_width-1, -1):
            loop_id, loop = yarn.add_loop_to_end()
            node_to_course_and_wale[loop_id] = (cur_course_id, _*wale_dist+1)
            node_on_front_or_back[loop_id] = 'b'
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
        # then build the remaining courses
        prior_row_right_sleeve = first_row
        # +1 is because we have built the first course above, cur_course_id+self.right_sleeve_height+1 instead of cur_course_id+self.right_sleeve_height is because
        # 
        for _ in range(cur_course_id+1, cur_course_id+self.right_sleeve_height):
            next_row = []
            for parent_id in (prior_row_right_sleeve):
                child_id, child = yarn.add_loop_to_end()
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                # below is because for the left sleeve, the first half is on the front bed and the second half is on the back bed
                if len(next_row) <= self.right_sleeve_width:
                    pull_direction = Pull_Direction.BtF
                else:
                    pull_direction = Pull_Direction.FtB
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
            prior_row_right_sleeve = next_row
        # start to build the shoulder part (include decreased tube)
        #height is actually the number of times the tube can be continuously decreased
        max_height = int(((self.body_width+self.left_sleeve_width+self.right_sleeve_width)+1)/2) 
        assert self.height_above_shoulder <= max_height
        last_course_id = cur_course_id + self.right_sleeve_height - 1
        cur_course_id = last_course_id + 1
        first_row = []
        # start to build the first course
        # note that the current course for body part, left sleeve, and right sleeve are stored in "prior_row__body_part_half_on_back",\
        # "next_row_body_part_half_on_front", "prior_row_left_sleeve", "prior_row_right_sleeve"
        for i, parent_id in enumerate(prior_row_right_sleeve):
            child_id, child = yarn.add_loop_to_end()
            wale_id = node_to_course_and_wale[parent_id][1]
            node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
            node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
            first_row.append(child_id)
            self.knitGraph.add_loop(child)
            if i < int(len(prior_row_left_sleeve)/2):
                pull_direction = Pull_Direction.BtF
            else:
                pull_direction = Pull_Direction.FtB
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
        prior_row_body_part_half_on_back = prior_row_body_part[int(loop_ids_num/2):]
        for parent_id in prior_row_body_part_half_on_back:
            child_id, child = yarn.add_loop_to_end()
            wale_id = node_to_course_and_wale[parent_id][1]
            node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
            node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
            first_row.append(child_id)
            self.knitGraph.add_loop(child)
            pull_direction = Pull_Direction.FtB
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
        for i, parent_id in enumerate(prior_row_left_sleeve):
            child_id, child = yarn.add_loop_to_end()
            wale_id = node_to_course_and_wale[parent_id][1]
            node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
            node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
            first_row.append(child_id)
            self.knitGraph.add_loop(child)
            if i < int(len(prior_row_left_sleeve)/2):
                pull_direction = Pull_Direction.FtB
            else:
                pull_direction = Pull_Direction.BtF
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
        for parent_id in next_row_body_part_half_on_front:
            child_id, child = yarn.add_loop_to_end()
            wale_id = node_to_course_and_wale[parent_id][1]
            node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
            node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
            first_row.append(child_id)
            self.knitGraph.add_loop(child)
            pull_direction = Pull_Direction.BtF
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
        # now that first course has been built, now start decreasing (in the future, we might build some base course for the shoulder part before start decreasing.)
        # cur_course_id += 1
        cur_wale_id = self.body_width - 1
        cur_course_id += 1
        max_index = self.body_width + self.right_sleeve_width - 1
        min_index = -self.left_sleeve_width
        course_width = max_index - min_index + 1
        prior_row = first_row
        for _ in range(1, self.height_above_shoulder): #starting from 1 is because we have consumed a course above for the first course
            next_row = []
            if max_index - cur_wale_id >= 2:
                cur_front_and_right_part = prior_row[:(max_index - cur_wale_id - 1)]
                parent_on_right_edge_front = prior_row[max_index - cur_wale_id - 1]
                print('when max_index - cur_wale_id >= 2:')
                print(f'cur_front_and_right_part is {cur_front_and_right_part}, parent_on_right_edge_front is {parent_on_right_edge_front}')
                for i, parent_id in enumerate(cur_front_and_right_part):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
                    node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.BtF
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    if i == max_index - cur_wale_id - 2:
                        self.knitGraph.connect_loops(parent_on_right_edge_front, child_id, pull_direction = pull_direction, parent_offset = wale_dist)
                # 
                non_edge_parent_on_back = prior_row[(max_index - cur_wale_id + 1):((max_index - cur_wale_id + 1)+course_width-2)]
                parent_on_right_edge_back = prior_row[max_index - cur_wale_id]
                parent_on_left_edge_back = prior_row[(max_index - cur_wale_id + 1)+course_width-2]
                print(f'non_edge_parent_on_back is {non_edge_parent_on_back}, parent_on_right_edge_back is {parent_on_right_edge_back}, \
                    parent_on_left_edge_back is {parent_on_left_edge_back}')
                for i, parent_id in enumerate(non_edge_parent_on_back):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
                    node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.FtB
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    if i == 0:
                        self.knitGraph.connect_loops(parent_on_right_edge_back, child_id, pull_direction = pull_direction, parent_offset = wale_dist)
                    elif i == len(non_edge_parent_on_back) - 1:
                        self.knitGraph.connect_loops(parent_on_left_edge_back, child_id, pull_direction = pull_direction, parent_offset =-wale_dist)
                # 
                non_edge_parent_left_on_front = prior_row[(max_index - cur_wale_id + 1)+course_width:]
                parent_on_left_edge_front = prior_row[(max_index - cur_wale_id + 1)+course_width-1]
                print(f'non_edge_parent_left_on_front is {non_edge_parent_left_on_front}, parent_on_left_edge_front is {parent_on_left_edge_front}')
                for i, parent_id in enumerate(non_edge_parent_left_on_front):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
                    node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.BtF
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    if i == 0:
                        self.knitGraph.connect_loops(parent_on_left_edge_front, child_id, pull_direction = pull_direction, parent_offset = -wale_dist)
                prior_row = next_row
            elif max_index - cur_wale_id == 1:
                next_row = []
                print('when max_index - cur_wale_id == 1:')
                cur_front_and_right_part = prior_row[:(max_index - cur_wale_id - 1)]
                parent_on_right_edge_front = prior_row[max_index - cur_wale_id - 1]
                print(f'cur_front_and_right_part is {cur_front_and_right_part}, parent_on_right_edge_front is {parent_on_right_edge_front}')
                first_parent_node_to_start_next_course = prior_row[-1]
                child_id, child = yarn.add_loop_to_end()
                wale_id = node_to_course_and_wale[first_parent_node_to_start_next_course][1]
                node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
                node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                pull_direction = Pull_Direction.BtF
                self.knitGraph.connect_loops(first_parent_node_to_start_next_course, child_id, pull_direction = pull_direction)
                self.knitGraph.connect_loops(parent_on_right_edge_front, child_id, pull_direction = pull_direction, parent_offset = wale_dist)
                # 
                non_edge_parent_on_back = prior_row[(max_index - cur_wale_id + 1):((max_index - cur_wale_id + 1)+course_width-2)]
                parent_on_right_edge_back = prior_row[max_index - cur_wale_id]
                parent_on_left_edge_back = prior_row[(max_index - cur_wale_id + 1)+course_width-2]
                print(f'non_edge_parent_on_back is {non_edge_parent_on_back}, parent_on_right_edge_back is {parent_on_right_edge_back}, \
                    parent_on_left_edge_back is {parent_on_left_edge_back}')
                for i, parent_id in enumerate(non_edge_parent_on_back):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
                    node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.FtB
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    if i == 0:
                        self.knitGraph.connect_loops(parent_on_right_edge_back, child_id, pull_direction = pull_direction, parent_offset = wale_dist)
                    elif i == len(non_edge_parent_on_back) - 1:
                        self.knitGraph.connect_loops(parent_on_left_edge_back, child_id, pull_direction = pull_direction, parent_offset = -wale_dist)
                # 
                non_edge_parent_left_on_front = prior_row[(max_index - cur_wale_id + 1)+course_width:]
                parent_on_left_edge_front = prior_row[(max_index - cur_wale_id + 1)+course_width-1]
                print(f'non_edge_parent_left_on_front is {non_edge_parent_left_on_front}, parent_on_left_edge_front is {parent_on_left_edge_front}')
                for i, parent_id in enumerate(non_edge_parent_left_on_front[:-1]):
                    child_id, child = yarn.add_loop_to_end()
                    wale_id = node_to_course_and_wale[parent_id][1]
                    node_to_course_and_wale[child_id] = (cur_course_id, wale_id)
                    node_on_front_or_back[child_id] = node_on_front_or_back[parent_id]
                    next_row.append(child_id)
                    self.knitGraph.add_loop(child)
                    pull_direction = Pull_Direction.BtF
                    self.knitGraph.connect_loops(parent_id, child_id, pull_direction = pull_direction)
                    if i == 0:
                        self.knitGraph.connect_loops(parent_on_left_edge_front, child_id, pull_direction = pull_direction, parent_offset = -wale_dist)
                prior_row = next_row
                cur_wale_id -= 1
            max_index -= 1
            min_index += 1
            course_width = max_index - min_index + 1
            cur_course_id += 1
            print(f'updated max_wale_id is {max_index}, updated min_wale_id is {min_index}, updated course_width is {course_width}, cur_wale_id is {cur_wale_id}')
        
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        for node in self.knitGraph.node_on_front_or_back.keys():
            course_and_wale = self.knitGraph.node_to_course_and_wale[node]
            front_or_back = self.knitGraph.node_on_front_or_back[node]
            self.knitGraph.course_and_wale_and_bed_to_node[(course_and_wale, front_or_back)] = node
        return self.knitGraph

    def stockinette(self) -> Knit_Graph:
        """
        (self, width: int = 4, height: int = 4, carrier:int=3, gauge: float = 1)
        :param carrier:
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: a knitgraph of stockinette on one yarn of width stitches by height course
        """
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        self.knitGraph.add_yarn(yarn)
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        first_row = []
        wale_dist = int(1/self.gauge)
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            self.knitGraph.add_loop(loop)

        prior_row = first_row
        for _ in range(1, self.height):
            next_row = []
            for parent_id in reversed(prior_row):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                self.knitGraph.connect_loops(parent_id, child_id)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
            prior_row = next_row
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        self.knitGraph.course_and_wale_to_node = {tuple(v): k for k, v in self.knitGraph.node_to_course_and_wale.items()}
        return self.knitGraph

    def rib(self) -> Knit_Graph: 
        """
        (self, width: int = 4, height: int = 4, rib_width: int = 1, carrier_id:int = 3, gauge: float = 1)
        :param rib_width: determines how many columns of knits and purls are in a single rib.
        (i.e.) the first course of width=4 and rib_width=2 will be kkpp. Always start with knit columns
        :param width: a number greater than 0 to set the number of stitches in the swatch
        :param height: A number greater than 2 to set the number of courses in the swatch
        :return: A knit graph with a repeating columns of knits (back to front) then purls (front to back).
        """
        assert self.width > 0
        assert self.height > 1
        assert self.rib_width <= self.width
        wale_dist = int(1/self.gauge)
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph, carrier_id=self.carrier)
        self.knitGraph.add_yarn(yarn)
        first_row = []
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'
            self.knitGraph.add_loop(loop)

        prior_row = first_row
        next_row = []
        for column, parent_id in reversed([*enumerate(prior_row)]):
            child_id, child = yarn.add_loop_to_end()
            next_row.append(child_id)
            self.knitGraph.add_loop(child)
            rib_id = int(int(column) / int(self.rib_width))
            if rib_id % 2 == 0:  # even ribs:
                pull_direction = Pull_Direction.BtF
            else:
                pull_direction = Pull_Direction.FtB
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction=pull_direction)
            wale_id = node_to_course_and_wale[parent_id][1]
            node_to_course_and_wale[child_id] = (1, wale_id)
            parent_loop_bed = node_on_front_or_back[parent_id]
            node_on_front_or_back[child_id] = parent_loop_bed

        for _ in range(2, self.height):
            prior_row = next_row
            next_row = []
            for parent_id in reversed(prior_row):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                grand_parent = [*self.knitGraph.graph.predecessors(parent_id)][0]
                parent_pull_direction = self.knitGraph.graph[grand_parent][parent_id]["pull_direction"]
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction=parent_pull_direction)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (_, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        self.knitGraph.course_and_wale_to_node = {tuple(v): k for k, v in self.knitGraph.node_to_course_and_wale.items()}
        return self.knitGraph

    def lace(self):
        """
        (self, width: int = 4, height: int = 4, gauge: float = 1)
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: a knitgraph with k2togs and yarn-overs surrounded by knit wales
        """
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", knitGraph)
        self.knitGraph.add_yarn(yarn)
        first_row = []
        wale_dist = int(1/self.gauge)
        node_to_course_and_wale = {}
        node_on_front_or_back = {}
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)
            node_to_course_and_wale[loop_id] = (0, _*wale_dist)
            node_on_front_or_back[loop_id] = 'f'

        def add_loop_and_knit(p_id, offset: int = 0):
            """
            Knits a loop into the graph
            :param p_id: the id of the parent loop being knit through
            :return: the id of the child loop created
            """
            c_id, c = yarn.add_loop_to_end()
            next_row.append(c_id)
            self.knitGraph.add_loop(c)
            self.knitGraph.connect_loops(p_id, c_id, pull_direction=Pull_Direction.BtF, parent_offset=offset)
            return c_id

        prior_row = first_row
        for row in range(1, self.height):
            next_row = []
            prior_parent_id = -1
            reversed_prior_row = [*reversed(prior_row)]
            for col, parent_id in enumerate(reversed_prior_row):
                # knit on even rows and before and after twists
                if row % 2 == 0 or col % self.width in set(range(self.width)).difference({1,2}): 
                    child_id = add_loop_and_knit(parent_id)
                # yarn over
                elif col % self.width == 1:
                    child_id, child = yarn.add_loop_to_end()
                    self.knitGraph.add_loop(child)
                    next_row.append(child_id) 
                    prior_parent_id = parent_id
                # decrease
                elif col % self.width == 2:
                    child_id = add_loop_and_knit(parent_id)
                    self.knitGraph.connect_loops(prior_parent_id, child_id, parent_offset=wale_dist)
                wale_id = node_to_course_and_wale[parent_id][1]
                node_to_course_and_wale[child_id] = (row, wale_id)
                parent_loop_bed = node_on_front_or_back[parent_id]
                node_on_front_or_back[child_id] = parent_loop_bed
            prior_row = next_row
        # self.knitGraph = knitGraph
        self.knitGraph.node_to_course_and_wale = node_to_course_and_wale
        self.knitGraph.node_on_front_or_back = node_on_front_or_back
        self.knitGraph.course_and_wale_to_node = {tuple(v): k for k, v in self.knitGraph.node_to_course_and_wale.items()}
        return self.knitGraph

    def seed(self) -> Knit_Graph:
        """
        (self, width: int = 4, height=4)
        :param width: a number greater than 0 to set the number of stitches in the swatch
        :param height: A number greater than 0 to set teh number of courses in the swatch
        :return: A knit graph with a checkered pattern of knit and purl stitches of width and height size.
        The first stitch should be a knit
        """
        assert self.width > 0
        assert self.height > 1

        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph)
        self.knitGraph.add_yarn(yarn)
        first_row = []
        for _ in range(0, self.width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            self.knitGraph.add_loop(loop)

        prior_row = first_row
        next_row = []
        for column, parent_id in enumerate(reversed(prior_row)):
            child_id, child = yarn.add_loop_to_end()
            next_row.append(child_id)
            self.knitGraph.add_loop(child)
            if column % 2 == 0:  # even seed:
                pull_direction = Pull_Direction.BtF
            else:
                pull_direction = Pull_Direction.FtB
            self.knitGraph.connect_loops(parent_id, child_id, pull_direction=pull_direction)

        for _ in range(2, self.height):
            prior_row = next_row
            next_row = []
            for parent_id in reversed(prior_row):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                self.knitGraph.add_loop(child)
                grand_parent = [*self.knitGraph.graph.predecessors(parent_id)][0]
                parent_pull_direction = self.knitGraph.graph[grand_parent][parent_id]["pull_direction"]
                self.knitGraph.connect_loops(parent_id, child_id, pull_direction=parent_pull_direction.opposite())
        return self.knitGraph

    def twisted_stripes(self, width: int = 4, height=5, left_twists: bool = True) -> Knit_Graph:
        """
        :param left_twists: if True, make the left leaning stitches in front, otherwise right leaning stitches in front
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: A knitgraph with repeating pattern of twisted stitches surrounded by knit wales
        """
        assert width % 4 == 0, "Pattern is 4 loops wide"
        # knitGraph = Knit_Graph()
        yarn = Yarn("yarn", self.knitGraph)
        self.knitGraph.add_yarn(yarn)

        # Add the first course of loops
        first_course = []
        for _ in range(0, width):
            loop_id, loop = yarn.add_loop_to_end()
            first_course.append(loop_id)
            knitGraph.add_loop(loop)

        def add_loop_and_knit(p_id, depth=0, parent_offset: int = 0, pull_direction= Pull_Direction.BtF):
            """
            adds a loop by knitting to the knitgraph
            :param parent_offset: Set the offset of the parent loop in the cable. offset = parent_index - child_index
            :param p_id: the parent loop's id
            :param depth: the crossing- depth to knit at
            """
            child_id, child = yarn.add_loop_to_end()
            next_course.append(child_id)
            knitGraph.add_loop(child)
            knitGraph.connect_loops(p_id, child_id, depth=depth, parent_offset=parent_offset, pull_direction=pull_direction)

        if left_twists:  # set the depth for the first loop in the twist (1 means it will cross in front of other stitches)
            twist_depth = 1
        else:
            twist_depth = -1

        # add new courses
        prior_course = first_course
        for course in range(1, height):
            next_course = []
            reversed_prior_course = [*reversed(prior_course)]

            # print('reversed_prior_course', reversed_prior_course)
            for col, parent_id in enumerate(reversed_prior_course):
                #if course % 2 == 0 or col % 4 == 0 or col % 4 == 3:  # knit on even rows and before and after twists
                if course % 2 == 0 or col % 4 == 0 or col % 4 == 3:
                    add_loop_and_knit(parent_id)
                elif col % 4 == 1:
                    next_parent_id = reversed_prior_course[col + 1]
                    # print('col',col, col+1, next_parent_id)
                    # add_loop_and_knit(next_parent_id, depth=twist_depth, parent_offset=1)
                    add_loop_and_knit(next_parent_id, depth=twist_depth, parent_offset=-1)
                    twist_depth = -1 * twist_depth  # switch depth for neighbor
                elif col % 4 == 2:
                    next_parent_id = reversed_prior_course[col - 1]
                    # print('col',col, col-1, next_parent_id)
                    # add_loop_and_knit(next_parent_id, depth=twist_depth, parent_offset=-1)
                    add_loop_and_knit(next_parent_id, depth=twist_depth, parent_offset=1)
                    twist_depth = -1 * twist_depth  # switch depth for next twist
                
            prior_course = next_course

        return knitGraph


    def both_twists(height=20) -> Knit_Graph:
        """
        :param left_twists: if True, make the left leaning stitches in front, otherwise right leaning stitches in front
        :param width: the number of stitches of the swatch
        :param height:  the number of courses of the swatch
        :return: A knitgraph with repeating pattern of twisted stitches surrounded by knit wales
        """
        width = 10
        knitGraph = Knit_Graph()
        yarn = Yarn("yarn", knitGraph)
        knitGraph.add_yarn(yarn)

        # Add the first course of loops
        first_course = []
        for _ in range(0, width):
            loop_id, loop = yarn.add_loop_to_end()
            first_course.append(loop_id)
            knitGraph.add_loop(loop)

        def add_loop_and_knit(p_id, depth=0, parent_offset: int = 0):
            """
            adds a loop by knitting to the knitgraph
            :param parent_offset: Set the offset of the parent loop in the cable. offset = parent_index - child_index
            :param p_id: the parent loop's id
            :param depth: the crossing- depth to knit at
            """
            child_id, child = yarn.add_loop_to_end()
            next_course.append(child_id)
            knitGraph.add_loop(child)
            knitGraph.connect_loops(p_id, child_id, depth=depth, parent_offset=parent_offset)

        # add new courses
        prior_course = first_course
        for course in range(1, height):
            next_course = []
            reversed_prior_course = [*reversed(prior_course)]
            for col, parent_id in enumerate(reversed_prior_course):
                if course % 2 == 1 or col in {0, 1, 4, 5,8, 9}:  # knit on odd rows and borders or middle
                    add_loop_and_knit(parent_id)
                elif col == 2:
                    parent_id = reversed_prior_course[3]
                    add_loop_and_knit(parent_id, depth=-1, parent_offset=-1)
                elif col == 3:
                    parent_id = reversed_prior_course[2]
                    add_loop_and_knit(parent_id, depth=1, parent_offset=1)
                elif col == 6:
                    parent_id = reversed_prior_course[7]
                    add_loop_and_knit(parent_id, depth=1, parent_offset=-1)
                elif col == 7:
                    parent_id = reversed_prior_course[6]
                    add_loop_and_knit(parent_id, depth=-1, parent_offset=1)
            prior_course = next_course

        return knitGraph


    # def twisted_stripes(width: int = 4, height=5) -> Knit_Graph:
    #     """
    #     :param width: the number of stitches of the swatch
    #     :param height:  the number of courses of the swatch
    #     :return: A knitgraph with repeating pattern of twisted stitches surrounded by knit wales
    #     """
    #     knitGraph = Knit_Graph()
    #     yarn = Yarn("yarn")
    #     knitGraph.add_yarn(yarn)
    #     first_row = []
    #     for _ in range(0, width):
    #         loop_id, loop = yarn.add_loop_to_end()
    #         first_row.append(loop_id)
    #         knitGraph.add_loop(loop)
    #
    #     def add_loop_and_knit(p_id, depth=0):
    #         """
    #         adds a loop by knitting to the knitgraph
    #         :param p_id: the parent loop's id
    #         :param depth: the crossing- depth to knit at
    #         """
    #         child_id, child = yarn.add_loop_to_end()
    #         next_row.append(child_id)
    #         knitGraph.add_loop(child)
    #         knitGraph.connect_loops(p_id, child_id, depth=depth)
    #
    #     prior_row = first_row
    #     first_depth = 1  # switch between left and right twists
    #     for row in range(1, height):
    #         next_row = []
    #         prior_parent_id = -1
    #         reversed_prior_row = [*reversed(prior_row)]
    #         for col, parent_id in enumerate(reversed_prior_row):
    #             if row % 2 == 0 or col % 4 == 0 or col % 4 == 3:  # knit on even rows and before and after twists
    #                 add_loop_and_knit(parent_id)
    #             elif col % 4 == 1:
    #                 prior_parent_id = parent_id
    #                 next_parent_id = reversed_prior_row[col + 1]
    #                 add_loop_and_knit(next_parent_id, first_depth)  # set to opposite depth of crossing partner
    #             elif col % 4 == 2:
    #                 add_loop_and_knit(prior_parent_id, -1 * first_depth)  # set to opposite depth of crossing partner
    #                 first_depth = -1 * first_depth  # switch depth for next twist course
    #         prior_row = next_row
    #
    #     return knitGraph


    def lace_and_twist():
        """

        :return:
        """
        width = 13
        knitGraph = Knit_Graph()
        yarn = Yarn("yarn", knitGraph)
        knitGraph.add_yarn(yarn)
        first_row = []
        for _ in range(0, width):
            loop_id, loop = yarn.add_loop_to_end()
            first_row.append(loop_id)
            knitGraph.add_loop(loop)

        next_row = []
        for _ in range(0, width):
            child_id, child = yarn.add_loop_to_end()
            knitGraph.add_loop(child)
            next_row.append(child_id)
        # knit edge
        knitGraph.connect_loops(0, 25)
        knitGraph.connect_loops(12, 13)
        # bottom of decrease stack
        knitGraph.connect_loops(1, 24, stack_position=0)
        knitGraph.connect_loops(6, 19, stack_position=0)
        knitGraph.connect_loops(11, 14, stack_position=0)
        # 2nd of decrease stack
        knitGraph.connect_loops(2, 24, stack_position=1, parent_offset=1)
        knitGraph.connect_loops(5, 19, stack_position=1, parent_offset=-1)
        knitGraph.connect_loops(10, 14, stack_position=1, parent_offset=-1)
        # 3rd of decrease stack
        knitGraph.connect_loops(7, 19, stack_position=2, parent_offset=1)
        # twist  right
        knitGraph.connect_loops(3, 21, depth=1, parent_offset=1)
        knitGraph.connect_loops(4, 22, depth=-1, parent_offset=-1)
        # twist left
        knitGraph.connect_loops(8, 16, depth=-1, parent_offset=1)
        knitGraph.connect_loops(9, 17, depth=1, parent_offset=-1)

        for parent_id in reversed(next_row):
            child_id, child = yarn.add_loop_to_end()
            knitGraph.add_loop(child)
            knitGraph.connect_loops(parent_id, child_id)

        return knitGraph


    def short_rows(width: int = 10, buffer_height: int = 2) -> Knit_Graph:
        """
        :param buffer_height: THe height of the buffer on top and bottom
        :param width: the width of the swatch, must be greater than 4
        :return: a knitgraph with width in stockinette with 4 short rows in the center of a buffer
        """
        assert width > 4, "Not enough stitches to short row"
        # Get the base of the graph
        knit_graph = stockinette(width=width, height=buffer_height)
        # print('[*knit_graph.yarns.values()][0]', [*knit_graph.yarns.values()][0])
        yarn = [*knit_graph.yarns.values()][0]

        loop_ids_to_course, course_to_loop_ids, loop_ids_to_wale, wale_to_loop_ids = knit_graph.get_courses()
        if len(course_to_loop_ids) == 1:
            top_course = course_to_loop_ids[0]
        else:
            top_course_index = max(*course_to_loop_ids.keys())
            top_course = course_to_loop_ids[top_course_index]
        # print(course_to_loop_ids, course_to_loop_ids.keys(), *course_to_loop_ids.keys())
        # print('top course', top_course)
        # Knit to last two loops and reserve on left
        next_row = []
        reversed_top_course = [*reversed(top_course)]
        reserved_top_left = reversed_top_course[-2:]
        for parent_id in reversed_top_course[:-2]:
            child_id, child = yarn.add_loop_to_end()
            next_row.append(child_id)
            knit_graph.add_loop(child)
            knit_graph.connect_loops(parent_id, child_id)

        # Knit to last two loops and reserve on right
        top_course = next_row
        next_row = []
        reversed_top_course = [*reversed(top_course)]
        reserved_top_right = reversed_top_course[-2:]
        for parent_id in reversed_top_course[:-2]:
            child_id, child = yarn.add_loop_to_end()
            next_row.append(child_id)
            knit_graph.add_loop(child)
            knit_graph.connect_loops(parent_id, child_id)

        # Knit over last row and reserved loops on left
        top_course = next_row
        next_row = []
        reversed_top_course = [*reversed(top_course)]
        reversed_top_course.extend(reserved_top_left)
        for parent_id in reversed_top_course:
            child_id, child = yarn.add_loop_to_end()
            next_row.append(child_id)
            knit_graph.add_loop(child)
            knit_graph.connect_loops(parent_id, child_id)

        # knit over last row and reserved loops on right
        top_course = next_row
        next_row = []
        reversed_top_course = [*reversed(top_course)]
        reversed_top_course.extend(reserved_top_right)
        for parent_id in reversed_top_course:
            child_id, child = yarn.add_loop_to_end()
            next_row.append(child_id)
            knit_graph.add_loop(child)
            knit_graph.connect_loops(parent_id, child_id)

        # add 5 stst rows
        prior_row = next_row
        for _ in range(0, buffer_height):
            next_row = []
            for parent_id in reversed(prior_row):
                child_id, child = yarn.add_loop_to_end()
                next_row.append(child_id)
                knit_graph.add_loop(child)
                knit_graph.connect_loops(parent_id, child_id)
            prior_row = next_row
        return knit_graph
    
    def generate_knitgraph(self):
        if self.pattern == 'tube':
            knit_graph = self.tube()
        elif self.pattern == 'decreased_tube':
            knit_graph = self.decrease_tube()
        elif self.pattern == 'arrow_shaped_hat':
            knit_graph = self.arrow_shaped_hat()
        elif self.pattern == 'increased_tube':
            knit_graph = self.increased_tube()
        elif self.pattern == 'stockinette':
            knit_graph = self.stockinette()
        elif self.pattern == 'rib':
            knit_graph = self.rib()
        elif self.pattern == 'lace':
            knit_graph = self.lace()
        elif self.pattern == 'seed':
            knit_graph = self.seed()
        elif self.pattern == 'shirt':
            knit_graph = self.shirt()
        return knit_graph

