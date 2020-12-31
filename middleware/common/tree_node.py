# -*- coding: utf-8 -*-
"""Module describing known
"""

class TreeNode(object):

    def __init__(self, name):
        self.name = name        
        self.left = None
        self.right = None        

    def __str__(self):
        return self.name

    def get_name(self):
        return self.name

    def add_left(self, t_node):        
        self.left = t_node            
    
    def add_right(self, t_node):        
        self.right = t_node            

    def print(self):
        print(self.name)
        if self.left != None:        
            self.left.print()
        if self.right != None:            
            self.right.print()