from __future__ import annotations

import inspect

import monkay
import monkay.types as monkay_types
from monkay import asgi, base, cages, core

EXPECTED_TOP_LEVEL_EXPORTS = [
    "Monkay",
    "DeprecatedImport",
    "PRE_ADD_LAZY_IMPORT_HOOK",
    "ExtensionProtocol",
    "load",
    "load_any",
    "absolutify_import",
    "InGlobalsDict",
    "UnsetError",
    "get_value_from_settings",
    "Cage",
    "TransparentCage",
]

EXPECTED_MONKAY_INIT_PARAMETERS = [
    "globals_dict",
    "with_instance",
    "with_extensions",
    "extension_order_key_fn",
    "settings_path",
    "preloads",
    "settings_preloads_name",
    "settings_extensions_name",
    "uncached_imports",
    "lazy_imports",
    "deprecated_lazy_imports",
    "settings_ctx_name",
    "extensions_applied_ctx_name",
    "skip_all_update",
    "skip_getattr_fixup",
    "evaluate_settings",
    "ignore_settings_import_errors",
    "pre_add_lazy_import_hook",
    "post_add_lazy_import_hook",
    "ignore_preload_import_errors",
    "package",
]

EXPECTED_CAGE_INIT_PARAMETERS = [
    "globals_dict",
    "obj",
    "name",
    "preloads",
    "context_var_name",
    "deep_copy",
    "original_wrapper",
    "update_fn",
    "use_wrapper_for_reads",
    "skip_self_register",
    "package",
]

EXPECTED_MONKAY_METHOD_PARAMETERS = {
    "clear_caches": ["self", "settings_cache", "import_cache"],
    "evaluate_preloads": ["self", "preloads", "ignore_import_errors", "package"],
    "evaluate_settings": [
        "self",
        "on_conflict",
        "ignore_import_errors",
        "ignore_preload_import_errors",
        "onetime",
    ],
    "set_instance": ["self", "instance", "apply_extensions", "use_extensions_overwrite"],
    "with_instance": ["self", "instance", "apply_extensions", "use_extensions_overwrite"],
    "with_settings": ["self", "settings", "evaluate_settings_with"],
    "with_extensions": ["self", "extensions", "apply_extensions"],
    "with_full_overwrite": [
        "self",
        "extensions",
        "settings",
        "instance",
        "apply_extensions",
        "evaluate_settings_with",
    ],
    "add_lazy_import": ["self", "name", "value", "no_hooks"],
    "add_deprecated_lazy_import": ["self", "name", "value", "no_hooks"],
    "add_extension": ["self", "extension", "use_overwrite", "on_conflict"],
    "apply_extensions": ["self", "use_overwrite"],
    "ensure_extension": ["self", "name_or_extension"],
    "find_missing": [
        "self",
        "all_var",
        "search_pathes",
        "ignore_deprecated_import_errors",
        "require_search_path_all_var",
    ],
    "sorted_exports": ["self", "all_var", "separate_by_category", "sort_by"],
    "update_all_var": ["self", "all_var"],
}


def _parameter_names(callable_obj: object) -> list[str]:
    return list(inspect.signature(callable_obj).parameters)


def test_top_level_exports_list_is_stable() -> None:
    assert monkay.__all__ == EXPECTED_TOP_LEVEL_EXPORTS


def test_top_level_exports_resolve_expected_symbols() -> None:
    assert monkay.Monkay is core.Monkay
    assert monkay.Cage is cages.Cage
    assert monkay.TransparentCage is cages.TransparentCage
    assert monkay.load is base.load
    assert monkay.load_any is base.load_any
    assert monkay.absolutify_import is base.absolutify_import
    assert monkay.get_value_from_settings is base.get_value_from_settings
    assert monkay.InGlobalsDict is base.InGlobalsDict
    assert monkay.UnsetError is base.UnsetError
    assert monkay.DeprecatedImport is monkay_types.DeprecatedImport
    assert monkay.PRE_ADD_LAZY_IMPORT_HOOK is monkay_types.PRE_ADD_LAZY_IMPORT_HOOK
    assert monkay.ExtensionProtocol is monkay_types.ExtensionProtocol


def test_public_submodule_exports_are_stable() -> None:
    assert asgi.__all__ == [
        "CMToASGIMiddleware",
        "Lifespan",
        "LifespanHook",
        "ASGIApp",
        "MuteInterruptException",
    ]


def test_monkay_constructor_signature_is_stable() -> None:
    parameters = list(inspect.signature(monkay.Monkay).parameters.values())
    assert [parameter.name for parameter in parameters] == EXPECTED_MONKAY_INIT_PARAMETERS
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[1:])


def test_public_function_signatures_are_stable() -> None:
    assert _parameter_names(base.load) == ["path", "allow_splits", "package"]
    assert _parameter_names(base.load_any) == ["path", "attrs", "non_first_deprecated", "package"]
    assert _parameter_names(base.absolutify_import) == ["import_path", "package"]
    assert _parameter_names(base.get_value_from_settings) == ["settings", "name"]
    assert _parameter_names(base.evaluate_preloads) == [
        "preloads",
        "ignore_import_errors",
        "package",
    ]


def test_cage_constructor_signature_is_stable() -> None:
    parameters = list(inspect.signature(cages.Cage).parameters.values())
    assert [parameter.name for parameter in parameters] == EXPECTED_CAGE_INIT_PARAMETERS
    assert parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert parameters[1].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in parameters[2:])


def test_asgi_signatures_are_stable() -> None:
    lifespan_params = list(inspect.signature(asgi.Lifespan).parameters.values())
    assert [parameter.name for parameter in lifespan_params] == ["app", "timeout"]
    assert lifespan_params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert lifespan_params[1].kind is inspect.Parameter.KEYWORD_ONLY

    hook_params = list(inspect.signature(asgi.LifespanHook).parameters.values())
    assert [parameter.name for parameter in hook_params] == ["app", "setup", "do_forward"]
    assert hook_params[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert hook_params[1].kind is inspect.Parameter.KEYWORD_ONLY
    assert hook_params[2].kind is inspect.Parameter.KEYWORD_ONLY


def test_monkay_method_signatures_are_stable() -> None:
    for method_name, expected_parameters in EXPECTED_MONKAY_METHOD_PARAMETERS.items():
        assert _parameter_names(getattr(monkay.Monkay, method_name)) == expected_parameters
