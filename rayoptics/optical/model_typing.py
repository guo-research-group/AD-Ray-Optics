#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""" type hints for rayoptics

Created on Tue Dec  7 10:48:54 2021

.. codeauthor: Michael J. Hayford
"""
from __future__ import annotations
from typing import Tuple, Literal, List, Iterator

import numpy as np

from rayoptics.seq import interface
from rayoptics.seq import gap

Vector2 = np.ndarray
Vector3 = np.ndarray
Direction3 = np.ndarray
Matrix3 = np.ndarray
Transform3 = Tuple[Matrix3, Vector3]

DCenterTypes = Literal['decenter', 'reverse', 'dec and return', 'bend']
InteractMode = Literal['transmit', 'reflect', 'dummy']
ZDir = Literal[1, -1]

Path_Seg = Tuple[interface.Interface, gap.Gap, 
                 Transform3, float, ZDir]
Path = Iterator[Path_Seg]

Ray_Seg = Tuple[Vector3, Direction3, float, Direction3]
Ray_Data = List[Ray_Seg]
Ray_Package = Tuple[Ray_Data, float, float]
