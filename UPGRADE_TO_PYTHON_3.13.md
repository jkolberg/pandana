# Pandana: Upgrade to Python 3.13 — Step-by-Step Instructions

These instructions will upgrade the Pandana library to support Python 3.13+.
Follow each step in exact order. Each step specifies the exact file, the exact
text to find, and the exact replacement text. Do not deviate from the instructions.

There are 6 steps total. All file paths are relative to the repository root.

---

## STEP 1: Update pyproject.toml build dependencies

**File:** `pyproject.toml`

**Why:** The `oldest-supported-numpy` package is discontinued and has no wheels
for Python 3.13+. Cython 0.25.2 is far too old — Python 3.13 requires
Cython >= 3.0.8. These two issues completely prevent the package from building.

**Find this exact text:**
```
[build-system]
# Requirements for building the compiled package
requires = [
        "wheel",
        "setuptools >=40.8",
        "cython >=0.25.2",
        "oldest-supported-numpy"
]
build-backend = "setuptools.build_meta"
```

**Replace with this exact text:**
```
[build-system]
# Requirements for building the compiled package
requires = [
        "wheel",
        "setuptools >=65.0",
        "cython >=3.0.8",
        "numpy >=2.0"
]
build-backend = "setuptools.build_meta"
```

**What changed:** 
- `setuptools >=40.8` → `setuptools >=65.0` (needed for modern Python)
- `cython >=0.25.2` → `cython >=3.0.8` (needed for Python 3.13 support)
- `oldest-supported-numpy` → `numpy >=2.0` (the replacement; NumPy 2.0 is the first to support 3.13)

---

## STEP 2: Update setup.py install dependencies, classifiers, and python_requires

**File:** `setup.py`

**Why:** The minimum dependency versions are so old they don't support Python 3.13.
There is also no `python_requires` field, so pip doesn't gate installations on
unsupported Python versions. The classifiers stop at Python 3.11.

### STEP 2a: Add python_requires to setup()

**Find this exact text:**
```
    url="https://udst.github.io/pandana/",
    ext_modules=[cyaccess],
    install_requires=[
```

**Replace with this exact text:**
```
    url="https://udst.github.io/pandana/",
    ext_modules=[cyaccess],
    python_requires=">=3.9",
    install_requires=[
```

### STEP 2b: Update install_requires version minimums

**Find this exact text:**
```
    install_requires=[
        'numpy >=1.8',
        'pandas >=0.17',
        'requests >=2.0',
        'scikit-learn >=0.18',
        'tables >=3.1'
    ],
```

**Replace with this exact text:**
```
    install_requires=[
        'numpy >=1.26',
        'pandas >=1.5',
        'requests >=2.0',
        'scikit-learn >=1.3',
        'tables >=3.9'
    ],
```

### STEP 2c: Update classifiers

**Find this exact text:**
```
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: GNU Affero General Public License v3",
    ],
```

**Replace with this exact text:**
```
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: GNU Affero General Public License v3",
    ],
```

---

## STEP 3: Rewrite src/cyaccess.pyx (the Cython bridge)

**File:** `src/cyaccess.pyx`

**Why:** This is the most critical change. The file uses the old `np.ndarray[type]`
buffer syntax throughout, which is deprecated in Cython 3 and incompatible with
NumPy 2.0's C-API. It also never calls `np.import_array()`, which causes segfaults
with NumPy 2.0+. The entire file must be replaced.

**Replace the ENTIRE contents of `src/cyaccess.pyx` with the following:**

