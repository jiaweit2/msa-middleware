from middleware.preset.rules import *


def basic_cost_func(args):
    # Metrics: network delay, annotator complexity

    predicates, members = args
    # Find least-cost annotators owner
    annotators = {}  # -> [owner, cost]
    for id_ in members:
        for annotator in members[id_].annotators.map:
            # cost = complexity + delay
            c = members[id_].annotators.map[annotator][1] + (
                members[id_].last_updated - members[id_].last_sent
            )
            if annotator not in annotators or c < annotators[annotator][1]:
                annotators[annotator] = [id_, c]
    plan = {}  # predicate -> [(owner, annotator), ...]
    cost = {}  # predicate -> cost
    for k, v in predicates.items():
        var = v[0]
        cost[k] = float("inf")
        plan[k] = None
        for combo in rules[var]:
            c = sum(
                annotators[a][1] if a in annotators else float("inf") for a in combo
            )
            if c < cost[k]:
                cost[k] = c
                plan[k] = [(annotators[a][0], a) for a in combo]
    return cost, plan


class Optimizer:
    def __init__(self, cost_func=basic_cost_func):
        self.cost_func = cost_func

    def filter(self, members, pos):
        # filter 1: not-in-range nodes(sensors)
        return members

    def find_cost(self, predicates, members, pos):
        members = self.filter(members, pos)
        return self.cost_func([predicates, members])
