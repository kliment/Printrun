# distutils: language = c++
# This file is copied from GCoder.
#
# GCoder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GCoder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

from libcpp cimport bool
from libc.stdlib cimport malloc, free

cdef extern from "string.h":
       char *strncpy(char *dest, char *src, size_t n)
       size_t strlen(const char *s)

cdef class GLine(object):
    
    cdef public float _x, _y, _z, _e, _f, _i, _j, _s, _p
    cdef public bool _is_move, _relative, _relative_e, _extruding
    cdef public float _current_x, _current_y, _current_z
    cdef public int _current_tool
    cdef public long _gcview_end_vertex
    cdef char* _raw
    cdef char* _command
    cdef public object _split_raw
    
    cdef public bool has_x, has_y, has_z, has_e, has_f, has_i, has_j, has_s, has_p
    cdef public bool has_is_move, has_relative, has_relative_e, has_extruding
    cdef public bool has_current_x, has_current_y, has_current_z
    cdef public bool has_current_tool
    cdef public bool has_gcview_end_vertex
    cdef public bool has_raw
    cdef public bool has_command
    cdef public bool has_split_raw

    __slots__ = ()

    def __cinit__(self):
        self._raw = NULL
        self._command = NULL

    def __dealloc__(self):
        if self._raw: free(self._raw)
        if self._command: free(self._command)

    def __getattr__(self, name):
        if getattr(self, "has_" + name):
            if name == "raw":
                return self._raw
            elif name == "command":
                return self._command
            return getattr(self, "_" + name)
        else:
            return None

    def setstring(self, name, value):
        cdef char* orig = value
        str_len = len(orig)
        cdef char* array = <char *>malloc(str_len + 1)
        strncpy(array, orig, str_len);
        array[str_len] = 0;
        if name == "raw":
            self._raw = array
        elif name == "command":
            self._command = array
        setattr(self, "has_" + name, True)

    def set(self, name, value):
        setattr(self, "_" + name, value)
        setattr(self, "has_" + name, True)
