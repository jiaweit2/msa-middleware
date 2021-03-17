from middleware.common.decision import Decision
from middleware.common.parser import AthenaParser
from middleware.node.utils import *


def on_query(query, Global):
    name, input_str, position, status = query.split("\t")
    # Parse boolean expression of decision query
    a = AthenaParser()
    a.load_str(input_str)
    decision_logic, coa_validity, predicates = a.variables[name][1:4]
    post_process_coa(coa_validity)
    cost, plan = Global.optimizer.find_cost(predicates, Global.members, position)
    print(cost, plan)
    d = Decision("/query_res", decision_logic, coa_validity, predicates, 60, cost=cost)
    with Global.lock:
        Global.buffer = [d, plan, predicates, 0, [], None]
    schedule(Global)


def schedule(Global):
    d, plan, predicates, num, vals, last_predicate = Global.buffer

    if len(vals) < num:
        # wait for more remote sensor values
        return

    while d.get_value() == "undecided":
        if len(vals) > 0:
            predicate = last_predicate
        else:
            predicate = d.pick()
            if predicate is None:
                print("Fail to conclude a decision!")
                break
            with Global.lock:
                Global.buffer[5] = predicate
                num = Global.buffer[3] = len(plan[predicate])
            var = predicates[predicate][0]
            for owner, annotator in plan[predicate]:
                if owner == "SELF":
                    data = get_sensor_data(annotator, Global)
                    vals.append(
                        Global.members["SELF"].annotators.run(annotator, data, var)
                    )
                else:
                    print_and_pub(
                        owner,
                        annotator + "\t" + var + "\t" + Global.curr_id,
                        Global.publisher,
                        "get_data",
                    )
            if len(vals) < num:
                # wait for more remote sensor values
                return
        d.set_var_value(predicates[predicate][0], float(sum(vals)) / float(len(vals)))
        with Global.lock:
            # reset buffer values
            vals = []

    # a result is obtained
    with Global.lock:
        Global.buffer = None
    print_and_pub("query_result", d.get_value(), Global.publisher)
