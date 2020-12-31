# -*- coding: utf-8 -*-
"""Module describing known
"""

import logging
import logging.config

from middleware.common.const import *

try:
    logging.config.dictConfig(DEFAULT_LOGGER)
    logger = logging.getLogger("decision_maker")
except:
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s: %(filename)s:%(lineno)3s|%(threadName)s|%(funcName)s]: %(message)s",
    )
    logger = logging.getLogger(__name__)


class Variable(object):
    def __init__(self, name, freshness_p, associated_vars):
        self.name = name
        self.value = UNDECIDED
        self.cost = 0
        self.freshness_p = freshness_p
        self.associated_vars = associated_vars
        self.resolved_vars = dict()
        self.user_cbs = set()
        self.to_resolve = dict()

    def set_associated_vars(self, var_ptrs):
        self.associated_vars = set(var_ptrs)

    def add_associated_var(self, var_ptr):
        if var_ptr:
            self.associated_vars.add(var_ptr)

    def get_associated_vars(self):
        return self.associated_vars

    def add_user_cb(self, user_cb):
        if user_cb:
            self.user_cbs.add(user_cb)

    def get_user_cbs(self):
        return list(self.user_cbs)

    def set_value(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def add_cost(self, cost):
        self.cost += cost

    def set_cost(self, cost):
        self.cost = cost

    def get_cost(self):
        return self.cost

    def get_name(self):
        return self.name

    def get_freshness_p(self):
        return self.freshness_p

    def set_freshness_p(self, freshness_p):
        self.freshness_p = freshness_p

    def is_resolved(self):
        if self.value != UNDECIDED:
            return True
        else:
            return False

    def get_reason(self):
        return self.resolved_vars

    def propagate(self):
        if self.name in self.to_resolve:
            self.to_resolve.pop(self.name)

        for var_instance in list(self.associated_vars):
            logger.debug(
                "Propagate to value %s of %s to %s",
                self.value,
                self.name,
                var_instance.get_name(),
            )
            var_instance.set_var_value(self.name, self.value)

        for user_cb in list(self.user_cbs):
            user_cb(self.name, self.value, self.resolved_vars)

    def set_to_resolve(self, to_resolve):
        self.to_resolve = to_resolve

    def process(self):
        pass

    def set_var_value(self, var_name, var_value):
        pass