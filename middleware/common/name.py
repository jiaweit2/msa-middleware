# -*- coding: utf-8 -*-
"""Module describing name
"""

import time
import pickle

class Name(object):

    def __init__(self, name):
        if name and name[0] != '/':            
            name = '/'+name            

        while '//' in name:
            name = name.replace('//', '/')
        
        self.name_components = name.split('/')[1:]
        self.name_components = [comp for comp in self.name_components if comp]
        self.name = '/'+'/'.join(self.name_components)


    def __str__(self):
        return self.name

    def __len__(self):
        return len(self.name_components)

    #####################
    # Getter Functions  #
    #####################

    def get_name_components(self):
        return self.name_components

    def get_name_component(self, idx):
        return self.name_components[idx]

    def get_length(self):
        return self.__len__()

    def get_sub_name(self, begin_idx, end_idx):        
        if end_idx < 0:
            if self.get_length() + end_idx >= 0:
                end_idx = self.get_length() + end_idx
            else:
                return Name('/')
        if begin_idx > end_idx: 
            end_idx = begin_idx

        name_components = [''] + self.name_components[begin_idx:end_idx+1]
        return Name('/'.join(name_components))

    def get_common_prefix(self, name):
        cnt = 0
        name = Name(str(name))
        for i in range(min(self.get_length(), name.get_length())):
            if self.get_name_component(i) == name.get_name_component(i):
                cnt += 1
                continue
            else:
                break
        if cnt == 0: return Name('/')
        else: return self.get_sub_name(0, cnt-1)


    #####################
    # Name Operators    #
    #####################

    def equal(self, name):
        return self.name == str(name)

    def is_prefix_of(self, name):        
        if self.equal(self.get_common_prefix(name)):
            return True
        else:
            return False


if __name__ == '__main__':
    a = Name('/test/a/b/c/123')
    print(a.get_sub_name(0, 1))
    # print(len(a))
    # print(a.get_length())
    # print(a.get_sub_name(0, -3))
    # print(Name('/test').is_prefix_of(Name('/test')))

        