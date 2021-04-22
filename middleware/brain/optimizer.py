def least_cost_annotators(members, annotator_wanted=None):
    # Find least-cost annotator(s) owner
    annotators = {}  # annotator -> [owner, cost]
    for id_ in members:
        for annotator in members[id_].annotators.map:
            if annotator_wanted and annotator != annotator_wanted:
                continue
            # Check if the node has the sensor
            sensor_name = members[id_].annotators.map[annotator][2]
            if sensor_name not in members[id_].sensors.map:
                continue
            # cost = complexity * throughput(mb/s)
            c = members[id_].annotators.map[annotator][1] * members[id_].throughput
            if annotator not in annotators or c < annotators[annotator][1]:
                annotators[annotator] = [id_, c]
    if annotator_wanted:
        return annotators[annotator_wanted]  # owner
    return annotators


def basic_cost_func(args):
    # Metrics: network delay, annotator complexity
    predicates, members, rules = args
    annotators = least_cost_annotators(members)
    plan = {}  # predicate -> [(owner, annotator), ...]
    cost = {}  # predicate -> cost
    for k, v in predicates.items():
        temp = v[0].split("@")
        var = temp[0]
        specified_id = None
        if len(temp) > 1:
            specified_id = temp[1]
        cost[k] = float("inf")
        plan[k] = None
        for combo in rules[var]:
            if specified_id is not None:
                proceed = True
                c = 0
                for a in combo:
                    if a not in members[specified_id].annotators.map:
                        proceed = False
                        break
                    sensor_name = members[specified_id].annotators.map[a][2]
                    if sensor_name not in members[specified_id].sensors.map:
                        proceed = False
                        break
                    c += members[specified_id].annotators.map[a][1]
                if proceed:
                    cost[k] = c
                    plan[k] = [(specified_id, a) for a in combo]

            else:
                c = sum(
                    annotators[a][1] if a in annotators else float("inf") for a in combo
                )
                if c < cost[k]:
                    cost[k] = c
                    plan[k] = [(annotators[a][0], a) for a in combo]
    return cost, plan


class Optimizer:
    def __init__(self, rules, cost_func=basic_cost_func):
        self.cost_func = cost_func
        self.rules = rules

    def filter(self, members, pos):
        # filter 1: not-in-range nodes(sensors)
        return members

    def find_cost(self, predicates, members, pos):
        members = self.filter(members, pos)
        return self.cost_func([predicates, members, self.rules])
