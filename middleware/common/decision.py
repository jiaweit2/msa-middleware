# -*- coding: utf-8 -*-
"""Module describing decision
"""
import copy
import logging
import logging.config
import numpy as np
from pyeda.inter import *

from middleware.common.const import *
from middleware.common.variable import Variable
from middleware.common.tree_node import TreeNode

try:
    logging.config.dictConfig(DEFAULT_LOGGER)
    logger = logging.getLogger("decision_maker")
except:
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s: %(filename)s:%(lineno)3s|%(threadName)s|%(funcName)s]: %(message)s",
    )
    logger = logging.getLogger(__name__)

TINY_VALUE = 0.00000000001


class Decision(Variable):
    def __init__(
        self,
        name,
        decision_logic,
        coa_validity,
        predicates,
        freshness_p=DEFAULT_FRESHNESS_P,
        associated_vars=set(),
    ):
        super().__init__(name, freshness_p, associated_vars)
        self.decision_logic = decision_logic
        self.coa_validity = copy.deepcopy(coa_validity)
        self.unresolvable = list()
        self.otherwise = "OTHERWISE"
        for k, v in coa_validity.items():
            if v == OTHERWISE:
                self.coa_validity.pop(k)
                self.otherwise = k

        self.predicates = predicates
        self.vars_to_predicates = dict()
        self.predicate_values = []
        for k, v in predicates.items():
            self.predicate_values.append(None)

            left, oper, right = v
            if not left in self.vars_to_predicates:
                self.vars_to_predicates[left] = set()
            self.vars_to_predicates[left].add(k)

            if is_variable(right):
                if not right in self.vars_to_predicates:
                    self.vars_to_predicates[right] = set()
                self.vars_to_predicates[right].add(k)

        self.prob = dict()
        self.cost = dict()

        self.request_tree = None
        self.resolver = None
        self.produce_var = None

    ############
    ## Setter ##
    ############

    def set_resolver(self, func):
        self.resolver = func

    def set_prob(self, prob):
        # Expected format of given prob: { predicate_str: value } ex) { '/a/b == False': 0.5 }
        # Expected output: { predicate_id: value } ex) { 'p0': 0.5 }
        for predicate, prob_value in prob.items():
            predicate = predicate.replace(" ", "")
            for p_name, p_list in self.predicates.items():
                if predicate == "".join(p_list):
                    self.prob[p_name] = prob_value

        for k, v in self.prob.items():
            if v == 1.0:
                self.set_predicate_value(k, 1)
            elif v == 0.0:
                self.set_predicate_value(k, 0)

    def set_produce_var(self, func):
        self.produce_var = func

    def set_var_value(self, var_name, value):
        logger.debug("Value of variable %s is %s", var_name, str(value)[:10])
        if var_name not in self.vars_to_predicates:
            return

        if value == UNDECIDED:
            return

        self.resolved_vars[var_name] = value

        for p in self.vars_to_predicates[var_name]:
            if value == UNRESOLVABLE:
                self.set_predicate_value(p, None)
            else:
                if var_name == self.predicates[p][0]:
                    self.predicates[p][0] = str(value)

                if var_name == self.predicates[p][2]:
                    self.predicates[p][2] = str(value)

                if is_constant(self.predicates[p][0]) and is_constant(
                    self.predicates[p][2]
                ):
                    logger.debug("Deciding predicate %s", self.predicates[p])
                    p_value = int(eval("".join(self.predicates[p])))

                    self.set_predicate_value(p, p_value)

            self.predicates.pop(p)
        self.vars_to_predicates.pop(var_name)

        self.process()

    def set_predicate_value(self, p_name, value):
        # value can be 0, 1, or None
        logger.debug("Value of predicate %s is %s", p_name, value)

        for user_cb in self.user_cbs:
            user_cb(p_name, value, {})

        self.request_tree = self.update_request_tree(self.request_tree, p_name, value)
        p_idx = int(p_name.replace("p", ""))
        self.predicate_values[p_idx] = value

        # Process decision logic based on the given predicate value
        for predicates in copy.deepcopy(self.decision_logic):
            if p_name in predicates:
                if value == None:
                    self.unresolvable.append(self.decision_logic.index(predicates))
                    del self.decision_logic[self.decision_logic.index(predicates)]
                if value == 0:
                    del self.decision_logic[self.decision_logic.index(predicates)]
                if value == 1:
                    self.decision_logic[self.decision_logic.index(predicates)].remove(
                        p_name
                    )

        for predicates in self.decision_logic:
            if len(predicates) == 0:
                logger.debug("Found the viable courses of action!")

        # Check viability of coa
        for k in list(self.coa_validity.keys()):
            self.coa_validity[k] = (
                self.coa_validity[k].replace(p_name + ",", "1,")
                if value
                else self.coa_validity[k].replace(p_name + ",", "0,")
            )
            self.coa_validity[k] = (
                self.coa_validity[k].replace(p_name + ")", "1)")
                if value
                else self.coa_validity[k].replace(p_name + ")", "0)")
            )

            f = expr(self.coa_validity[k])
            if f.is_one():
                # If the logical expression is determined to be True
                self.value = k
                break
            elif f.is_zero():
                # If the logical expression is determined to be False
                self.coa_validity.pop(k)
            else:
                # If the logical expression is not determined yet
                continue

        if not self.coa_validity:
            if self.unresolvable:
                self.value = UNRESOLVABLE
            else:
                self.value = self.otherwise

    ############
    ## Getter ##
    ############

    def get_predicates(self):
        return copy.deepcopy(self.predicates)

    def get_vars_to_predicates(self):
        return copy.deepcopy(self.vars_to_predicates)

    def get_vars(self):
        return self.vars_to_predicates.keys()

    def get_decision_logic(self):
        return copy.deepcopy(self.decision_logic)

    def get_validity(self, coa):
        return self.coa_validity[coa]

    def get_all_validity(self):
        return copy.deepcopy(self.coa_validity)

    def get_predicate_values(self):
        return copy.deepcopy(self.predicate_values)

    def get_request_tree(self):
        return copy.deepcopy(self.request_tree)

    def get_fetch(self):
        if not self.request_tree:
            return []

        p = self.request_tree.get_name()
        variables = set()

        if p in self.predicates:
            if is_variable(self.predicates[p][0]):
                variables.add(self.predicates[p][0])
            if is_variable(self.predicates[p][2]):
                variables.add(self.predicates[p][2])

        return list(variables)

    def get_prefetch(self):
        if not self.request_tree:
            return []

        visited, queue = list(), [self.request_tree]

        while queue:
            v = queue.pop()
            if v.get_name() not in visited:
                if v.get_name() not in visited:
                    visited.append(v.get_name())
                if v.left != None:
                    queue.append(v.left)
                if v.right != None:
                    queue.append(v.right)

        variables = list()
        for p in visited[1:]:
            if p not in self.predicates:
                continue
            if (
                is_variable(self.predicates[p][0])
                and self.predicates[p][0] not in variables
            ):
                variables.append(self.predicates[p][0])
            if (
                is_variable(self.predicates[p][2])
                and self.predicates[p][2] not in variables
            ):
                variables.append(self.predicates[p][2])

        return list(variables)

    ################
    ## Scheduling ##
    ################

    def update_request_tree(self, node, p_name, value):
        # logger.debug("%s, %s, %s", node, p_name, value)
        if not node:
            logger.debug("Request node is None.")
            return

        if p_name == str(node):
            if value == True:
                node = node.left
            if value == False or value == None:
                node = node.right

        if node:
            if node.left:
                node.left = self.update_request_tree(node.left, p_name, value)
            if node.right:
                node.right = self.update_request_tree(node.right, p_name, value)

        return node

    def schedule(self):
        """Schedule the request order for predicates in the decision

        This function will construct the request tree

        Args:
            prob (dict): true probability for the predicates
                         {predicate_name: probability}
            cost (dict): cost to resolve the values of the predicates
                         {predicate_name: cost}
        """
        root = self.pick(self.decision_logic)
        if root:
            self.request_tree = TreeNode(root)
            self.construct(self.request_tree, self.decision_logic)
        else:
            logger.debug("Decision logic is empty: %s", self.decision_logic)

    def construct(self, node, decision_logic):
        """Construct the request tree"""
        node_name = node.get_name()

        assume_false = copy.deepcopy(decision_logic)
        assume_true = copy.deepcopy(decision_logic)
        for predicates in copy.deepcopy(assume_false):
            if node_name in predicates:
                del assume_false[assume_false.index(predicates)]

        for i in range(len(assume_true)):
            if node_name in assume_true[i]:
                assume_true[i].remove(node_name)

        left = self.pick(assume_true)
        if left:
            # logger.debug("if node %s is true, the best pick is %s", node_name, left)
            node.left = TreeNode(left)
            self.construct(node.left, copy.deepcopy(assume_true))

        right = self.pick(assume_false)
        if right:
            # logger.debug("if node %s is false, the best pick is %s", node_name, right)
            node.right = TreeNode(right)
            self.construct(node.right, copy.deepcopy(assume_false))

    def pick(self, decision_logic):
        """Actual scheduling algorithm here"""

        if len(decision_logic) == 0:
            # logger.debug("Decision logic is empty")
            return None

        for predicates in decision_logic:
            if len(predicates) == 0:
                # logger.debug("There is already a viable coa")
                return None

        # Compute TRUE probability per unit cost for the given subree
        aggregates = []
        for subtree in decision_logic:
            aggregate = []
            for p in subtree:
                # logger.debug("p: %s", p)
                p_prob = self.prob[p] if p in self.prob else DEFAULT_PROB
                p_cost = self.cost[p] if p in self.cost else DEFAULT_COST
                true_prob_per_cost = float(p_prob) / float(p_cost)
                if true_prob_per_cost > 0:
                    aggregate.append(np.log(true_prob_per_cost))
                else:
                    aggregate.append(np.log(TINY_VALUE))
            aggregates.append(aggregate)

        # Select the courses of action and AND subtree
        # that maxmize TRUE probability per unit cost
        max_val = float(-np.inf)
        chosen_subtree_idx = -1
        for i in range(len(aggregates)):
            if not aggregates[i]:
                logger.debug("This path, you already found the decision.")
                return None
            val = np.sum(aggregates[i])
            if max_val < val:
                max_val = val
                chosen_subtree_idx = i

        if chosen_subtree_idx < 0:
            logger.debug("Nothing to choose? Something wrong")
            return None

        # Select the predicate that maximze FALSE probability per unit cost
        leaf_cost = []
        for p in decision_logic[chosen_subtree_idx]:
            p_prob = self.prob[p] if p in self.prob else DEFAULT_PROB
            p_cost = self.cost[p] if p in self.cost else DEFAULT_COST
            false_prob_per_cost = (1 - p_prob) / p_cost
            leaf_cost.append(false_prob_per_cost)

        if not leaf_cost:
            logger.debug("This means all leaf nodes are already examined.")
            return None

        chosen_leaf_idx = leaf_cost.index(max(leaf_cost))
        chosen_leaf = decision_logic[chosen_subtree_idx][chosen_leaf_idx]

        return chosen_leaf

    def process(self):
        logger.debug("Process decision %s", self.name)
        if self.value == UNDECIDED:
            self.schedule()

            # for var in self.get_fetch():
            #     logger.debug("Fetch %s", var)
            #     self.resolver(var, self)

        else:
            if self.produce_var:
                self.produce_var(self.name, self.value)
            self.propagate()


