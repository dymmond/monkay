from monkay import Monkay


def bar():
    return "notbar"


monkay = Monkay(
    globals(),
    lazy_imports={
        "bar": ".fn_module:bar",
    },
)
