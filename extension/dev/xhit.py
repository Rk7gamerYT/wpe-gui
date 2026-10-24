"""Which X11 window is under the pointer at (x, y)? Uses XWarpPointer + XQueryPointer through ctypes.

The X server hit-tests by *its own* stacking order, so a full-screen X11 window on top swallows the clicks meant for
the X11 apps below it, whatever the Wayland compositor thinks.
"""
import ctypes
import ctypes.util
import subprocess
import sys

x11 = ctypes.CDLL(ctypes.util.find_library("X11"))
x11.XOpenDisplay.restype = ctypes.c_void_p
x11.XDefaultRootWindow.restype = ctypes.c_ulong
display = x11.XOpenDisplay(None)
root = x11.XDefaultRootWindow(ctypes.c_void_p(display))
px, py = int(sys.argv[1]), int(sys.argv[2])
x11.XWarpPointer(ctypes.c_void_p(display), ctypes.c_ulong(0), ctypes.c_ulong(root), 0, 0, 0, 0, px, py)
x11.XSync(ctypes.c_void_p(display), 0)
r, c = ctypes.c_ulong(), ctypes.c_ulong()
rx, ry, wx, wy = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
mask = ctypes.c_uint()
x11.XQueryPointer(ctypes.c_void_p(display), ctypes.c_ulong(root), ctypes.byref(r), ctypes.byref(c),
                  ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(mask))
child = c.value
name = subprocess.run(["xwininfo", "-id", hex(child)], capture_output=True, text=True).stdout.split("\n")[1:2] if child else ["(nenhuma: raiz)"]
print(f"ponteiro em {px},{py} -> janela X sob ele: {hex(child)} {name[0].strip()[:90]}")
