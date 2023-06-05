#include <dlfcn.h>

// XXX: Not thread-safe.

namespace {
#if defined(__linux__)
    const char* lib = "libvulkan.so.1";
#else
# error not implemented
#endif
    const char* sym = "vkGetInstanceProcAddr";

    void* hdl = nullptr;
    void* proc = nullptr;
}

void* initVK() {
    if (!hdl) {
        hdl = dlopen(lib, RTLD_LAZY | RTLD_LOCAL);
        if (!hdl)
            return nullptr;
    }
    if (!proc) {
        proc = dlsym(hdl, sym);
        if (!proc)
            return nullptr;
    }
    return proc;
}

void deinitVK() {
    if (hdl) {
        dlclose(hdl);
        hdl = nullptr;
        proc = nullptr;
    }
}