if __name__ == "__main__":
    coa_validity = {"CoA1": "And(p1, p3)", "CoA2": "And(p2, p0)", "CoA3": "And(p4)"}

    predicates = {
        "p0": ["/temperature", ">=", "10"],
        "p1": ["/precipitation", ">=", "10"],
        "p2": ["/windSpeed", ">=", "10"],
        "p3": ["/temperature", ">=", "30"],
        "p4": ["/windSpeed", ">=", "70"],
    }

    d = Decision(
        "/test", [["p0"], ["p1"], ["p2"], ["p3"], ["p4"]], coa_validity, predicates, 60
    )
    # d = Decision('test', [['p1'], ['p3'], ['p2'], ['p0'], ['p4']], coa_validity, predicates, 60)
    # print(d.request_tree)
    # print(d.value)
    # # d.set_var_value('/windSpeed', UNRESOLVABLE)
    # d.set_predicate_value('p4', None)
    # print(d.value)

    # d.set_var_value('/windSpeed', UNRESOLVABLE)
    # d.set_var_value('/precipitation', UNRESOLVABLE)
    # print(d.request_tree)
    # print(d.value)
    # print(d.get_fetch())
    # print(d.get_prefetch())
    # print(d.coa_validity)
    d.set_var_value("/precipitation", "50")
    d.set_var_value("/temperature", "5")
    d.set_var_value("/windSpeed", "50")

    if d.get_value():
        print(d.get_value())
