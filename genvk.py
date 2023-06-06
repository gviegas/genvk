#!/usr/bin/env python3

# Created by Gustavo C. Viegas.
# Last change: 2023/jun.

from copy import deepcopy
import os
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import xml.etree.ElementTree


class Command:
    """Represents a vulkan procedure.

    vk.xml:
    registry > commands > proto[,params]."""

    GLOBAL = 0
    INSTANCE = 1
    DEVICE = 2

    def __init__(self, proto, params):
        self.proto = Command.Proto(proto)
        self.params = []
        for p in params:
            self.params.append(Command.Param(p))
        self.isext = self.proto.name[-1].isupper()
        if self.isext:
            self.ext = Extension(self)
        self.level = Command.GLOBAL
        if len(self.params) == 0:
            return
        s = self.params[0].typ
        if s == "VkInstance" or s == "VkPhysicalDevice":
            self.level = Command.INSTANCE
        elif s == "VkDevice" or s == "VkQueue" or s == "VkCommandBuffer":
            if self.proto.name != "vkGetDeviceProcAddr":
                self.level = Command.DEVICE
            else:
                # vkGetDeviceProcAddr is obtained from vkGetInstanceProcAddr
                # using a valid VkInstance handle.
                self.level = Command.INSTANCE

    def __str__(self):
        s = str(self.proto) + "(\n    "
        n = len(self.params)
        if n > 0:
            for i in range(n-1):
               s += str(self.params[i]) + ",\n    "
            s += str(self.params[n-1])
        s += ")"
        return s

    class TypeName:
        """registry > commands > command > *elem* > type,name."""
        def __init__(self, elem):
            name = elem.find("name")
            assert(name is not None and name.text is not None)
            self.name = name.text.strip()
            typ = elem.find("type")
            assert(typ is not None and typ.text is not None)
            self.typ = ""
            if elem.text is not None:
                self.typ = elem.text
            self.typ += typ.text
            if typ.tail is not None:
                self.typ += typ.tail
            self.typ = self.typ.strip()

        def __str__(self):
            return self.typ + " " + self.name

    class Proto(TypeName):
        """registry > commands > command > proto."""
        pass

    class Param(TypeName):
        """registry > commands > command > param."""
        pass


