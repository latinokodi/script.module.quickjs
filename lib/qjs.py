import ctypes
import os
import platform

# Shared libqjs that the per-platform qjswrapper.* links against.  The wrapper
# binaries are kept small/dynamic on desktop OSes, so the dependency library
# must be shipped next to them and pre-loaded before the wrapper is loaded.
_WRAPPER_PLATFORMS = {
    'windows_x86_64': ('qjs.dll',),
    'linux_x86_64': ('libqjs.so.0', 'libqjs.so'),
    'darwin_x86_64': ('libqjs.0.dylib', 'libqjs.dylib'),
}


def get_lib_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == 'linux':
        if 'armv7' in machine or 'armv8l' in machine or 'armeabi' in machine:
            return os.path.join(base_dir, 'android_armv7', 'libqjswrapper.so')
        elif 'aarch64' in machine or 'arm64' in machine:
            return os.path.join(base_dir, 'android_arm64', 'libqjswrapper.so')
        else:
            return os.path.join(base_dir, 'linux_x86_64', 'libqjswrapper.so')
    elif system == 'windows':
        if '64' in machine:
            return os.path.join(base_dir, 'windows_x86_64', 'qjswrapper.dll')
        else:
            return os.path.join(base_dir, 'windows_x86', 'qjswrapper.dll')
    elif system == 'darwin':
        return os.path.join(base_dir, 'darwin_x86_64', 'libqjswrapper.dylib')
        
    return None


def get_platform_dir():
    """Return the directory name of the wrapper selected for this host."""
    lib_path = get_lib_path()
    if not lib_path:
        return None
    return os.path.basename(os.path.dirname(lib_path))


def _preload_dependency_library(wrapper_path):
    """Load the shared libqjs that the wrapper links against, if shipped here."""
    directory = os.path.dirname(wrapper_path)
    platform_dir = os.path.basename(directory)
    candidates = _WRAPPER_PLATFORMS.get(platform_dir)
    if not candidates:
        # Android/arm builds are statically linked - nothing to pre-load.
        return
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(directory)
        except OSError:
            pass
    for name in candidates:
        dependency_path = os.path.join(directory, name)
        if not os.path.exists(dependency_path):
            continue
        try:
            if platform.system().lower() == 'windows':
                ctypes.CDLL(dependency_path)
            else:
                ctypes.CDLL(dependency_path, mode=getattr(ctypes, 'RTLD_GLOBAL', 0))
        except OSError:
            # Leave it to the wrapper load to raise a meaningful error.
            pass
        return


class QuickJS:
    def __init__(self):
        lib_path = get_lib_path()
        if not lib_path or not os.path.exists(lib_path):
            raise Exception("Unsupported platform or missing QuickJS library: %s" % lib_path)
        
        _preload_dependency_library(lib_path)
        self.lib = ctypes.cdll.LoadLibrary(lib_path)
        
        # Setup eval_js_wrapper signature
        self.lib.eval_js_wrapper.argtypes = [ctypes.c_char_p]
        self.lib.eval_js_wrapper.restype = ctypes.POINTER(ctypes.c_char)
        
        # Setup free_js_wrapper_result signature
        self.lib.free_js_wrapper_result.argtypes = [ctypes.POINTER(ctypes.c_char)]
        self.lib.free_js_wrapper_result.restype = None

    def eval(self, script):
        if isinstance(script, str):
            script_bytes = script.encode('utf-8')
        else:
            script_bytes = script
            
        res_ptr = self.lib.eval_js_wrapper(script_bytes)
        if not res_ptr:
            return None
            
        try:
            # Cast the pointer to c_char_p and get the value
            result_bytes = ctypes.cast(res_ptr, ctypes.c_char_p).value
            if result_bytes is not None:
                return result_bytes.decode('utf-8')
            return None
        finally:
            # Safely free the memory allocated in C
            self.lib.free_js_wrapper_result(res_ptr)

# Convenience method mirroring existing runner syntax if needed
def eval_script(script):
    qjs = QuickJS()
    return qjs.eval(script)
