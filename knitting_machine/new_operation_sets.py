"""Sets of Operations that happen in groups of carriage passes"""
from enum import Enum
from typing import Optional, Dict, Set, List, Tuple

from knitting_machine.Machine_State import Needle, Pass_Direction, Yarn_Carrier, Machine_State
from knitting_machine.machine_operations import *


class Instruction_Type(Enum):
    """An enumerator for the different instruction types in Knitout"""
    Knit = "knit"
    Split = "split"
    Tuck = "tuck"
    Miss = "miss"
    Drop = "drop"
    Xfer = "xfer"
    Rack = "rack"

    def direction_must_be_consistent(self) -> bool:
        """
        :return: True if this instruction must be in a consistent carriage pass,
        (all left to right or all right to left),
        in a sorted order
        """
        return self.value in [Instruction_Type.Knit.value, Instruction_Type.Split.value,
                              Instruction_Type.Tuck.value, Instruction_Type.Miss.value]

    def direction_must_be_Left_to_Right(self) -> bool:
        """
        :return: True if the instruction must be in a left to right pass
        """
        return self.value == Instruction_Type.Drop

    def direction_does_not_matter(self) -> bool:
        """
        :return: True
        """
        return self.value in [Instruction_Type.Xfer.value, Instruction_Type.Rack.value]


class Instruction_Parameters:
    def __init__(self, needle_1: Needle, involved_loop: Optional[int] = None, needle_2: Optional[Needle] = None, carrier: Optional[Yarn_Carrier] = None,
                 comment: str = "", racking: Optional[int] = None):
        self._needle_1: Needle = needle_1
        self._involved_loop: Optional[int] = involved_loop
        self._needle_2: Optional[Needle] = needle_2
        self._carrier: Optional[Yarn_Carrier] = carrier
        self._racking: Optional[int] = racking
        self._comment: str = comment

    @property
    def carrier(self) -> Optional[Yarn_Carrier]:
        return self._carrier

    @property
    def no_yarn(self) -> bool:
        return self.carrier is None

    @property
    def comment(self):
        return self._comment

    @comment.setter
    def comment(self, comment: str):
        self._comment = comment

    def miss(self, direction: Pass_Direction):
        assert self._needle_1 is not None, "No Miss needle provided."
        # update below from "assert self.no_yarn, "No carrier to miss""
        assert self.no_yarn == False, "No carrier to miss"
        return miss(direction, self._needle_1, self._carrier, self.comment)

    def knit(self, machine_state: Machine_State, direction: Pass_Direction):
        assert self._needle_1 is not None, "No Needle to knit on"
        assert self._involved_loop is not None, "No loop_id provided"
        return knit(machine_state, direction, self._needle_1, self._carrier, self._involved_loop, self.comment)

    def tuck(self, machine_state: Machine_State, direction: Pass_Direction):
        assert self._needle_1 is not None, "No Needle to tuck on"
        assert self._involved_loop is not None, "No loop_id provided"
        return tuck(machine_state, direction, self._needle_1, self._carrier, self._involved_loop, self.comment)

    def split(self, machine_state: Machine_State, direction: Pass_Direction):
        assert self._needle_1 is not None, "No Needle to split from"
        assert self._needle_2 is not None, "No Needle to split to"
        assert self._involved_loop is not None, "No loop_id provided"
        return split(machine_state, direction, self._needle_1, self._needle_2, self._carrier, self._involved_loop, self.comment)

    def drop(self, machine_state: Machine_State):
        assert self._needle_1 is not None, "No Needle to tuck on"
        return drop(machine_state, self._needle_1, self.comment)

    def xfer(self, machine_state: Machine_State):
        assert self._needle_1 is not None, "No Needle to split from"
        assert self._needle_2 is not None, "No Needle to split to"
        return xfer(machine_state, self._needle_1, self._needle_2, self.comment)
    
    # def rack(self, machine_state: Machine_State) -> str:
    #     return rack(machine_state, self._racking, self.comment)

    def __hash__(self):
        return hash(self._needle_1)