class Extension:
    """Composed with Command to represent procs that are extensions."""
    NA = 0
    COMMON = 1
    WAYLAND = 2
    WIN32 = 3
    XCB = 4

    GUARDS = {
        NA: ("", ""),
        COMMON: ("", ""),
        WAYLAND: ("#ifdef VK_USE_PLATFORM_WAYLAND_KHR\n", "#endif\n"),
        WIN32: ("#ifdef VK_USE_PLATFORM_WIN32_KHR\n", "#endif\n"),
        XCB: ("#ifdef VK_USE_PLATFORM_XCB_KHR\n", "#endif\n")
        }

    def __init__(self, command):
        self.category = Extension.NA
        if not command.isext:
            return
        for e in Extension.NAMES_COMMON:
            if e == command.proto.name:
                self.category = Extension.COMMON
                return
        for e in Extension.NAMES_WAYLAND:
            if e == command.proto.name:
                self.category = Extension.WAYLAND
                return
        for e in Extension.NAMES_WIN32:
            if e == command.proto.name:
                self.category = Extension.WIN32
                return
        for e in Extension.NAMES_XCB:
            if e == command.proto.name:
                self.category = Extension.XCB
                return

    NAMES_COMMON = [
        # From VK_KHR_surface:
        "vkDestroySurfaceKHR",
        "vkGetPhysicalDeviceSurfaceCapabilitiesKHR",
        "vkGetPhysicalDeviceSurfaceFormatsKHR",
        "vkGetPhysicalDeviceSurfacePresentModesKHR",
        "vkGetPhysicalDeviceSurfaceSupportKHR",
        # From VK_KHR_swapchain:
        "vkAcquireNextImageKHR",
        "vkCreateSwapchainKHR",
        "vkDestroySwapchainKHR",
        "vkGetSwapchainImagesKHR",
        "vkQueuePresentKHR",
        # From VK_KHR_copy_commands2 (core in v1.3):
        "vkCmdBlitImage2KHR",
        "vkCmdCopyBuffer2KHR",
        "vkCmdCopyBufferToImage2KHR",
        "vkCmdCopyImage2KHR",
        "vkCmdCopyImageToBuffer2KHR",
        "vkCmdResolveImage2KHR",
        # From VK_KHR_dynamic_rendering (core in v1.3):
        "vkCmdBeginRenderingKHR",
        "vkCmdEndRenderingKHR",
        # From VK_KHR_synchronization2 (core in v1.3):
        "vkCmdPipelineBarrier2KHR",
        "vkCmdResetEvent2KHR",
        "vkCmdSetEvent2KHR",
        "vkCmdWaitEvents2KHR",
        "vkCmdWriteTimestamp2KHR",
        "vkQueueSubmit2KHR",
        # From VK_KHR_buffer_device_address (core in v1.2 (optional) & v1.3):
        "vkGetBufferDeviceAddressKHR",
        "vkGetBufferOpaqueCaptureAddressKHR",
        "vkGetDeviceMemoryOpaqueCaptureAddressKHR",
        # From VK_KHR_create_renderpass2 (core in v1.2):
        "vkCmdBeginRenderPass2KHR",
        "vkCmdEndRenderPass2KHR",
        "vkCmdNextSubpass2KHR",
        "vkCreateRenderPass2KHR",
        # From VK_KHR_device_group (core in v1.1):
        "vkCmdDispatchBaseKHR",
        "vkCmdSetDeviceMaskKHR",
        "vkGetDeviceGroupPeerMemoryFeaturesKHR",
        "vkGetDeviceGroupPresentCapabilitiesKHR",
        "vkGetDeviceGroupSurfacePresentModesKHR",
        "vkGetPhysicalDevicePresentRectanglesKHR",
        "vkAcquireNextImage2KHR",
        # From VK_KHR_device_group_creation (core in v1.1):
        "vkEnumeratePhysicalDeviceGroupsKHR",
        # From VK_KHR_get_physical_device_properties2 (core in v1.1):
        "vkGetPhysicalDeviceFeatures2KHR",
        "vkGetPhysicalDeviceFormatProperties2KHR",
        "vkGetPhysicalDeviceImageFormatProperties2KHR",
        "vkGetPhysicalDeviceMemoryProperties2KHR",
        "vkGetPhysicalDeviceProperties2KHR",
        "vkGetPhysicalDeviceQueueFamilyProperties2KHR",
        "vkGetPhysicalDeviceSparseImageFormatProperties2KHR",
        ]

    NAMES_WAYLAND = [
        # From VK_KHR_wayland_surface:
        "vkCreateWaylandSurfaceKHR",
        "vkGetPhysicalDeviceWaylandPresentationSupportKHR",
        ]

    NAMES_WIN32 = [
        # From VK_KHR_win32_surface:
        "vkCreateWin32SurfaceKHR",
        "vkGetPhysicalDeviceWin32PresentationSupportKHR",
        ]

    NAMES_XCB = [
        # From VK_KHR_xcb_surface:
        "vkCreateXcbSurfaceKHR",
        "vkGetPhysicalDeviceXcbPresentationSupportKHR",
        ]


# TODO: Currently, this is only used for filtering non-core commands.
class Feature:
    """registry > feature."""
    def __init__(self, feature):
        assert(feature.tag == "feature")
        self.name = feature.attrib["name"]
        self.cmds = [x.get("name") for x in feature.findall("./require/command")]
        self.noncore = re.match(r"(^|(.+,))vulkan((,.+)|$)", feature.get("api")) is None


class Version:
    """Used to extract the header version for informational purposes."""
    def __init__(self, types):
        assert(types.tag == "types")
        self.major = ""
        self.minor = ""
        self.patch = ""
        defs = types.findall("./type[@api='vulkan'][@category='define']")
        for d in defs:
            name = d.find("name")
            if name is None:
                continue
            if name.text == "VK_HEADER_VERSION":
                self.patch = name.tail.strip()
            if name.text == "VK_HEADER_VERSION_COMPLETE":
                typ = d.find("type")
                assert(typ is not None)
                s = typ.tail.split(",")
                assert(len(s) >= 3)
                self.minor = s[-2].strip()
                self.major = s[-3].strip(' (')

    def __str__(self):
        return "{}.{}.{}".format(self.major, self.minor, self.patch)


HEADER = """// Code generated by genvk.py. DO NOT EDIT.
// [vk.xml {}]

#ifndef GENVK_VK_H
#define GENVK_VK_H

#define VK_NO_PROTOTYPES
#if defined(__linux__)
# define VK_USE_PLATFORM_WAYLAND_KHR
# define VK_USE_PLATFORM_XCB_KHR
#elif defined(_WIN32)
# define VK_USE_PLATFORM_WIN32_KHR
#endif
#include <vulkan/vulkan.h>

#ifdef __cplusplus
extern "C" {{
#endif

// Function pointers.
{}
// Functions that obtain the function pointers.
// The usage is as follows:
//  1. Call getGlobalProcsVK and check that vkGetInstanceProcAddr is valid;
//  2. Create a valid VkInstance and call getInstanceProcsVK;
//  3. Create a valid VkDevice and call getDeviceProcsVK;
//  4. Call clearProcsVK before exiting.
{}
{}

#ifdef __cplusplus
}}
#endif

#endif // GENVK_VK_H
"""


