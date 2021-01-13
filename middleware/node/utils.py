import cv2
from middleware.node.const import *
from middleware.node.annotate import *
from middleware.common.parser import AthenaParser
from middleware.common.decision import Decision


def list_to_str(arr):
    s = ""
    for a in arr:
        if s != "":
            s += ","
        s += str(a)
    return s


def get_latest_data(sensor_type):
    if sensor_type == "Camera":
        # image loading
        img = cv2.imread(CAM_DATA_PATH)
        img = cv2.resize(img, None, fx=0.4, fy=0.4)
        # height, width, channels = img.shape
        data = cv2.imencode(".jpg", img)[1].tobytes()
        return YOLO_Annotate(data)


def post_process_coa(variables):
    for var in variables:
        if len(variables[var]) > 0 and variables[var][-1] != ")":
            variables[var] = "And(" + variables[var] + ")"


def on_query(query, Global):
    name, skills_req, input_str = query.split("\t")
    skills_req = skills_req.split(",")
    # Parse boolean expression of decision query
    a = AthenaParser()
    a.load_str(input_str)
    decision_logic, coa_validity, predicates = a.variables[name][1:4]
    post_process_coa(coa_validity)
    print(coa_validity)
    with Global.lock:
        Global.buffer_query = [decision_logic, coa_validity, predicates]

    # TODO: A better middleware algorithm to find the best suiting nodes
    # Assume only one skill here in skills_req for now
    skill = skills_req[0]
    if skill not in Global.skills:
        for sensor, member in Global.members.items():
            if skill in member.skills:
                print_and_pub(
                    sensor, skill + "\t" + Global.curr_id, Global.publisher, "get_data"
                )
                break
    else:
        annotated_data = get_latest_data(skill)
        on_query_decide(annotated_data)


def on_query_decide(annotated_data, Global):
    if not Global.buffer_query:
        return
    decision_logic, coa_validity, predicates = Global.buffer_query
    d = Decision("/query_res", decision_logic, coa_validity, predicates, 60)
    variables = []
    for p in predicates:
        variables.append(predicates[p][0])
    for var in annotated_data:
        if var in variables:
            d.set_var_value(var, annotated_data[var])
    if d.get_value():
        print_and_pub("query_result", d.get_value(), Global.publisher)
    else:
        print("Something is wrong with the decision model")
    with Global.lock:
        Global.buffer_query = None