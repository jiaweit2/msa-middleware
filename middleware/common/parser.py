# -*- coding: utf-8 -*-
"""Module describing Decision Maker
"""
from lark import Lark, Tree, Token
from pyeda.inter import *

from middleware.common.const import *


class AthenaParser(object):
    """Class to define a decision maker

    This class mainly ...

    """

    def __init__(self):
        self.parser = Lark(ATHENA_GRAMMAR, start="input")
        self.variables = dict()

    def load(
        self, input_str, default_freshness_p=DEFAULT_FRESHNESS_P, custom_markers=dict()
    ):
        """The function to parse the given decision rule

        Args:
            input_str (str): the given decision rule

        Note:
            Please optimize this part. It is very complicated now

        """

        # Mainly parsing
        variables = dict()

        try:
            tree = self.parser.parse(input_str)
        except:
            return variables

        # Interpret the result
        for stmt in tree.children:

            if len(stmt.children[0].children) == 1:
                # Var case
                var_name = str(stmt.children[0].children[0])
                if var_name != str(Name(var_name)):
                    print("Var name %s is malformatted!")
                    return

                if stmt.children[1].data == "label":
                    # Label case
                    annotator_func = str(stmt.children[1].children[0].children[0])
                    args = []
                    for arg in stmt.children[1].children[1].children:
                        args.append(str(arg.children[0]))

                    freshness_p = DEFAULT_FRESHNESS_P
                    if len(stmt.children[1].children) > 3:
                        freshness_p = int(stmt.children[1].children[3])

                    prefix_sets = []
                    for data_set in stmt.children[1].children[2].children:
                        prefix_sets.append(
                            [str(d.children[0]) for d in data_set.children]
                        )

                    variables[var_name] = (
                        LABEL,
                        annotator_func,
                        args,
                        prefix_sets,
                        freshness_p,
                        -1,
                    )

                elif stmt.children[1].data == "decision":
                    # Decision case
                    freshness_p = DEFAULT_FRESHNESS_P
                    if len(stmt.children[1].children) > 1:
                        freshness_p = int(stmt.children[1].children[1])

                    coas = stmt.children[1].children[0].children
                    coa_validity = dict()
                    predicates = dict()
                    decision_logic = "Or("

                    for i in range(len(coas)):
                        coa_key = str(coas[i].children[0].children[0])
                        logic_exprs = coas[i].children[1]

                        if logic_exprs.children[0] == OTHERWISE:
                            coa_validity[coa_key] = OTHERWISE
                            continue

                        q = deque([logic_exprs])
                        tokens = []

                        while q:
                            curr = q.pop()
                            if isinstance(curr, Tree):
                                if curr.data == "logic_exprs":
                                    for j in range(len(curr.children) - 1, -1, -1):
                                        q.append(curr.children[j])

                                elif curr.data == "logic_expr":
                                    for j in range(len(curr.children) - 1, -1, -1):
                                        q.append(curr.children[j])

                                elif curr.data == "conjunction":
                                    tokens.append(str(curr.children[0]))

                                if curr.data == "predicate":
                                    p_key = (
                                        str(curr.children[0].children[0]),
                                        str(curr.children[1].children[0]),
                                        str(curr.children[2].children[0]),
                                    )
                                    if p_key not in predicates:
                                        predicates[p_key] = "p" + str(len(predicates))
                                    tokens.append(predicates[p_key])

                            elif curr in {"(", ")"}:
                                tokens.append(str(curr))

                        coa_validity[coa_key] = str(expr("".join(tokens)))

                        decision_logic += str(coa_validity[coa_key]) + ", "

                    decision_logic += ")"
                    decision_logic = decision_logic.replace(", )", ")")

                    f = expr(decision_logic)

                    if not f.satisfy_one():
                        print("This logic is unsatisfiable")
                        return

                    fm = str(espresso_exprs(f.to_dnf()))
                    fm = fm.replace("And", "")
                    fm = fm.replace("(", "[")
                    fm = fm.replace(")", "]")
                    if "Or" in fm:
                        fm = fm.replace("Or", "")
                        fm = fm[1:-2]

                    predicate_reg = re.compile(r"(\,|\[|\])")
                    p_tokens = predicate_reg.split(fm)
                    p_tokens = deque([t.strip() for t in p_tokens if t.strip() != ""])

                    for i in range(len(p_tokens)):
                        if p_tokens[i] not in {"[", "]", ","}:
                            p_tokens[i] = '"' + p_tokens[i] + '"'

                    Or = eval("".join(p_tokens))

                    for i in range(len(Or)):
                        if type(Or[i]) != list:
                            Or[i] = [Or[i]]

                    inv_predicates = {v: list(k) for k, v in predicates.items()}
                    variables[var_name] = (
                        DECISION,
                        Or,
                        coa_validity,
                        inv_predicates,
                        freshness_p,
                    )

                else:
                    print("Unknown variable type. Has to be Label, or Decision!")

            else:
                # Vars case
                var_names = []

                for t in stmt.children[0].children:
                    var_name = str(t.children[0])
                    if var_name != str(Name(var_name)):
                        print("Var name %s is malformatted!")
                        return
                    var_names.append(var_name)

                if stmt.children[1].data != "label":
                    print("Current vars should be only label!")
                    return

                annotator_func = str(stmt.children[1].children[0].children[0])
                args = []
                for arg in stmt.children[1].children[1].children:
                    if len(arg.children[0].children) == 1:
                        # Means it is a constant
                        args.append(str(arg.children[0].children[0]))
                    else:
                        # Means it is a marker
                        tmp = ""
                        for c in arg.children[0].children:
                            tmp += c
                        args.append(str(tmp))

                freshness_p = DEFAULT_FRESHNESS_P
                if len(stmt.children[1].children) > 3:
                    freshness_p = int(stmt.children[1].children[3])

                data_sets = []
                for data_set in stmt.children[1].children[2].children:
                    data_sets.append([str(d.children[0]) for d in data_set.children])

                for i in range(len(var_names)):
                    variables[var_names[i]] = (
                        LABEL,
                        annotator_func,
                        args,
                        data_sets,
                        freshness_p,
                        i,
                    )

        return variables

    def load_str(self, input_str):
        variables = self.load(input_str)
        if not variables:
            return False

        self.load_vars(variables)
        return True

    def load_vars(self, variables):
        self.variables = {**self.variables, **variables}


if __name__ == "__main__":
    a = AthenaParser()
    input_str = """/Champaign/cloth = Decision({
    "Jumper": ((/Champaign/temperature <= 5) | (/Champaign/windSpeed >= 30)),
    "T-Shirt": ((/Champaign/temperature >= 25) | (/Champaign/windSpeed <= 10)),
    "Rain coat": /Champaign/rain == True,
    "Hoody": otherwise
})
"""
    result = a.load_str(input_str)
    print(a.variables)