"""Cable Definition is used to construct different cable structures"""
from typing import List

from knit_graphs.Knit_Graph import Pull_Direction
from knitspeak_compiler.knitspeak_interpreter.stitch_definitions import Stitch_Definition, Stitch_Lean


    
class Left_Lean_CastOn_Stitch_Definition:
    def __init__(self, pull_direction: Pull_Direction = Pull_Direction.BtF, cabling_depth: int = 0,
                 offset_to_parent_loops = [], child_loops: int = 1):
        self.child_loops = child_loops
        self.offset_to_parent_loops: List[int] = offset_to_parent_loops
        self.pull_direction: Pull_Direction = pull_direction
        self.cabling_depth = cabling_depth
    
    def __str__(self):
        return f"LeftLeanCO"

class Right_Lean_CastOn_Stitch_Definition:
    def __init__(self, pull_direction: Pull_Direction = Pull_Direction.BtF, cabling_depth: int = 0,
                 offset_to_parent_loops = [], child_loops: int = 1):
        self.child_loops = child_loops
        self.offset_to_parent_loops: List[int] = offset_to_parent_loops
        self.pull_direction: Pull_Direction = pull_direction
        self.cabling_depth = cabling_depth 

    def __str__(self):
        return f"RightLeanCO"


class Left_Lean_Stitch_Definition:
    def __init__(self, inc_lean: Stitch_Lean = Stitch_Lean.Left, lean_offset: int = 1, lean_stitch_pull_direction: Pull_Direction = Pull_Direction.BtF, child_loops: int =1, \
                 cabling_depth: int = 0):
        self._lean = inc_lean
        self._lean_offset = lean_offset
        self.pull_direction = lean_stitch_pull_direction
        self.child_loops = child_loops
        self.offset_to_parent_loops: List[int] = [0]
        self.cabling_depth = cabling_depth
        
    def __str__(self):
        return f"{self._lean}-Lean"

class Right_Lean_Stitch_Definition:
    def __init__(self, inc_lean: Stitch_Lean = Stitch_Lean.Right, lean_offset: int = -1, lean_stitch_pull_direction: Pull_Direction = Pull_Direction.BtF, child_loops: int =1, \
                 cabling_depth: int = 0):
        self._lean = inc_lean
        self._lean_offset = lean_offset
        self.pull_direction = lean_stitch_pull_direction
        self.child_loops = child_loops
        self.offset_to_parent_loops: List[int] = [0]
        self.cabling_depth = cabling_depth
        
    def __str__(self):
        return f"{self._lean}-Lean"
    
class Increase_Stitch_Definition:
    """
    A class used to organize associated stitch definitions in a cable
    """

    def __init__(self, inc_lean: Stitch_Lean = Stitch_Lean.Left, lean_stitch_pull_direction: Pull_Direction = Pull_Direction.BtF
                 ):
        self._lean = inc_lean
        self._lean_stitch_pull_direction = lean_stitch_pull_direction
        

    @property
    def lean(self) -> Stitch_Lean:
        """
        :return: the direction the cable leans
        """
        return self._lean

    def stitch_definitions(self) -> List[Stitch_Definition]:
        """
        :return: the list of stitch definitions that construct this cable in yarn-wise order
        """
        # cast_on = [Stitch_Definition(offset_to_parent_loops=[])]
        # lean_stitch = [Lean_Stitch_Definition(self.lean, -1 if self.lean == Stitch_Lean.Right else 1, self._lean_stitch_pull_direction)]
        # below is because we always need the stitch with most negative to be connected first (think of this on the right side, since
        # for wrong side we will flip the stitch so that's the same.)
        if self.lean is Stitch_Lean.Right: 
            lean_stitch = [Right_Lean_Stitch_Definition(lean_stitch_pull_direction = self._lean_stitch_pull_direction)]
            cast_on = [Right_Lean_CastOn_Stitch_Definition()]
            return lean_stitch + cast_on
        else: 
            lean_stitch = [Left_Lean_Stitch_Definition(lean_stitch_pull_direction = self._lean_stitch_pull_direction)]
            cast_on = [Left_Lean_CastOn_Stitch_Definition()]
            return cast_on + lean_stitch

    def copy(self):
        """
        :return: a deep copy of the cable definition
        """
        newInc_Stitch = Increase_Stitch_Definition(self._lean, self._lean_stitch_pull_direction)
        return newInc_Stitch


    def __str__(self):
        return f"{self.lean}CO"

    def __repr__(self):
        return str(self)
