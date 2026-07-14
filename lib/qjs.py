import ctypes
import os
import platform

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

class QuickJS:
    def __init__(self):
        lib_path = get_lib_path()
        if not lib_path or not os.path.exists(lib_path):
            raise Exception("Unsupported platform or missing QuickJS library: %s" % lib_path)
        
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
