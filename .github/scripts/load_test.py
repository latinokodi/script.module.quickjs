#!/usr/bin/env python3
"""Smoke-test a packaged QuickJS wrapper directory.

Used by CI after building the native libraries: loads the wrapper through
ctypes (pre-loading its qjs dependency) and asserts a few JS results.

Usage: python .github/scripts/load_test.py <directory>
"""
import ctypes
import os
import platform
import sys

WRAPPER_NAMES = ("qjswrapper.dll", "libqjswrapper.so", "libqjswrapper.dylib")
DEPENDENCY_NAMES = ("qjs.dll", "libqjs.so.0", "libqjs.so", "libqjs.0.dylib", "libqjs.dylib")

REQUIRED_KEYS = ("qjswrapper", "qjs")


def _find(directory, names):
    for name in names:
        path = os.path.join(directory, name)
        if os.path.exists(path):
            return path
    return None


def _load(directory):
    directory = os.path.abspath(directory)
    wrapper = _find(directory, WRAPPER_NAMES)
    if not wrapper:
        raise SystemExit("no qjswrapper found in %s" % directory)
    dependency = _find(directory, DEPENDENCY_NAMES)

    system = platform.system().lower()
    if system == "windows":
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(directory)
        if dependency:
            ctypes.CDLL(dependency)
        lib = ctypes.CDLL(wrapper)
    else:
        mode = getattr(ctypes, "RTLD_GLOBAL", 0)
        if dependency:
            ctypes.CDLL(dependency, mode=mode)
        lib = ctypes.CDLL(wrapper, mode=mode)

    lib.eval_js_wrapper.argtypes = [ctypes.c_char_p]
    lib.eval_js_wrapper.restype = ctypes.c_void_p
    lib.free_js_wrapper_result.argtypes = [ctypes.c_void_p]
    lib.free_js_wrapper_result.restype = None
    return lib


def _eval(lib, script):
    ptr = lib.eval_js_wrapper(script.encode("utf-8"))
    if not ptr:
        return None
    try:
        return ctypes.cast(ptr, ctypes.c_char_p).value.decode("utf-8")
    finally:
        lib.free_js_wrapper_result(ptr)


TESTS = (
    ("1+1", "2"),
    ("JSON.stringify({a:[1,2]})", '{"a":[1,2]}'),
    ("typeof Uint32Array", "function"),
    ("Math.imul(3,4)", "12"),
    ("Math.clz32(1)", "31"),
    (
        "var __o=[];var console={log:function(x){__o.push(String(x))}};"
        "console.log('ok');__o.join('')",
        "ok",
    ),
)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: %s <native-dir>" % sys.argv[0])
    directory = sys.argv[1]
    print("testing %s on %s/%s" % (directory, platform.system(), platform.machine()))
    lib = _load(directory)
    failures = 0
    for script, expected in TESTS:
        got = _eval(lib, script)
        ok = got == expected
        failures += 0 if ok else 1
        print("  %-14s -> %r %s" % (script[:14], got, "OK" if ok else "FAIL expected %r" % expected))
    if failures:
        raise SystemExit("%d QuickJS smoke test(s) failed" % failures)
    print("QuickJS wrapper OK")


if __name__ == "__main__":
    main()
