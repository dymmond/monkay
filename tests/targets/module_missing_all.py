from monkay import Monkay

monkay = Monkay(
    globals(),
    lazy_imports={
        "bar": ".fn_module:bar",
    },
    skip_all_update=True,
)
