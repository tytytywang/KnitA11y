"""Compiler code for converting knitspeak AST to knitgraph"""
from typing import List, Dict, Union, Tuple, Set

from knit_graphs.Knit_Graph import Knit_Graph
from knit_graphs.Yarn import Yarn
from knitspeak_compiler.knitspeak_interpreter.knitspeak_interpreter import KnitSpeak_Interpreter
from knitspeak_compiler.knitspeak_interpreter.cable_definitions import Cable_Definition
from knitspeak_compiler.knitspeak_interpreter.increase_definitions import *
from knitspeak_compiler.knitspeak_interpreter.closures import Num_Closure, Iterator_Closure
from knitspeak_compiler.knitspeak_interpreter.stitch_definitions import Stitch_Definition
from debugging_tools.exceptions import ErrorException


class Knitspeak_Compiler:
    """
    A class used to compile knit graphs from knitspeak
    """

    def __init__(self, carrier_id: int):
        self._parser = KnitSpeak_Interpreter()
        self.parse_results: List[Dict[str, Union[List[int, Num_Closure, Iterator_Closure], List[tuple]]]] = []
        self.course_ids_to_operations: Dict[int, List[tuple]] = {}
        self.knit_graph = Knit_Graph()
        self.yarn = Yarn("yarn", self.knit_graph, carrier_id = carrier_id)
        self.knit_graph.add_yarn(self.yarn)
        self.last_course_loop_ids: List[int] = []
        self.cur_course_loop_ids: List[int] = []
        self.current_row = 0
        self.loop_ids_consumed_by_current_course: Set[int] = set()

        self.tube_front_to_back_offset: int = 0
        self.last_course_loop_ids_temp: List[int] = []
        self.is_cur_on_front_bed: bool
        self.is_cur_row: bool
        self.is_cur_round: bool
        self.terminated: bool
        self.row_count: int

        self.number_of_left_leaning_front_half: int
        self.number_of_right_leaning_front_half: int
        self.number_of_left_leaning_back_half: int
        self.number_of_right_leaning_back_half: int

    def _increment_current_row(self):
        """
        Increments the current row by 1 and manages its state in the symbol table
        """
        self.current_row += 1
        self._parser.parser.symbolTable["current_row"] = self.current_row

    @property
    def _working_ws(self) -> bool:
        """
        :return: true if currently compiling a wrong-side row
        """
        return self.current_row % 2 == 0

    def get_course_walking_direction(self):
        print(f'self._parser.parser.symbolTable._symbol_table["round_courses"] is {self._parser.parser.symbolTable._symbol_table["round_courses"]},\
              self._parser.parser.symbolTable._symbol_table["row_courses"] is {self._parser.parser.symbolTable._symbol_table["row_courses"]}')
        for course_id in self._parser.parser.symbolTable._symbol_table["round_courses"]:
            self.knit_graph.course_id_to_walking_direction[course_id] = 'clockwise' 
        row_courses = sorted(self._parser.parser.symbolTable._symbol_table["row_courses"])
        print(f'sorted row_course is {row_courses}')
        for course_id in row_courses:
            # print(f'self.knit_graph.course_id_to_walking_direction is {self.knit_graph.course_id_to_walking_direction}')
            if course_id == 1:
                self.knit_graph.course_id_to_walking_direction[course_id] = 'counter-clockwise'
            elif (course_id - 1) in self._parser.parser.symbolTable._symbol_table["round_courses"]:
                self.knit_graph.course_id_to_walking_direction[course_id] = 'counter-clockwise'
            elif (course_id - 1) in self._parser.parser.symbolTable._symbol_table["row_courses"]:
                direction_last_row = self.knit_graph.course_id_to_walking_direction[course_id-1]
                self.knit_graph.course_id_to_walking_direction[course_id] = 'clockwise' if direction_last_row == 'counter-clockwise' else 'counter-clockwise'
        print(f'in compiler, self.knit_graph.course_id_to_walking_direction is {self.knit_graph.course_id_to_walking_direction}')

    def compile(self, starting_width: int, row_count: int, object_type: str, pattern: str, patternIsFile: bool = False) -> Knit_Graph:
        """
        Populates the knit_graph based on the compiled instructions. May throw errors from compilation
        :param row_count: the number of rows to knit before completing, pattern may repeat or be incomplete
        :param starting_width: the number of loops used to create the 0th course
        :param pattern: the pattern as a string or in a file
        :param patternIsFile: True if pattern is provided in a file
        :return: the resulting compiled knit graph
        """
        self.row_count = row_count
        self.knit_graph.object_type = object_type
        if object_type == 'tube':
            if starting_width % 2 != 0:
                raise ErrorException(f'starting width is required to be an even number for tube')
        self.parse_results = self._parser.interpret(pattern, patternIsFile)
        # self.get_course_walking_direction()
        self._organize_courses()  # organize course instructions
        self.get_course_walking_direction()
        self.populate_0th_course(starting_width)  # populate the 0th course; note that it doesn't increase the self.current_row
        print(f'self._parser.parser.symbolTable is {self._parser.parser.symbolTable._symbol_table}, key is {self._parser.parser.symbolTable._symbol_table.keys()}')
        
        if object_type == 'tube':
            # divide the loops on the 0th course into two and place them into front and back beds accordingly
            for i in range(starting_width // 2):
                self.knit_graph.add_loop_to_front_part(i)
            for i in range(starting_width // 2, starting_width):
                self.knit_graph.add_loop_to_back_part(i)


        self.is_cur_on_front_bed = False  # 0th course is always a round and the last loop will land on the back bed
        self.terminated: bool = False
        for course_id in sorted(self.course_ids_to_operations):
            self._increment_current_row()
            self.terminated = False
            course_instructions = self.course_ids_to_operations[course_id]
            #----initialized count every time a new course begins
            self.number_of_left_leaning_front_half = 0
            self.number_of_right_leaning_front_half = 0
            self.number_of_left_leaning_back_half = 0
            self.number_of_right_leaning_back_half = 0
            #----
            self.is_cur_row = False
            self.is_cur_round = False
            if self.current_row in self._parser.parser.symbolTable._symbol_table["row_courses"]:
                self.is_cur_row = True
                self.knit_graph.course_to_row[course_id] = True
            elif self.current_row in self._parser.parser.symbolTable._symbol_table["round_courses"]:
                self.is_cur_round = True
                self.knit_graph.course_to_row[course_id] = False
                #--deprecated when test pattern haha
                # if self.is_cur_on_front_bed:  # if last course is row and this course is round
                #     # we need to reverse direction since round is always clock-wise
                #     self.last_course_loop_ids.reverse()
                #     self.last_course_loop_ids_temp.reverse()
                # self.is_cur_on_front_bed = True
                #---
            else:
                raise ErrorException(f"Cannot find row: {self.current_row} in the symbol table")

            self.tube_front_to_back_offset = 0
            for instruction in course_instructions:
                print(f'in compile, course id is {course_id}, instruction is {instruction}')
                self._process_instruction(instruction)
                # if self.terminated:
                #     print(f'in compile, terminated at course id is {course_id}, instruction is {instruction}')
                #     break
            #----
            # while not self.terminated:
            #     for instruction in course_instructions:
            #         print(f'in compile, course id is {course_id}, instruction is {instruction}')
            #         self._process_instruction(instruction)       
            #----
            self.last_course_loop_ids = self.cur_course_loop_ids
            self.last_course_loop_ids_temp = self.last_course_loop_ids.copy()
            self.knit_graph.course_to_loop_ids_including_slip[course_id] = self.cur_course_loop_ids
            self.cur_course_loop_ids = []
            self.loop_ids_consumed_by_current_course = set()
            
            # if self.terminated and self.current_row != row_count:
            #     raise ErrorException("\nPop from an empty list before the whole instructions are processed." + 
            #         "\nTrailing redundant knit instructions in the last course are automatically trimmed" +
            #         "\nCheck if there are too many knit instructions in your knitspeak before the last course!")

            # elif self.terminated:
            #     break

            #----
            # self.terminated: bool = False
            #----

        return self.knit_graph

    def populate_0th_course(self, starting_width: int):
        """
        Populates the first course of the knitgraph with starting_width loops.
        Adds loop_ids in yarn-wise order to self.last_course_loop_ids
        :param starting_width: the number of loops to create
        """
        for i in range(0, starting_width):
            loop_id, loop = self.yarn.add_loop_to_end()
            self.knit_graph.add_loop(loop)
            self.last_course_loop_ids.append(loop_id) 
            self.last_course_loop_ids_temp.append(loop_id)

    def _organize_courses(self):
        """
        takes the parser results and organizes the course instructions by their course ids.
        raises two possible errors
         If a course is defined more than once, raise an error documenting the course_id
         If a course between 1 and the maximum course is not defined, raise an error documenting the course_id
        Note that all closures in these ids are executed before the row operations (may cause implementation confusion)
        """
        print(f'self.parse_results is {self.parse_results}')
        for instructions in self.parse_results:
            course_ids = instructions["courseIds"]
            course_instructions = instructions["stitch-operations"]
            for course_id in course_ids:
                if isinstance(course_id, Num_Closure):
                    course_id = course_id.to_int()  # converts any variable numbers to their current state
                    if course_id in self.course_ids_to_operations:
                        raise ErrorException(f"KnitSpeak Error: Course {course_id} is defined more than once")
                    self.course_ids_to_operations[course_id] = course_instructions
                elif isinstance(course_id, Iterator_Closure):  # closes iteration over variable numbers
                    sub_courses = course_id.to_int_list()
                    for sub_id in sub_courses:
                        if sub_id in self.course_ids_to_operations:
                            raise ErrorException(f"KnitSpeak Error: Course {sub_id} is defined more than once")
                        self.course_ids_to_operations[sub_id] = course_instructions
                else:  # course_id is integer
                    if course_id in self.course_ids_to_operations:
                        raise ErrorException(f"KnitSpeak Error: Course {course_id} is defined more than once")
                    self.course_ids_to_operations[course_id] = course_instructions
        # max_course = max([*self.course_ids_to_operations])
        max_course = self.row_count
        if "all_rs_rows" in self._parser.parser.symbolTable:
            course_instructions = self.course_ids_to_operations[1]
            for course_id in range(3, max_course + 1, 2):
                if course_id not in self.course_ids_to_operations:
                    self.course_ids_to_operations[course_id] = course_instructions
                    self._parser.parser.symbolTable._symbol_table["row_courses"].add(course_id)
                else:
                    print(f"KnitSpeak Warning: course {course_id} overrides rs-instructions")
        if "all_rs_rounds" in self._parser.parser.symbolTable:
            course_instructions = self.course_ids_to_operations[1]
            for course_id in range(3, max_course + 1, 2):
                if course_id not in self.course_ids_to_operations:
                    self.course_ids_to_operations[course_id] = course_instructions
                    self._parser.parser.symbolTable._symbol_table["round_courses"].add(course_id)
                else:
                    print(f"KnitSpeak Warning: course {course_id} overrides rs-instructions")
        if "all_ws_rows" in self._parser.parser.symbolTable:
            course_instructions = self.course_ids_to_operations[2]
            for course_id in range(4, max_course + 1, 2):
                if course_id not in self.course_ids_to_operations:
                    self.course_ids_to_operations[course_id] = course_instructions
                    self._parser.parser.symbolTable._symbol_table["row_courses"].add(course_id)
                else:
                    print(f"KnitSpeak Warning: course {course_id} overrides ws-instructions")
        if "all_ws_rounds" in self._parser.parser.symbolTable:
            course_instructions = self.course_ids_to_operations[2]
            for course_id in range(4, max_course + 1, 2):
                if course_id not in self.course_ids_to_operations:
                    self.course_ids_to_operations[course_id] = course_instructions
                    self._parser.parser.symbolTable._symbol_table["round_courses"].add(course_id)
                else:
                    print(f"KnitSpeak Warning: course {course_id} overrides ws-instructions")

        for course_id in range(1, max_course + 1):
            if course_id not in self.course_ids_to_operations:
                raise ErrorException(f"KnitSpeak Error: Course {course_id} is undefined")

        if max_course % 2 == 1 and ("all_ws_rows" in self._parser.parser.symbolTable or "all_ws_rounds" in self._parser.parser.symbolTable):  # ends on rs row
            self.course_ids_to_operations[max_course + 1] = self.course_ids_to_operations[2]

        print(f'self.course_ids_to_operations is {self.course_ids_to_operations}')
        
    def _process_instruction(self, instruction: Tuple[Union[tuple, Stitch_Definition, Cable_Definition, Increase_Stitch_Definition, list],
                                                      Tuple[bool, int]]):
        """
        :param instruction: A tuple with the knitting instructions and information about how to repeat them
        instruction[0] can be a stitch definition, cable definition, or a list of instruction tuples
        instruction[1] is a tuple with a boolean and an int.
         If the boolean is true, then the integer represents the number of times to repeat the instructions
         If the boolean is false, then the integer represents the number of loops left after executing the instructions
        :return:
        """ 
        # [([(1-BtF-c0->1, (True, 2)), (2-BtF-c0->1, (True, 1)), (1-BtF-c0->1, (True, 1))], (False, 0))]
        print(f'in _process_instruction, instruction is {instruction}, action is {instruction[0]}, static_repeats is {instruction[1][0]}')
        action = instruction[0]
        is_stitch = isinstance(action, Stitch_Definition)
        is_cable = isinstance(action, Cable_Definition)
        is_list = type(action) is list
        static_repeats = instruction[1][0]
        repeats = 1
        if static_repeats:
            repeats = instruction[1][1]
            if isinstance(repeats, Num_Closure):
                repeats = repeats.to_int()
        remaining_loops = 0
        if not static_repeats:
            remaining_loops = instruction[1][1]
            if isinstance(remaining_loops, Num_Closure):
                remaining_loops = remaining_loops.to_int() #(1-BtF-c0->1, (True, 2)) However, the to_int in Num_Closure has not been implemented from the very begining, I think this is bc it usually not used in the knitspeak grammer. so the remaining_loops is always 0.

        def execute_instructions():
            """
            Executes the action according to its type
            """
            if is_stitch:
                print('is stitch')
                self._process_stitch(action)
            elif is_cable:
                print('is cable')
                self._process_cable(action)
            elif is_list:
                print('is list')
                self._process_list(action)
            else:
                self._process_instruction(action)

        if not static_repeats:  # need to iterate until remaining loops is left
            print(f'not static_repeats, self.terminated is {self.terminated}')
            if remaining_loops != 0:
                while (len(self.last_course_loop_ids) - len(self.cur_course_loop_ids)) > remaining_loops and not self.terminated: #here we add not self.terminated because ks like
                    # this --- tube_pattern = r''' 1st round [k 2, skpo, k] to end. ''' will fall into a non-stoppable execution since the len(cur course loop) is smaller than len(last course loops) but the last_course_loop_ids_temp has already been consumed up.
                    # later, I found this is not enough, bc when there is ks like "1st round k, yo, [k 2, p 2] to end.", the first condition (i.e. len_last - len_cur > 0) will break before consuming up the last node on the last course. so consider relax the first condition.
                # while not self.terminated:
                    print(f'in not static_repeats statement, self.terminated is {self.terminated}, remain_loop is {remaining_loops}')
                    execute_instructions()
                    print('exit not static_repeats')
                # assert remaining_loops == (len(self.last_course_loop_ids) - len(self.cur_course_loop_ids)) #not always hold true for the same reason as above
            else:
                while not self.terminated:
                    print(f'in not static_repeats statement, self.terminated is {self.terminated}, remain_loop is {remaining_loops}')
                    execute_instructions()
                    print('exit not static_repeats')
        else:
            if not self.terminated:
                print(f'is static_repeats, repeats is {repeats}, remain_loop is {remaining_loops}')
                for _ in range(0, repeats):
                    execute_instructions()
                print('exit static_repeats')

    def _process_stitch(self, stitch_def: Stitch_Definition, flipped_by_cable=False):
        """
        Uses a stitch definition and compiler state to generate a new loop and connect it to the prior course.
        May throw two compiler errors.
         if there is no loop at the parent offsets of the stitch, then throw an error reporting the missing index
         if a parent loop has already been consumed, then throw an error reporting the misused parent loop
        :param flipped_by_cable: if True, implies that this stitch came from a cable and has been flipped appropriately
        :param stitch_def: the stitch definition used to connect the new loop
        """

        # if self._working_ws and ("all_rs_rounds" not in self._parser.parser.symbolTable) and ("all_ws_rounds" not in self._parser.parser.symbolTable) and ('round' not in self._parser.parser.symbolTable) and not flipped_by_cable:  # flips stitches following hand-knitting conventions
        #     stitch_def = stitch_def.copy_and_flip()

        def is_on_front_bed_for_tube(graph: Knit_Graph, parent_node: int) -> bool:
            return parent_node in graph.loops_on_front_part_of_the_tube

        def count_num_of_cur_course_loops_on_front(graph: Knit_Graph) -> int:
            num_on_front = 0
            for loop_id in self.cur_course_loop_ids:
                if is_on_front_bed_for_tube(self.knit_graph, loop_id):
                    num_on_front+=1
            return num_on_front
        
        if self._working_ws and self.is_cur_row and not flipped_by_cable:  # flips stitches following hand-knitting conventions
            stitch_def = stitch_def.copy_and_flip()

        if stitch_def.child_loops >= 1:
            if flipped_by_cable == True:
                print('in flipped_by_cable')
                parent_loops = []
                number_of_parents = len(stitch_def.offset_to_parent_loops)
                print(f'number_of_parents is {number_of_parents}')
                for i in range(number_of_parents):
                    print(f'i is {i}, len(self.last_course_loop_ids_temp) is {len(self.last_course_loop_ids_temp)}')
                    if len(self.last_course_loop_ids_temp) < 1 and number_of_parents != 0: #make sure this is not yo
                        self.terminated = True
                        print(f'self.terminated is {self.terminated}')
                        return
                    if self.is_cur_row:
                        for stack_position, parent_offset in enumerate(stitch_def.offset_to_parent_loops):
                            print(f'the parent offset of cable stitch is {parent_offset}')
                            
                            if parent_offset < 0:
                                parent_loops.append(self.last_course_loop_ids_temp.pop(-1+parent_offset))
                            else:
                                parent_loops.append(self.last_course_loop_ids_temp.pop())
                
                            # if parent_offset > 0:
                            #     parent_loops.append(self.last_course_loop_ids_temp.pop(parent_offset))
                            # else:
                            #     parent_loops.append(self.last_course_loop_ids_temp.pop())
                    elif self.is_cur_round:
                        for stack_position, parent_offset in enumerate(stitch_def.offset_to_parent_loops):
                            if parent_offset < 0:
                                parent_offset = len(self.cur_course_loop_ids) - len(self.loop_ids_consumed_by_current_course) - stitch_def.offset_to_parent_loops[0]
                                parent_loops.append(self.last_course_loop_ids_temp.pop(parent_offset))
                            else:
                                parent_loops.append(self.last_course_loop_ids_temp.pop(0))
                            print(f'the parent offset of cable stitch is {parent_offset}, stitch_def.offset_to_parent_loops[0] is {stitch_def.offset_to_parent_loops[0]}')
                loop_id, loop = self.yarn.add_loop_to_end()
                print(f'in _process_stitch, loop id added on the yarn is {loop_id}, len(self.last_course_loop_ids_temp) is {len(self.last_course_loop_ids_temp)}, \
                    self.terminated is {self.terminated}')
                print(f'in _process_stitch, parent_loops is {parent_loops}')

                self.knit_graph.add_loop(loop)
                self.cur_course_loop_ids.append(loop_id)
        
                for stack_position, parent_loop in enumerate(parent_loops):
                    self.loop_ids_consumed_by_current_course.add(parent_loop)
                    if self.is_cur_row:
                        reversed_list = self.last_course_loop_ids[::-1]
                        parent_offset = len(self.cur_course_loop_ids) - (reversed_list.index(parent_loop)+1)
                    else:
                        #not reversed
                        parent_offset = (len(self.cur_course_loop_ids) - (self.last_course_loop_ids.index(parent_loop)+1))
                    if self.knit_graph.object_type == "sheet":
                        if self.current_row % 2 == 0:
                            parent_offset = -parent_offset
                    elif self.knit_graph.object_type == "tube":
                        if self.is_cur_row:
                            if self.current_row % 2 == 0:
                                parent_offset = -parent_offset

                        if len(self.loop_ids_consumed_by_current_course) < 1 or is_on_front_bed_for_tube(self.knit_graph, parent_loop):
                            parent_offset = -parent_offset  # negate when in front bed
                        
                        # if we are switching from front bed to back bed
                        if len(self.loop_ids_consumed_by_current_course) > 0 and self.is_cur_on_front_bed and \
                                not is_on_front_bed_for_tube(self.knit_graph, parent_loop):
                            self.is_cur_on_front_bed = False
                            self.tube_front_to_back_offset = -parent_offset

                        # if we are switching from back bed to front bed
                        if len(self.loop_ids_consumed_by_current_course) > 0 and not self.is_cur_on_front_bed and \
                                is_on_front_bed_for_tube(self.knit_graph, parent_loop):
                            self.is_cur_on_front_bed = True
                            self.tube_front_to_back_offset = -parent_offset

                    parent_offset += self.tube_front_to_back_offset
                    
                    self.knit_graph.connect_loops(parent_loop, loop_id, stitch_def.pull_direction,
                                                stack_position, stitch_def.cabling_depth, parent_offset)
                    print(f"loop_id is: {loop_id}")
                    print(f"parent_loop_id is: {parent_loop}")
                    print(f"parent_offset is: {parent_offset}")
                    print(f"self.cur_course_loops is: {self.cur_course_loop_ids}")
                    print(f"self.loop_ids_comsumed_by_current_course is: {self.loop_ids_consumed_by_current_course}")
                    print(f"self.last_course_loops is: {self.last_course_loop_ids}")
                    print(f"self.last_course_loops_temp is: {self.last_course_loop_ids_temp}") 
            else:
                parent_loops = []
                number_of_parents = len(stitch_def.offset_to_parent_loops)
                print(f'number_of_parents is {number_of_parents}')
                for i in range(number_of_parents):
                    print(f'i is {i}, len(self.last_course_loop_ids_temp) is {len(self.last_course_loop_ids_temp)}')
                    if len(self.last_course_loop_ids_temp) < 1 and number_of_parents != 0:
                        self.terminated = True
                        print(f'self.terminated is {self.terminated}')
                        return
                    if self.is_cur_row:
                        parent_loops.append(self.last_course_loop_ids_temp.pop())
                    elif self.is_cur_round:
                        parent_loops.append(self.last_course_loop_ids_temp.pop(0))
                loop_id, loop = self.yarn.add_loop_to_end()
                print(f'in _process_stitch, loop id added on the yarn is {loop_id}, len(self.last_course_loop_ids_temp) is {len(self.last_course_loop_ids_temp)}, \
                    self.terminated is {self.terminated}')
                print(f'in _process_stitch, parent_loops is {parent_loops}')

                self.knit_graph.add_loop(loop)
                self.cur_course_loop_ids.append(loop_id)
                if number_of_parents == 0: # a yarn over
                    # if we want to position the yo node that bridges the front and back part on the back part (coupled with a code block below)
                    #-----
                    # if we are switching from front bed to back bed
                    # if len(self.loop_ids_consumed_by_current_course) > 0 and self.is_cur_on_front_bed and \
                    # not self.last_course_loop_ids_temp[0] in self.knit_graph.loops_on_front_part_of_the_tube:
                    #     self.is_cur_on_front_bed = False
                    #     self.cur_course_loop_ids = [loop_id]
                    #     self.loop_ids_consumed_by_current_course = set()
                    #-----
                
                    # print(f'self.last_course_loop_ids_temp[0] is {self.last_course_loop_ids_temp[0]}')
                    print(f"loop_id is: {loop_id}")
                    print(f"self.cur_course_loops is: {self.cur_course_loop_ids}")
                    print(f"self.loop_ids_comsumed_by_current_course is: {self.loop_ids_consumed_by_current_course}")
                    print(f"self.last_course_loops is: {self.last_course_loop_ids}")
                    print(f"self.last_course_loops_temp is: {self.last_course_loop_ids_temp}")     

                for stack_position, parent_loop in enumerate(parent_loops):
                    self.loop_ids_consumed_by_current_course.add(parent_loop)

                    parent_offset = len(self.cur_course_loop_ids) - len(self.loop_ids_consumed_by_current_course)

                    if self.knit_graph.object_type == "sheet":
                        if self.current_row % 2 == 0:
                            parent_offset = -parent_offset
                    elif self.knit_graph.object_type == "tube":
                        if self.is_cur_row:
                            if self.current_row % 2 == 0:
                                parent_offset = parent_offset #originally parent_offset = -parent_offset

                        if len(self.loop_ids_consumed_by_current_course) < 1 or is_on_front_bed_for_tube(self.knit_graph, parent_loop):
                            parent_offset = -parent_offset  # negate when in front bed
                        
                        # if we are switching from front bed to back bed
                        if len(self.loop_ids_consumed_by_current_course) > 0 and self.is_cur_on_front_bed and \
                                not is_on_front_bed_for_tube(self.knit_graph, parent_loop):
                            self.is_cur_on_front_bed = False
                            self.tube_front_to_back_offset = -parent_offset

                        # if we are switching from back bed to front bed
                        if len(self.loop_ids_consumed_by_current_course) > 0 and not self.is_cur_on_front_bed and \
                                is_on_front_bed_for_tube(self.knit_graph, parent_loop):
                            self.is_cur_on_front_bed = True
                            self.tube_front_to_back_offset = -parent_offset

                    parent_offset += self.tube_front_to_back_offset
                    
                    if len([*self.knit_graph.graph.successors(parent_loop)]) == 0:
                        self.knit_graph.connect_loops(parent_loop, loop_id, stitch_def.pull_direction,
                                                    stack_position, stitch_def.cabling_depth, parent_offset)
                    print(f"loop_id is: {loop_id}")
                    print(f"parent_loop_id is: {parent_loop}")
                    print(f"parent_offset is: {parent_offset}")
                    print(f"self.cur_course_loops is: {self.cur_course_loop_ids}")
                    print(f"self.loop_ids_comsumed_by_current_course is: {self.loop_ids_consumed_by_current_course}")
                    print(f"self.last_course_loops is: {self.last_course_loop_ids}")
                    print(f"self.last_course_loops_temp is: {self.last_course_loop_ids_temp}") 
                    print(f'stitch_def.offset_to_parent_loops[0] is {stitch_def.offset_to_parent_loops[0]}')  
            #---
            if len(stitch_def.offset_to_parent_loops) != 0 and abs(stitch_def.offset_to_parent_loops[0]) == 0.01:
                print('this is a cast-off stitch')
                previous_loop_on_this_course = self.cur_course_loop_ids[-2]
                self.knit_graph.connect_loops(previous_loop_on_this_course, loop_id, stitch_def.pull_direction,
                                                stack_position, stitch_def.cabling_depth, 1) #parent offset = -1
            #----          

        else:  # slip statement
            print(f'is a slip stitch')
            if self.is_cur_row:
                parent_loop = self.last_course_loop_ids_temp.pop()
            elif self.is_cur_round:
                parent_loop = self.last_course_loop_ids_temp.pop(0)
            self.cur_course_loop_ids.append(parent_loop)
            self.loop_ids_consumed_by_current_course.add(parent_loop)
            print(f"loop_id is: {parent_loop}")
            print(f"self.cur_course_loops is: {self.cur_course_loop_ids}")
            print(f"self.loop_ids_comsumed_by_current_course is: {self.loop_ids_consumed_by_current_course}")
            print(f"self.last_course_loops is: {self.last_course_loop_ids}")
            print(f"self.last_course_loops_temp is: {self.last_course_loop_ids_temp}")      
            # if len(self.last_course_loop_ids_temp) < 1:
            #     self.terminated = True
            #     print(f'self.terminated is {self.terminated}')
            #     return
        
        # check which bed to put the current loop to
        if stitch_def.child_loops == 1:  # when it's not a slip and has a parent
            predecessors = [*self.knit_graph.graph.predecessors((loop_id))]
            if len(predecessors) > 0:
                #----
                if stitch_def.is_decrease:
                    predecessors_all_on_front = True
                    for predecessor in predecessors:
                        if predecessor not in self.knit_graph.loops_on_front_part_of_the_tube:
                            predecessors_all_on_front = False
                    is_left_leaning = True
                    for offset in stitch_def.offset_to_parent_loops:
                        if offset > 0: 
                            is_left_leaning = False
                    if predecessors_all_on_front and is_left_leaning:
                        self.number_of_left_leaning_front_half += 1
                        self.knit_graph.courses_to_number_of_left_leaning_front_half[self.current_row] = self.number_of_left_leaning_front_half
                        self.knit_graph.courses_to_max_loop_id_left_leaning_front_half[self.current_row] = loop_id
                    elif (not predecessors_all_on_front) and is_left_leaning:
                        self.number_of_right_leaning_back_half += 1
                        self.knit_graph.courses_to_number_of_right_leaning_back_half[self.current_row] = self.number_of_right_leaning_back_half #"right" when we view from the front side of the KnitGraph
                        self.knit_graph.courses_to_max_loop_id_right_leaning_back_half[self.current_row] = loop_id
                    elif predecessors_all_on_front and (not is_left_leaning):
                        self.number_of_right_leaning_front_half += 1
                        self.knit_graph.courses_to_number_of_right_leaning_front_half[self.current_row] = self.number_of_right_leaning_front_half
                        self.knit_graph.courses_to_max_loop_id_right_leaning_front_half[self.current_row] = loop_id
                    else:
                        self.number_of_left_leaning_back_half += 1                        
                        self.knit_graph.courses_to_number_of_left_leaning_back_half[self.current_row] = self.number_of_left_leaning_back_half #"left" when we view from the front side of the KnitGraph
                        self.knit_graph.courses_to_max_loop_id_left_leaning_back_half[self.current_row] = loop_id
                #----
                if predecessors[0] in self.knit_graph.loops_on_front_part_of_the_tube:
                    self.knit_graph.add_loop_to_front_part(loop_id)
                elif predecessors[0] in self.knit_graph.loops_on_back_part_of_the_tube:
                    self.knit_graph.add_loop_to_back_part(loop_id)
                elif self.is_cur_row == False:
                    raise ErrorException(f"Predecessor of loop{loop_id} can not be found on either bed")
            else:  # its parent is a yarn over loop
                if self.is_cur_row:
                    print('yo on row')
                    if self.last_course_loop_ids_temp[-1] in self.knit_graph.loops_on_front_part_of_the_tube:
                        self.knit_graph.add_loop_to_front_part(loop_id)
                        #here we write down the loop_index for yarn over loop; If it is on a round, then the loop index needs to return to zero for both the front and back part
                        self.knit_graph.add_index_for_yarn_over_loop(loop_id, index = len(self.cur_course_loop_ids)-1)
                    else:
                        self.knit_graph.add_loop_to_back_part(loop_id)
                        self.knit_graph.add_index_for_yarn_over_loop(loop_id, index = len(self.cur_course_loop_ids)-count_num_of_cur_course_loops_on_front(self.knit_graph)-1)
                elif self.is_cur_round:
                    #this will position the yo node that bridges the front and back part on the back part
                    # if len(self.last_course_loop_ids_temp) != 0 and self.last_course_loop_ids_temp[0] in self.knit_graph.loops_on_front_part_of_the_tube: 
                        # self.knit_graph.add_loop_to_front_part(loop_id)
                        # self.knit_graph.add_index_for_yarn_over_loop(loop_id, index = len(self.cur_course_loop_ids)-1)
                    #---

                    #this will position the yo node that bridges the front and back part on the front part    
                    #---                
                    last_node_index_on_front_part_of_the_tube = len(self.last_course_loop_ids) - len(self.last_course_loop_ids_temp) - 1
                    last_node_on_front_part_of_the_tube = self.last_course_loop_ids[last_node_index_on_front_part_of_the_tube]
                    if last_node_on_front_part_of_the_tube in self.knit_graph.loops_on_front_part_of_the_tube: 
                        self.knit_graph.add_loop_to_front_part(loop_id)
                        self.knit_graph.add_index_for_yarn_over_loop(loop_id, index = len(self.cur_course_loop_ids) - 1)
                    #---
                    else:
                        self.knit_graph.add_loop_to_back_part(loop_id)
                        self.knit_graph.add_index_for_yarn_over_loop(loop_id, index = len(self.cur_course_loop_ids)-count_num_of_cur_course_loops_on_front(self.knit_graph)-1)
        #----
        if len(self.last_course_loop_ids_temp) < 1:
            self.terminated = True
            print(f'at last, self.terminated is {self.terminated}')
            return   
        #----

    def _process_cable(self, cable_def: Cable_Definition):
        """
        Uses a cable definition and compiler state to generate and connect a cable
        :param cable_def: the cable definition used to connect the cable into the knitgraph
        """
        original_cable_def = cable_def
        stitch_definitions = cable_def.stitch_definitions()
        if self._working_ws and ('round' not in self._parser.parser.symbolTable) and ("all_rs_rounds" not in self._parser.parser.symbolTable) and ("all_ws_rounds" not in self._parser.parser.symbolTable):  # flips cable by hand-knitting convention
            cable_def = cable_def.copy_and_flip()
            print(f'cable on ws, original cable def is {original_cable_def}, flipped cable def is {cable_def}')
            # for stitch_definition in stitch_definitions:
            #     stitch_definition.cabling_depth = stitch_definition.cabling_depth*(-1)  
        if 'round' not in self._parser.parser.symbolTable:
            for stitch_definition in stitch_definitions:
                print(f'in process_cable, stitch_def is {stitch_definition}, stitch_offset is {stitch_definition.offset_to_parent_loops[0]}, stitch_depth is {stitch_definition.cabling_depth}')
                self._process_stitch(stitch_definition, flipped_by_cable=True)
        if 'round' in self._parser.parser.symbolTable:
            cable_def = cable_def.copy_and_flip()
            stitch_definitions = cable_def.stitch_definitions()
            # stitch_definitions = [*reversed(stitch_definitions)]
            # print(f'reversed(stitch_definitions) is {[*reversed(stitch_definitions)]}, stitch_definitions is {stitch_definitions}')
            for stitch_definition in stitch_definitions:
                print(f'in process_cable, stitch_def is {stitch_definition}, stitch_offset is {stitch_definition.offset_to_parent_loops[0]}')
                self._process_stitch(stitch_definition, flipped_by_cable=True)



    def _process_list(self, action: List[tuple]):
        """
        Processes actions in a list of actions
        :param action: the list of actions
        """
        for sub_action in action:
            self._process_instruction(sub_action)