from middleware.common.decision import Decision
from middleware.common.parser import AthenaParser
from middleware.node.utils import *


def on_running_query(plan, Global):
    for predicate in plan:
        owner, annotator_name = plan[predicate][0]
        if owner == "SELF":
            sensor_name = Global.members["SELF"].annotators.get(annotator_name)[2]
            Global.members["SELF"].sensors.stream(sensor_name, Global, print_and_pub)
        else:
            print_and_pub(
                owner,
                annotator_name + "\t" + Global.curr_id,
                Global.publisher,
                "stream",
            )


def on_query(query, Global):
    name, input_str, position, status = query.split("\t")
    # Parse boolean expression of decision query
    a = AthenaParser()
    a.load_str(input_str)
    decision_logic, coa_validity, predicates = a.variables[name][1:4]
    post_process_coa(coa_validity)
    cost, plan = Global.optimizer.find_cost(predicates, Global.members, position)
    if status == "running":
        on_running_query(plan, Global)
    else:
        d = Decision(
            "/query_res", decision_logic, coa_validity, predicates, 60, cost=cost
        )
        with Global.lock_query:
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
            with Global.lock_query:
                Global.buffer[5] = predicate
                num = Global.buffer[3] = len(plan[predicate])
            var_tuple = predicates[predicate][0].split("@")
            var = var_tuple[0]
            if len(var_tuple) == 1:
                # Not specifying any sensor as the source
                for owner, annotator_name in plan[predicate]:
                    if owner == "SELF":
                        sensor = Global.members["SELF"].annotators.get(annotator_name)[
                            2
                        ]
                        data = Global.members["SELF"].sensors.get_data(sensor)
                        vals.append(
                            Global.members["SELF"].annotators.run(
                                annotator_name, data, var
                            )
                        )
                    else:
                        print_and_pub(
                            owner,
                            annotator_name + "\t" + var + "\t" + Global.curr_id,
                            Global.publisher,
                            "get_data",
                        )
            else:
                # Specify a sensor as the source
                for owner, annotator_name in plan[predicate]:
                    if owner == var_tuple[1]:
                        print_and_pub(
                            owner,
                            annotator_name + "\t" + var + "\t" + Global.curr_id,
                            Global.publisher,
                            "get_data",
                        )
                    break

            if len(vals) < num:
                # wait for more remote sensor values
                return
        if type(vals[0]) == str:
            val = vals[0]
        else:
            val = float(sum(vals)) / float(len(vals))
        d.set_var_value(predicates[predicate][0], val)
        with Global.lock_query:
            # reset buffer values
            vals = []

    # a result is obtained
    with Global.lock_query:
        Global.buffer = None
    print_and_pub("result", d.get_value(), Global.publisher)


if __name__ == "__main__":
    s = """/YOLO = Decision({ 
            "Human": person@0003 > 0.3,
            "NoHumanDetected": otherwise
        })"""
    a = AthenaParser()
    a.load_str(s)
    print(a.variables)