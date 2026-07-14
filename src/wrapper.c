#include "quickjs.h"
#include <string.h>
#include <stdlib.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif

// Simple function to evaluate JS and return a string
// Caller must free the returned string using free_js_wrapper_result
EXPORT const char* eval_js_wrapper(const char* script) {
    JSRuntime *rt = JS_NewRuntime();
    if (!rt) return NULL;
    JSContext *ctx = JS_NewContext(rt);
    if (!ctx) {
        JS_FreeRuntime(rt);
        return NULL;
    }
    
    JSValue val = JS_Eval(ctx, script, strlen(script), "<eval>", JS_EVAL_TYPE_GLOBAL);
    const char *str = JS_ToCString(ctx, val);
    
    char* result = NULL;
    if (str) {
        result = strdup(str);
        JS_FreeCString(ctx, str);
    }
    
    JS_FreeValue(ctx, val);
    JS_FreeContext(ctx);
    JS_FreeRuntime(rt);
    
    return result;
}

// Function to free the result string from python
EXPORT void free_js_wrapper_result(char* str) {
    if (str) free(str);
}
