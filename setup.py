import os
import sys

import numpy as np
from setuptools import setup, Extension


###############################################
# Building the C++ extension
###############################################

extra_compile_args = ["-w", "-std=c++11", "-O3"]
extra_link_args = []

if sys.platform.startswith("darwin"):  # Mac

    extra_compile_args += ["-stdlib=libc++"]
    extra_link_args += ["-stdlib=libc++"]

    if "CC" in os.environ:
        extra_compile_args += ["-fopenmp"]

    elif os.popen("which clang").read().strip() != "/usr/bin/clang":
        cc = "clang"
        cc_catalina = (
            "clang --sysroot /Library/Developer/CommandLineTools/SDKs/MacOSX.sdk"
        )

        extra_compile_args += ["-fopenmp"]

        if " 10.15" in os.popen("sw_vers").read():
            os.environ["CC"] = cc_catalina
        elif " 10." in os.popen("sw_vers").read():
            os.environ["CC"] = cc
        else:
            os.environ["CC"] = cc_catalina

elif sys.platform.startswith("win"):  # Windows
    extra_compile_args = ["/w", "/openmp"]

else:  # Linux
    extra_compile_args += ["-fopenmp"]
    extra_link_args += ["-lgomp"]


cyaccess = Extension(
    name="pandana.cyaccess",
    sources=[
        "src/accessibility.cpp",
        "src/graphalg.cpp",
        "src/cyaccess.pyx",
        "src/contraction_hierarchies/src/libch.cpp",
    ],
    language="c++",
    include_dirs=[".", np.get_include()],
    extra_compile_args=extra_compile_args,
    extra_link_args=extra_link_args,
)

setup(ext_modules=[cyaccess])