```cython
#cython: language_level=3

cimport cython
from libcpp cimport bool
from libcpp.vector cimport vector
from libcpp.string cimport string
from libcpp.pair cimport pair

import numpy as np
cimport numpy as np

np.import_array()

# resources
# http://cython.readthedocs.io/en/latest/src/userguide/wrapping_CPlusPlus.html
# http://www.birving.com/blog/2014/05/13/passing-numpy-arrays-between-python-and/


cdef extern from "accessibility.h" namespace "MTC::accessibility":
    cdef cppclass Accessibility:
        Accessibility(int, vector[vector[long]], vector[vector[double]], bool) except +
        vector[string] aggregations
        vector[string] decays
        void initializeCategory(double, int, string, vector[long])
        pair[vector[vector[double]], vector[vector[int]]] findAllNearestPOIs(
            float, int, string, int)
        void initializeAccVar(string, vector[long], vector[double])
        vector[double] getAllAggregateAccessibilityVariables(
            float, string, string, string, int)
        vector[int] Route(int, int, int)
        vector[vector[int]] Routes(vector[long], vector[long], int)
        double Distance(int, int, int)
        vector[double] Distances(vector[long], vector[long], int)
        vector[vector[pair[long, float]]] Range(vector[long], float, int, vector[long])
        void precomputeRangeQueries(double)


cdef convert_vector_to_array_dbl(vector[double] vec):
    cdef np.ndarray arr = np.zeros(len(vec), dtype="double")
    for i in range(len(vec)):
        arr[i] = vec[i]
    return arr


cdef convert_2D_vector_to_array_dbl(vector[vector[double]] vec):
    cdef np.ndarray arr = np.empty_like(vec, dtype="double")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[i][j] = vec[i][j]
    return arr


cdef convert_2D_vector_to_array_int(vector[vector[int]] vec):
    cdef np.ndarray arr = np.empty_like(vec, dtype="int")
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            arr[i][j] = vec[i][j]
    return arr


cdef class cyaccess:
    cdef Accessibility * access

    def __cinit__(
        self,
        long[::1] node_ids,
        double[:, ::1] node_xys,
        long[:, ::1] edges,
        double[:, ::1] edge_weights,
        bool twoway=True
    ):
        """
        node_ids: vector of node identifiers
        node_xys: the spatial locations of the same nodes
        edges: a pair of node ids which comprise each edge
        edge_weights: the weights (impedances) that apply to each edge
        twoway: whether the edges should all be two-way or whether they
            are directed from the first to the second node
        """
        self.access = new Accessibility(node_ids.shape[0], edges, edge_weights, twoway)

    def __dealloc__(self):
        del self.access

    def initialize_category(
        self,
        double maxdist,
        int maxitems,
        string category,
        long[::1] node_ids
    ):
        """
        maxdist - the maximum distance that will later be used in
            find_all_nearest_pois
        maxitems - the maximum number of items that will later be requested
            in find_all_nearest_pois
        category - the category name
        node_ids - an array of nodeids which are locations where this poi occurs
        """
        self.access.initializeCategory(maxdist, maxitems, category, node_ids)

    def find_all_nearest_pois(
        self,
        double radius,
        int num_of_pois,
        string category,
        int impno=0
    ):
        """
        radius - search radius
        num_of_pois - number of pois to search for
        category - the category name
        impno - the impedance id to use
        """
        ret = self.access.findAllNearestPOIs(radius, num_of_pois, category, impno)

        return convert_2D_vector_to_array_dbl(ret.first),\
            convert_2D_vector_to_array_int(ret.second)

    def initialize_access_var(
        self,
        string category,
        long[::1] node_ids,
        double[::1] values
    ):
        """
        category - category name
        node_ids: vector of node identifiers
        values: vector of values that are location at the nodes
        """
        self.access.initializeAccVar(category, node_ids, values)

    def get_available_aggregations(self):
        return self.access.aggregations

    def get_available_decays(self):
        return self.access.decays

    def get_all_aggregate_accessibility_variables(
        self,
        double radius,
        category,
        aggtyp,
        decay,
        int impno=0,
    ):
        """
        radius - search radius
        category - category name
        aggtyp - aggregation type, see docs
        decay - decay type, see docs
        impno - the impedance id to use
        """
        ret = self.access.getAllAggregateAccessibilityVariables(
            radius, category, aggtyp, decay, impno)

        return convert_vector_to_array_dbl(ret)

    def shortest_path(self, int srcnode, int destnode, int impno=0):
        """
        srcnode - node id origin
        destnode - node id destination
        impno - the impedance id to use
        """
        return self.access.Route(srcnode, destnode, impno)

    def shortest_paths(self, long[::1] srcnodes,
            long[::1] destnodes, int impno=0):
        """
        srcnodes - node ids of origins
        destnodes - node ids of destinations
        impno - impedance id
        """
        return self.access.Routes(srcnodes, destnodes, impno)

    def shortest_path_distance(self, int srcnode, int destnode, int impno=0):
        """
        srcnode - node id origin
        destnode - node id destination
        impno - the impedance id to use
        """
        return self.access.Distance(srcnode, destnode, impno)

    def shortest_path_distances(self, long[::1] srcnodes,
            long[::1] destnodes, int impno=0):
        """
        srcnodes - node ids of origins
        destnodes - node ids of destinations
        impno - impedance id
        """
        return self.access.Distances(srcnodes, destnodes, impno)

    def precompute_range(self, double radius):
        self.access.precomputeRangeQueries(radius)

    def nodes_in_range(self, vector[long] srcnodes, float radius, int impno,
            long[::1] ext_ids):
        """
        srcnodes - node ids of origins
        radius - maximum range in which to search for nearby nodes
        impno - the impedance id to use
        ext_ids - all node ids in the network
        """
        return self.access.Range(srcnodes, radius, impno, ext_ids)
```

**Summary of what changed in this file:**

1. Added `np.import_array()` call after the numpy cimport (line 12). This is
   REQUIRED by NumPy 2.0+ or the extension will segfault on import.