class Carriage_Pass:
    """
    A class that represents a set of instructions made in one pass of the carriage

    ...

    Attributes
    ----------
    machine_state: Machine_State
        The machine that is updated while writing these instructions
    needles_to_instruction_parameters: Dict[Needle, Tuple[Optional[int], Optional[Needle]]]
        The needles each operation starts on mapped to either or both the loop_id created and the second needle involved
    """

    def __init__(self, direction: Optional[Pass_Direction],
                 needles_to_instruction_parameters_and_types: Optional[Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]]], machine_state: Machine_State, only_racking: Optional[bool] = False):
        """
        :param instruction_type: The type of instruction to be done in this pass
        :param direction: the direction the carriage will move for this pass
        :param needles_to_instruction_parameters:
            The starting needles mapped to the loop_id created and a second needle to xfer
        :param machine_state: The machine model to update as instructions are written
        """
        self.machine_state: Machine_State = machine_state
        self._carrier_set: Set[Yarn_Carrier] = set()
        self.only_racking = only_racking
        self._instruction_type: Instruction_Type = None
        self.needles_to_instruction_parameters_and_types: \
                Dict[Needle, Tuple[Instruction_Parameters, Instruction_Type]] = needles_to_instruction_parameters_and_types
        if needles_to_instruction_parameters_and_types != {}:
            # print(f'self.needles_to_instruction_parameters_and_types is {self.needles_to_instruction_parameters_and_types}')
            params_list  = []
            for (param, param_type) in self.needles_to_instruction_parameters_and_types.values():
                params_list.append(param)
            for params in params_list:
                if not params.no_yarn:
                    self._carrier_set.add(params.carrier)
            # randomly pick an instruction type to assign below, the reason we can do this is because we put instuction of same type in terms of required direction for carriage pass
            # print('test', [*self.needles_to_instruction_parameters_and_types.values()])
            if len([*self.needles_to_instruction_parameters_and_types.values()])!= 0:
                self._instruction_type = [*self.needles_to_instruction_parameters_and_types.values()][0][1]
        self._direction = direction
        if self.direction is None and self._instruction_type != None:
            if self._instruction_type.direction_must_be_Left_to_Right():
                self._direction = Pass_Direction.Left_to_Right
            elif self._instruction_type.direction_must_be_consistent():
                self._direction = self.machine_state.last_carriage_direction.opposite()  # switch from last pass
            elif self._instruction_type.direction_must_be_Left_to_Right():
                assert self.direction.value == Pass_Direction.Left_to_Right.value, "Can only Drop on + (left to right) pass"

    # @property
    def instruction_type(self, needle: Needle) -> Instruction_Type:
        """
        :return: The instruction type in this pass
        """
        return self.needles_to_instruction_parameters_and_types[needle][1]

    @property
    def direction(self) -> Pass_Direction:
        """
        :return: the direction the carriage will move to complete this pass
        """
        return self._direction

    @property
    def carrier_set(self) -> Set[Yarn_Carrier]:
        """
        :return: the set of carriers involved in these instructions
        """
        return self._carrier_set

    def _sorted_needles(self) -> List[Needle]:
        needles = [*self.needles_to_instruction_parameters_and_types]
        # print('needles', needles)
        # needles_to_involved_loop_id = {}
        # involved_loop =  self.needles_to_instruction_parameters_and_types[needles[0]][0]._involved_loop
        # if (self._instruction_type == Instruction_Type.Knit or self._instruction_type == Instruction_Type.Split) and involved_loop != -1: 
        #     for needle in needles:
        #         needles_to_involved_loop_id[needle] = self.needles_to_instruction_parameters_and_types[needle][0]._involved_loop
        #     sorted_needles_to_involved_loop_id = {k: v for k, v in sorted(needles_to_involved_loop_id.items(), key=lambda item: item[1])}
        #     sorted_needle_by_loop_id = [*sorted_needles_to_involved_loop_id.keys()]
        #     return sorted_needle_by_loop_id
        # else:
        sorted_left_to_right = sorted(needles)
        if self.direction is Pass_Direction.Right_to_Left:
            print(f'direction should be -, actual direction is {self.direction}')
            return [*reversed(sorted_left_to_right)]
        elif self.direction is Pass_Direction.Left_to_Right:
            print(f'direction should be +, actual direction is {self.direction}')
            return sorted_left_to_right
        else:
            print(f'direction should be None, actual direction is {self.direction}')
            return sorted_left_to_right
            

    def _write_instruction(self, needle: Needle) -> str:
        """
        :param needle: the first (or only) needle that an instruction uses
        :return: The string for the line of code executing the instruction
        """
        # print(self.instruction_type(needle))
        print(f'direction is {self._direction}, instruction_types is {self.needles_to_instruction_parameters_and_types[needle][1]}, needle is {needle}, carrier is {self.needles_to_instruction_parameters_and_types[needle][0].carrier}, involved loop is {self.needles_to_instruction_parameters_and_types[needle][0]._involved_loop}')
        if self.instruction_type(needle).value == Instruction_Type.Knit.value:
            return self.needles_to_instruction_parameters_and_types[needle][0].knit(self.machine_state, self.direction)
        elif self.instruction_type(needle).value == Instruction_Type.Tuck.value:
            return self.needles_to_instruction_parameters_and_types[needle][0].tuck(self.machine_state, self.direction)
        elif self.instruction_type(needle).value == Instruction_Type.Split.value:
            return self.needles_to_instruction_parameters_and_types[needle][0].split(self.machine_state, self.direction)
        elif self.instruction_type(needle).value == Instruction_Type.Drop.value:
            return self.needles_to_instruction_parameters_and_types[needle][0].drop(self.machine_state)
        elif self.instruction_type(needle).value == Instruction_Type.Xfer.value:
            return self.needles_to_instruction_parameters_and_types[needle][0].xfer(self.machine_state)
        elif self.instruction_type(needle).value == Instruction_Type.Miss.value:
            return self.needles_to_instruction_parameters_and_types[needle][0].miss(self.direction)
        else:
            assert False, "The instruction was not recognized"

    def write_instructions(self, first_comment="", comment="") -> List[str]:
        """
        :param first_comment: A comment to add to the first instruction in the pass
        :param comment: A comment to add to every instruction in the pass
        :return: A list of knitout instructions that executes the instruction on each needle
        """
        
        # bring in yarns that are not yet in operation
        instructions = []
        in_hooked_carriers = set()
        for carrier in self.carrier_set:
            for sub_carrier in carrier.not_in_operation(self.machine_state):
                if sub_carrier not in self.machine_state.yarns_in_operation:  # bring new yarns needed in
                    in_hooked_carriers.add(sub_carrier)
                    instructions.append(inhook(self.machine_state, sub_carrier))
        if self.only_racking == False:
            starting_needles = self._sorted_needles()
            print('starting_needles(sorted)', starting_needles)
            for needle in starting_needles:
                if len(instructions) == 0:
                    c = first_comment
                else:
                    c = comment
                instruction = self._write_instruction(needle)
                instructions.append(instruction)
        else:
            instruction = rack(self.machine_state, racking = 0)
            instructions.append(instruction)
        # self.machine_state.last_carriage_direction = self.direction
        # release hooks on second pass with inhooks
        for carrier in [*self.machine_state.in_hooks]:
            if carrier not in in_hooked_carriers:  # don't release hook on first pass with in hook
                instructions.append(releasehook(self.machine_state, carrier))
        return instructions