SOURCE = """// Code generated by genvk.py. DO NOT EDIT.
// [vk.xml {}]

#include "vk.h"

{}
// Defined in dlvk.cpp.
void* initVK();
void deinitVK();

{}
{}
"""


INDENT = "    "


INIT_CALL = """vkGetInstanceProcAddr = reinterpret_cast<PFN_vkGetInstanceProcAddr>(initVK());
{0}if (!vkGetInstanceProcAddr)
{0}{0}return;
""".format(INDENT)


DEINIT_CALL = """deinitVK();
"""


DLVK_CPP = "dlvk.cpp"
DLVK_OBJ = "dlvk.o"
VK_CPP = "vk.cpp"
VK_OBJ = "vk.o"
VK_H = "vk.h"
VK_LIB = "vk.lib"


def gen_getters(commands, as_decls):
    """Returns a string containing the proc getters."""
    if as_decls:
        globl = "void getGlobalProcsVK(void);\n"
        inst = "void getInstanceProcsVK(VkInstance);\n"
        dev = "void getDeviceProcsVK(VkDevice);"
        return globl + inst + dev

    fp = INDENT + "PFN_vkVoidFunction fp = nullptr;\n"
    globl = "void getGlobalProcsVK() {\n" + INDENT + INIT_CALL + fp
    inst = "void getInstanceProcsVK(VkInstance h) {\n" + fp
    dev = "void getDeviceProcsVK(VkDevice h) {\n" + fp
    gext = {}
    iext = {}
    dext = {}
    gfmt = INDENT + 'fp = vkGetInstanceProcAddr(nullptr, "{}");\n'
    gfmt += INDENT + "{} = reinterpret_cast<PFN_{}>(fp);\n"
    ifmt = INDENT + 'fp = vkGetInstanceProcAddr(h, "{}");\n'
    ifmt += INDENT + "{} = reinterpret_cast<PFN_{}>(fp);\n"
    dfmt = INDENT + 'fp = vkGetDeviceProcAddr(h, "{}");\n'
    dfmt += INDENT + "{} = reinterpret_cast<PFN_{}>(fp);\n"

    for cmd in commands:
        name = cmd.proto.name
        if not name.startswith("vk"):
            continue
        if name == "vkGetInstanceProcAddr":
            # vkGetInstanceProcAddr is obtained by other means.
            continue
        if not cmd.isext:
            if cmd.level == Command.DEVICE:
                dev += dfmt.format(name, name, name)
            elif cmd.level == Command.INSTANCE:
                inst += ifmt.format(name, name, name)
            else:
                globl += gfmt.format(name, name, name)
        else:
            categ = cmd.ext.category
            if categ == Extension.NA:
                continue
            if cmd.level == Command.DEVICE:
                if not categ in dext:
                    dext[categ] = ""
                dext[categ] += dfmt.format(name, name, name)
            elif cmd.level == Command.INSTANCE:
                if not categ in iext:
                    iext[categ] = ""
                iext[categ] += ifmt.format(name, name, name)
            else:
                if not categ in gext:
                    gext[categ] = ""
                gext[categ] += gfmt.format(name, name, name)

    items = gext.items()
    for (k, v) in items:
        if v != "":
            globl += cmd.ext.GUARDS[k][0] + v + cmd.ext.GUARDS[k][1]
    items = iext.items()
    for (k, v) in items:
        if v != "":
            inst += cmd.ext.GUARDS[k][0] + v + cmd.ext.GUARDS[k][1]
    items = dext.items()
    for (k, v) in items:
        if v != "":
            dev += cmd.ext.GUARDS[k][0] + v + cmd.ext.GUARDS[k][1]
    globl += "}\n\n"
    inst += "}\n\n"
    dev += "}\n"
    return globl + inst + dev


def gen_procs(commands, proc_fmt):
    """Returns a string containing the formatted procs."""
    procs = ""
    exts = {}
    for cmd in commands:
        name = cmd.proto.name
        if not name.startswith("vk"):
            continue
        if not cmd.isext:
            procs += proc_fmt.format(name)
            continue
        categ = cmd.ext.category
        if categ == Extension.NA:
            continue
        if not categ in exts:
            exts[categ] = ""
        exts[categ] += proc_fmt.format(name)
    items = exts.items()
    for (k, v) in items:
        if v != "":
            procs += cmd.ext.GUARDS[k][0] + v + cmd.ext.GUARDS[k][1]
    return procs


