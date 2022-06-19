#!/usr/bin/env python3

# Created by Gustavo C. Viegas.
# Last change: 2022/jun.

import xml.etree.ElementTree
import sys


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
        """ registry > commands > command > *elem* > type,name """
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
        """ registry > commands > command > proto """
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
        "vkQueuePresentKHR"
        ]

    NAMES_WAYLAND = [
        # From VK_KHR_wayland_surface:
        "vkCreateWaylandSurfaceKHR",
        "vkGetPhysicalDeviceWaylandPresentationSupportKHR",
        ]

    NAMES_WIN32 = [
        # From VK_KHR_win32_surface:
        "vkCreateWin32SurfaceKHR",
        "vkGetPhysicalDeviceWin32PresentationSupportKHR"
        ]

    NAMES_XCB = [
        # From VK_KHR_xbc_surface:
        "vkCreateXcbSurfaceKHR",
        "vkGetPhysicalDeviceXcbPresentationSupportKHR"
        ]


class Version:
    """Used to extract the header version for informational purposes."""
    def __init__(self, types):
        assert(types.tag == "types")
        self.major = ""
        self.minor = ""
        self.patch = ""
        defs = types.findall("./type[@category='define']")
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


header = """/* Code generated by genvk.py.
   [vk.xml {}] */

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

/* Function pointers. */
{}
/* Functions that obtain the function pointers.
   The process of obtaining the procedures for use is as follows:
   1. Fetch the vkGetInstanceProcAddr symbol;
   2. Call get_globl_procs_vk;
   3. Create a valid VkInstance and call get_inst_procs_vk;
   4. Create a valid VkDevice and call get_dev_procs_vk. */
{}

#ifdef __cplusplus
}}
#endif

#endif /* GENVK_VK_H */
"""


source = """/* Code generated by genvk.py.
   [vk.xml {}] */

#include <assert.h>
#include "vk.h"

{}
{}
"""


indent = "      "


def gen_getters(commands, as_decls):
    """Returns a string containing the proc getters."""
    if as_decls:
        globl = "void get_globl_procs_vk(void);\n"
        inst = "void get_inst_procs_vk(VkInstance);\n"
        dev = "void get_dev_procs_vk(VkDevice);"
        return globl + inst + dev

    fp = indent + "PFN_vkVoidFunction fp = NULL;\n"
    globl = "void\nget_globl_procs_vk(void)\n{\n" + fp
    inst = "void\nget_inst_procs_vk(VkInstance h)\n{\n" + fp
    dev = "void\nget_dev_procs_vk(VkDevice h)\n{\n" + fp
    gext = {}
    iext = {}
    dext = {}
    gfmt = indent + 'fp = vkGetInstanceProcAddr(NULL, "{}");\n'
    gfmt += indent + "{} = (PFN_{})fp;\n"
    ifmt = indent + 'fp = vkGetInstanceProcAddr(h, "{}");\n'
    ifmt += indent + "{} = (PFN_{})fp;\n"
    dfmt = indent + 'fp = vkGetDeviceProcAddr(h, "{}");\n'
    dfmt += indent + "{} = (PFN_{})fp;\n"

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
    dev += "}"
    return globl + inst + dev


def gen_procs(commands, as_decls):
    """Returns a string containing the proc variables."""
    procs = ""
    exts = {}
    fmt = "extern PFN_{} {};\n" if as_decls else "PFN_{} {} = NULL;\n"
    for cmd in commands:
        name = cmd.proto.name
        if not name.startswith("vk"):
            continue
        if not cmd.isext:
            procs += fmt.format(name, name)
            continue
        categ = cmd.ext.category
        if categ == Extension.NA:
            continue
        if not categ in exts:
            exts[categ] = ""
        exts[categ] += fmt.format(name, name)
    items = exts.items()
    for (k, v) in items:
        if v != "":
            procs += cmd.ext.GUARDS[k][0] + v + cmd.ext.GUARDS[k][1]
    return procs


def gen_commands(registry):
    """Returns a list containing a Command for every proc in the registry."""
    cmds = registry.find("commands")
    if cmds is None:
        print("[!] bad xml file: 'commands' element not found")
        exit()
    objs = []
    for cmd in cmds.findall("command"):
        proto = cmd.find("proto")
        if proto is None:
            continue
        params = cmd.findall("param")
        objs.append(Command(proto, params))
    return objs


def gen_version(registry):
    """Returns a Version instance identifying the header version."""
    types = registry.find("types")
    if types is None:
        print("[!] bad xml file: 'types' element not found")
        exit()
    return Version(types)


def gen(pathname, oflag):
    """Generates the proc files from the given vk.xml registry."""
    tree = xml.etree.ElementTree.parse(pathname)
    root = tree.getroot()
    if root.tag != "registry":
        print("[!] bad xml file: unexpected root element '" + root.tag + "'")
        exit()
    commands = gen_commands(root)
    version = gen_version(root)
    with open("vk.h", oflag) as f:
        procs = gen_procs(commands, True)
        getters = gen_getters(commands, True)
        f.write(header.format(version, procs, getters))
    with open("vk.c", oflag) as f:
        procs = gen_procs(commands, False)
        getters = gen_getters(commands, False)
        f.write(source.format(version, procs, getters))


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
    if oflag == "":
        oflag = "x"
    gen(pathname, oflag)