2. Removed typed return annotations from the three helper functions. Changed:
   - `cdef np.ndarray[double] convert_vector_to_array_dbl(...)` → `cdef convert_vector_to_array_dbl(...)`
   - `cdef np.ndarray[double, ndim = 2] convert_2D_vector_to_array_dbl(...)` → `cdef convert_2D_vector_to_array_dbl(...)`
   - `cdef np.ndarray[int, ndim = 2] convert_2D_vector_to_array_int(...)` → `cdef convert_2D_vector_to_array_int(...)`
   
   The `np.ndarray[type]` syntax in return type position is deprecated.

3. Changed all `np.ndarray[type]` parameter types to typed memoryviews:
   - `np.ndarray[long]` → `long[::1]`
   - `np.ndarray[double, ndim=2]` → `double[:, ::1]`
   - `np.ndarray[long, ndim=2]` → `long[:, ::1]`
   - `np.ndarray[double]` → `double[::1]`
   
   The `[::1]` suffix means C-contiguous memory layout (same as what numpy
   arrays use by default). This is the modern Cython way to accept array
   arguments.

4. In `__cinit__`, changed `len(node_ids)` to `node_ids.shape[0]` because
   typed memoryviews don't support `len()` — they use `.shape[N]` instead.

5. Everything else (docstrings, logic, C++ extern declarations, method names)
   is UNCHANGED.

---

## STEP 4: Update requirements-dev.txt

**File:** `requirements-dev.txt`

**Why:** `pytest>=3.6,<4.0` will not install on Python 3.13 (pytest 3.x is
incompatible). `pytest-cov<2.10` is similarly ancient and broken on modern Python.

**Find this exact text:**
```
# requirements for development and testing

coveralls
numpydoc
pycodestyle
pytest>=3.6,<4.0
pytest-cov<2.10
sphinx
sphinx_rtd_theme
```

**Replace with this exact text:**
```
# requirements for development and testing

coveralls
numpydoc
pycodestyle
pytest>=7.0
pytest-cov
sphinx
sphinx_rtd_theme
```

**What changed:**
- `pytest>=3.6,<4.0` → `pytest>=7.0` (removed upper pin, set reasonable minimum)
- `pytest-cov<2.10` → `pytest-cov` (removed upper pin)

---

## STEP 5: Remove Python 2 __future__ imports

These imports (`from __future__ import division, print_function`) were needed for
Python 2 compatibility. They are no-ops in Python 3 and should be removed for clarity.

### STEP 5a: pandana/network.py

**File:** `pandana/network.py`

**Find this exact text (the first line of the file):**
```
from __future__ import division, print_function

import numpy as np
```

**Replace with this exact text:**
```
import numpy as np
```

### STEP 5b: examples/simple_example.py

**File:** `examples/simple_example.py`

**Find this exact text:**
```
from __future__ import print_function

import os.path
```

**Replace with this exact text:**
```
import os.path
```

### STEP 5c: examples/shortest_path_example.py

**File:** `examples/shortest_path_example.py`

**Find this exact text:**
```
from __future__ import print_function

import os.path
```

**Replace with this exact text:**
```
import os.path
```

---

## STEP 6: Update the version number

**File:** `pandana/__init__.py`

**Find this exact text:**
```
from .network import Network

version = __version__ = '0.7'
```

**Replace with this exact text:**
```
from .network import Network

version = __version__ = '0.7.1'
```

**File:** `setup.py`

**Find this exact text:**
```
version = "0.7"
```

**Replace with this exact text:**
```
version = "0.7.1"
```

---

## VERIFICATION

After making all changes, run these commands from the repository root to verify:

```bash
# 1. Install build dependencies
pip install "cython>=3.0.8" "numpy>=2.0" "setuptools>=65.0" wheel

# 2. Build the extension in-place (this compiles the C++ and Cython)
python setup.py build_ext --inplace

# 3. Run the test suite
pip install pytest
pytest tests/ -v
```

**Expected result:** The build should complete without errors and all tests should pass.

**If the build fails** with errors about `long` type on Windows:
- Windows uses LLP64 where `long` is 32-bit. If you see type mismatch errors, 
  change `long[::1]` to `long long[::1]` in `src/cyaccess.pyx` AND change the
  C++ extern declarations from `vector[long]` to `vector[long long]`. This would
  also require updating the C++ `.h` files to use `long long` instead of `long`.
  However, this is a pre-existing Windows issue, not a Python 3.13 regression.

---

## FILES CHANGED (Summary)

| File | Type of Change |
|------|---------------|
| `pyproject.toml` | Updated build dependency versions |
| `setup.py` | Added python_requires, updated dep minimums, updated classifiers, bumped version |
| `src/cyaccess.pyx` | Full rewrite: added import_array, migrated to typed memoryviews |
| `requirements-dev.txt` | Removed restrictive upper version pins |
| `pandana/network.py` | Removed Python 2 __future__ import |
| `pandana/__init__.py` | Bumped version to 0.7.1 |
| `examples/simple_example.py` | Removed Python 2 __future__ import |
| `examples/shortest_path_example.py` | Removed Python 2 __future__ import |