def gen_vars(commands, as_decls):
    """Returns a string containing the proc variables."""
    return gen_procs(commands, "extern PFN_{0} {0};\n" if as_decls else "PFN_{0} {0} = nullptr;\n")


def gen_clear(commands, as_decl):
    """Returns a string containing the proc clearing function."""
    if as_decl:
        return "void clearProcsVK(void);"
    procs = gen_procs(commands, INDENT + "{} = nullptr;\n")
    return "void clearProcsVK() {\n" + procs + INDENT + DEINIT_CALL + "}"


def gen_commands(registry):
    """Returns a list containing Commands from the registry."""
    noncore_feats = [x for x in [Feature(x) for x in registry.findall("feature")] if x.noncore]
    noncore_cmds = frozenset()
    for feat in noncore_feats:
        noncore_cmds = noncore_cmds.union(feat.cmds)

    cmds = registry.find("commands")
    if cmds is None:
        print("[!] bad xml file: 'commands' element not found")
        exit()
    each_cmd = cmds.findall("command")

    aliases = {}
    for cmd in each_cmd:
        if cmd.get("api") not in (None, "vulkan"):
            continue
        alias = cmd.get("alias")
        name = cmd.get("name")
        if alias is not None and name is not None:
            # TODO: Do multiple aliases exist?
            aliases[alias] = name
            # TODO: Remove element instead.
            assert(cmd.find("proto") is None)

    objs = []
    for cmd in each_cmd:
        if cmd.get("api") not in (None, "vulkan"):
            continue
        proto = cmd.find("proto")
        if proto is None:
            continue
        params = cmd.findall("param")
        obj = Command(proto, params)
        if obj.proto.name in noncore_cmds:
            continue
        objs.append(obj)
        try:
            alias = aliases[obj.proto.name]
            cpy = deepcopy(obj)
            cpy.proto.name = alias
            objs.append(cpy)
        except KeyError:
            pass
    return objs


def gen_version(registry):
    """Returns a Version instance identifying the header version."""
    types = registry.find("types")
    if types is None:
        print("[!] bad xml file: 'types' element not found")
        exit()
    return Version(types)


def gen_lib():
    if os.name == "posix":
        # Assume gcc/clang.
        cpl = ["c++", "-O2", "-c"]
        subprocess.run(cpl + [DLVK_CPP], check=True)
        subprocess.run(cpl + [VK_CPP], check=True)
        subprocess.run(["ar", "rcs", VK_LIB, DLVK_OBJ, VK_OBJ], check=True)
    else:
        # TODO
        print("[!] gen_lib not yet implemented for " + os.name)
        exit()


def gen(xml_path):
    """Generates the proc files from the given vk.xml registry."""
    tree = xml.etree.ElementTree.parse(xml_path)
    root = tree.getroot()
    if root.tag != "registry":
        print("[!] bad xml file: unexpected root element '" + root.tag + "'")
        exit()
    commands = gen_commands(root)
    version = gen_version(root)
    with TemporaryDirectory() as tmpdir:
        cwd = os.getcwd()
        os.chdir(tmpdir)
        with open(VK_H, "w") as f:
            vars = gen_vars(commands, True)
            getters = gen_getters(commands, True)
            clear = gen_clear(commands, True)
            f.write(HEADER.format(version, vars, getters, clear))
        with open(VK_CPP, "w") as f:
            vars = gen_vars(commands, False)
            getters = gen_getters(commands, False)
            clear = gen_clear(commands, False)
            f.write(SOURCE.format(version, vars, getters, clear))
        os.link(os.path.join(cwd, DLVK_CPP), os.path.join(tmpdir, DLVK_CPP))
        gen_lib()
        os.chdir(cwd)
        os.rename(os.path.join(tmpdir, VK_H), os.path.join(cwd, VK_H))
        os.rename(os.path.join(tmpdir, VK_LIB), os.path.join(cwd, VK_LIB))


if __name__ == "__main__":
    pathname = ""
    oflag = ""
    for a in sys.argv[1:]:
        if a == "-w" and oflag == "":
            oflag = "w"
        elif a[0] != "-" and pathname == "":
            pathname = a
        else:
            print("usage:\n\t{} [vk.xml] [-w]".format(sys.argv[0]))
            exit()
    if pathname == "":
        pathname = "vk.xml"
    if oflag != "w":
        # BUG: Fix this.
        # os.rename (called by gen) has inconsistent behavior
        # (need something like renameat2 with RENAME_NOREPLACE).
        for p in [VK_H, VK_LIB]:
            try:
                f = open(p)
                f.close()
                print("[!] file '{}' exists".format(p))
                exit()
            except FileNotFoundError:
                pass
    gen(pathname)
