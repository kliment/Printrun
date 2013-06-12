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

cdef char* copy_string(object value):
    cdef char* orig = value
    str_len = len(orig)
    cdef char* array = <char *>malloc(str_len + 1)
    strncpy(array, orig, str_len)
    array[str_len] = 0;
    return array

cdef class GLine(object):
    
    cdef float _x, _y, _z, _e, _f, _i, _j, _s, _p
    cdef bool _is_move, _relative, _relative_e, _extruding
    cdef float _current_x, _current_y, _current_z
    cdef char _current_tool
    cdef long _gcview_end_vertex
    cdef char* _raw
    cdef char* _command
    cdef object _split_raw
    
    cdef bool has_x, has_y, has_z, has_e, has_f, has_i, has_j, has_s, has_p
    cdef bool has_is_move, has_relative, has_relative_e, has_extruding
    cdef bool has_current_x, has_current_y, has_current_z
    cdef bool has_current_tool
    cdef bool has_gcview_end_vertex
    cdef bool has_raw
    cdef bool has_command
    cdef bool has_split_raw

    __slots__ = ()

    def __cinit__(self):
        self._raw = NULL
        self._command = NULL

    def __dealloc__(self):
        if self._raw != NULL: free(self._raw)
        if self._command != NULL: free(self._command)

    property x:
        def __get__(self):
            if self.has_x: return self._x
            else: return None
        def __set__(self, value):
            self._x = value
            self.has_x = True
    property y:
        def __get__(self):
            if self.has_y: return self._y
            else: return None
        def __set__(self, value):
            self._y = value
            self.has_y = True
    property z:
        def __get__(self):
            if self.has_z: return self._z
            else: return None
        def __set__(self, value):
            self._z = value
            self.has_z = True
    property e:
        def __get__(self):
            if self.has_e: return self._e
            else: return None
        def __set__(self, value):
            self._e = value
            self.has_e = True
    property f:
        def __get__(self):
            if self.has_f: return self._f
            else: return None
        def __set__(self, value):
            self._f = value
            self.has_f = True
    property i:
        def __get__(self):
            if self.has_i: return self._i
            else: return None
        def __set__(self, value):
            self._i = value
            self.has_i = True
    property j:
        def __get__(self):
            if self.has_j: return self._j
            else: return None
        def __set__(self, value):
            self._j = value
            self.has_j = True
    property s:
        def __get__(self):
            if self.has_s: return self._s
            else: return None
        def __set__(self, value):
            self._s = value
            self.has_s = True
    property p:
        def __get__(self):
            if self.has_p: return self._p
            else: return None
        def __set__(self, value):
            self._p = value
            self.has_p = True
    property is_move:
        def __get__(self):
            if self.has_is_move: return self._is_move
            else: return None
        def __set__(self, value):
            self._is_move = value
            self.has_is_move = True
    property relative:
        def __get__(self):
            if self.has_relative: return self._relative
            else: return None
        def __set__(self, value):
            self._relative = value
            self.has_relative = True
    property relative_e:
        def __get__(self):
            if self.has_relative_e: return self._relative_e
            else: return None
        def __set__(self, value):
            self._relative_e = value
            self.has_relative_e = True
    property extruding:
        def __get__(self):
            if self.has_extruding: return self._extruding
            else: return None
        def __set__(self, value):
            self._extruding = value
            self.has_extruding = True
    property current_x:
        def __get__(self):
            if self.has_current_x: return self._current_x
            else: return None
        def __set__(self, value):
            self._current_x = value
            self.has_current_x = True
    property current_y:
        def __get__(self):
            if self.has_current_y: return self._current_y
            else: return None
        def __set__(self, value):
            self._current_y = value
            self.has_current_y = True
    property current_z:
        def __get__(self):
            if self.has_current_z: return self._current_z
            else: return None
        def __set__(self, value):
            self._current_z = value
            self.has_current_z = True
    property current_tool:
        def __get__(self):
            if self.has_current_tool: return self._current_tool
            else: return None
        def __set__(self, value):
            self._current_tool = value
            self.has_current_tool = True
    property gcview_end_vertex:
        def __get__(self):
            if self.has_gcview_end_vertex: return self._gcview_end_vertex
            else: return None
        def __set__(self, value):
            self._gcview_end_vertex = value
            self.has_gcview_end_vertex = True
    property split_raw:
        def __get__(self):
            if self.has_split_raw: return self._split_raw
            else: return None
        def __set__(self, value):
            self._split_raw = value
            self.has_split_raw = True
        def __del__(self):
            self._split_raw = None
    property raw:
        def __get__(self):
            if self.has_raw: return self._raw
            else: return None
        def __set__(self, value):
            self._raw = copy_string(value)
            self.has_raw = True
    property command:
        def __get__(self):
            if self.has_command: return self._command
            else: return None
        def __set__(self, value):
            self._command = copy_string(value)
            self.has_command = True
