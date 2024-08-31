// XXX: Not thread-safe.

namespace { const char* sym = "vkGetInstanceProcAddr"; }

#ifdef _WIN32

#include <windows.h>

namespace {
const char* lib = "vulkan-1.dll";

HMODULE hdl = nullptr;
FARPROC proc = nullptr;

void setHdl() { hdl = LoadLibrary(lib); }
void setProc() { proc = GetProcAddress(hdl, sym); }
void closeLib() { FreeLibrary(hdl); }
}

#else

#include <dlfcn.h>

namespace {
#if defined(__ANDROID__)
const char* lib = "libvulkan.so";
#elif defined(__linux__)
const char* lib = "libvulkan.so.1";
#else
#error Not implemented
#endif

void* hdl = nullptr;
void* proc = nullptr;

void setHdl() { hdl = dlopen(lib, RTLD_LAZY | RTLD_LOCAL); }
void setProc() { proc = dlsym(hdl, sym); }
void closeLib() { dlclose(hdl); }
}

#endif

void* initVK()
{
    if (!hdl) {
        setHdl();
        if (!hdl)
            return nullptr;
    }
    if (!proc) {
        setProc();
        if (!proc)
            return nullptr;
    }
    return reinterpret_cast<void*>(proc);
}

void deinitVK()
{
    if (hdl) {
        closeLib();
        hdl = nullptr;
        proc = nullptr;
    }
}
