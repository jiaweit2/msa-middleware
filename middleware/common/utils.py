# -*- coding: utf-8 -*-
"""Utility functions

This module includes a set of utility functions that are commonly used.

"""

from middleware.common.name import Name


def is_variable(target):
    """Helper function to check whether the given name is valid variable or not.

    Args:
        target (str): the target name

    Returns:
        bool: True for valid. False otherwise.

    """ 
    if target == str(Name(target)):        
        return True
    else:
        return False

def is_constant(target):
    """Helper function to check whether the given name is valid constant or not.

    Args:
        target (str): the target name

    Returns:
        bool: True for valid. False otherwise.

    """ 
    return not is_variable(target)