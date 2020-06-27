#cython: language_level=3
#
# This file is part of the Printrun suite.
#
# Printrun is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Printrun is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Printrun.  If not, see <http://www.gnu.org/licenses/>.

from libc.stdlib cimport malloc, free
from libc.stdint cimport uint8_t, uint32_t
from libc.string cimport strlen, strncpy

cdef char* copy_string(object value):
    value = value.encode('utf-8')
    cdef char* orig = value
    str_len = len(orig)
    cdef char* array = <char *>malloc(str_len + 1)
    strncpy(array, orig, str_len)
    array[str_len] = 0;
    return array

cdef enum BitPos:
    pos_raw =               1 << 0
    pos_command =           1 << 1
    pos_is_move =           1 << 2
    pos_x =                 1 << 3
    pos_y =                 1 << 4
    pos_z =                 1 << 5
    pos_e =                 1 << 6
    pos_f =                 1 << 7
    pos_i =                 1 << 8
    pos_j =                 1 << 9
    pos_relative =          1 << 10
    pos_relative_e =        1 << 11
    pos_extruding =         1 << 12
    pos_current_x =         1 << 13
    pos_current_y =         1 << 14
    pos_current_z =         1 << 15
    pos_current_tool =      1 << 16
    pos_gcview_end_vertex = 1 << 17
    # WARNING: don't use bits 24 to 31 as we store current_tool there

cdef inline uint32_t has_var(uint32_t status, uint32_t pos):
    return status & pos

cdef inline uint32_t set_has_var(uint32_t status, uint32_t pos):
    return status | pos

cdef inline uint32_t unset_has_var(uint32_t status, uint32_t pos):
    return status & ~pos

cdef class GLine:
    
    cdef char* _raw
    cdef char* _command
    cdef float _x, _y, _z, _e, _f, _i, _j
    cdef float _current_x, _current_y, _current_z
    cdef uint32_t _gcview_end_vertex
    cdef uint32_t _status

    __slots__ = ()

    def __cinit__(self):
        self._status = 0
        self._raw = NULL
        self._command = NULL

    def __init__(self, line):
        self.raw = line

    def __dealloc__(self):
        if self._raw != NULL: free(self._raw)
        if self._command != NULL: free(self._command)

    property x:
        def __get__(self):
            if has_var(self._status, pos_x): return self._x
            else: return None
        def __set__(self, value):
            self._x = value
            self._status = set_has_var(self._status, pos_x)
    property y:
        def __get__(self):
            if has_var(self._status, pos_y): return self._y
            else: return None
        def __set__(self, value):
            self._y = value
            self._status = set_has_var(self._status, pos_y)
    property z:
        def __get__(self):
            if has_var(self._status, pos_z): return self._z
            else: return None
        def __set__(self, value):
            self._z = value
            self._status = set_has_var(self._status, pos_z)
    property e:
        def __get__(self):
            if has_var(self._status, pos_e): return self._e
            else: return None
        def __set__(self, value):
            self._e = value
            self._status = set_has_var(self._status, pos_e)
    property f:
        def __get__(self):
            if has_var(self._status, pos_f): return self._f
            else: return None
        def __set__(self, value):
            self._f = value
            self._status = set_has_var(self._status, pos_f)
    property i:
        def __get__(self):
            if has_var(self._status, pos_i): return self._i
            else: return None
        def __set__(self, value):
            self._i = value
            self._status = set_has_var(self._status, pos_i)
    property j:
        def __get__(self):
            if has_var(self._status, pos_j): return self._j
            else: return None
        def __set__(self, value):
            self._j = value
            self._status = set_has_var(self._status, pos_j)
    property is_move:
        def __get__(self):
            if has_var(self._status, pos_is_move): return True
            else: return False
        def __set__(self, value):
            if value: self._status = set_has_var(self._status, pos_is_move)
            else: self._status = unset_has_var(self._status, pos_is_move)
    property relative:
        def __get__(self):
            if has_var(self._status, pos_relative): return True
            else: return False
        def __set__(self, value):
            if value: self._status = set_has_var(self._status, pos_relative)
            else: self._status = unset_has_var(self._status, pos_relative)
    property relative_e:
        def __get__(self):
            if has_var(self._status, pos_relative_e): return True
            else: return False
        def __set__(self, value):
            if value: self._status = set_has_var(self._status, pos_relative_e)
            else: self._status = unset_has_var(self._status, pos_relative_e)
    property extruding:
        def __get__(self):
            if has_var(self._status, pos_extruding): return True
            else: return False
        def __set__(self, value):
            if value: self._status = set_has_var(self._status, pos_extruding)
            else: self._status = unset_has_var(self._status, pos_extruding)
    property current_x:
        def __get__(self):
            if has_var(self._status, pos_current_x): return self._current_x
            else: return None
        def __set__(self, value):
            self._current_x = value
            self._status = set_has_var(self._status, pos_current_x)
    property current_y:
        def __get__(self):
            if has_var(self._status, pos_current_y): return self._current_y
            else: return None
        def __set__(self, value):
            self._current_y = value
            self._status = set_has_var(self._status, pos_current_y)
    property current_z:
        def __get__(self):
            if has_var(self._status, pos_current_z): return self._current_z
            else: return None
        def __set__(self, value):
            self._current_z = value
            self._status = set_has_var(self._status, pos_current_z)
    property current_tool:
        def __get__(self):
            if has_var(self._status, pos_current_tool): return self._status >> 24
            else: return None
        def __set__(self, value):
            self._status = (self._status & ((1 << 24) - 1)) | (value << 24)
            self._status = set_has_var(self._status, pos_current_tool)
    property gcview_end_vertex:
        def __get__(self):
            if has_var(self._status, pos_gcview_end_vertex): return self._gcview_end_vertex
            else: return None
        def __set__(self, value):
            self._gcview_end_vertex = value
            self._status = set_has_var(self._status, pos_gcview_end_vertex)
    property raw:
        def __get__(self):
            if has_var(self._status, pos_raw): return self._raw.decode('utf-8')
            else: return None
        def __set__(self, value):
            # WARNING: memory leak could happen here, as we don't do the following :
            # if self._raw != NULL: free(self._raw)
            self._raw = copy_string(value)
            self._status = set_has_var(self._status, pos_raw)
    property command:
        def __get__(self):
            if has_var(self._status, pos_command): return self._command.decode('utf-8')
            else: return None
        def __set__(self, value):
            # WARNING: memory leak could happen here, as we don't do the following :
            # if self._command != NULL: free(self._command)
            self._command = copy_string(value)
            self._status = set_has_var(self._status, pos_command)

cdef class GLightLine:

    cdef char* _raw
    cdef char* _command
    cdef uint8_t _status

    __slots__ = ()

    def __cinit__(self):
        self._status = 0
        self._raw = NULL
        self._command = NULL

    def __init__(self, line):
        self.raw = line

    def __dealloc__(self):
        if self._raw != NULL: free(self._raw)
        if self._command != NULL: free(self._command)

    property raw:
        def __get__(self):
            if has_var(self._status, pos_raw): return self._raw.decode('utf-8')
            else: return None
        def __set__(self, value):
            # WARNING: memory leak could happen here, as we don't do the following :
            # if self._raw != NULL: free(self._raw)
            self._raw = copy_string(value)
            self._status = set_has_var(self._status, pos_raw)
    property command:
        def __get__(self):
            if has_var(self._status, pos_command): return self._command.decode('utf-8')
            else: return None
        def __set__(self, value):
            # WARNING: memory leak could happen here, as we don't do the following :
            # if self._command != NULL: free(self._command)
            self._command = copy_string(value)
            self._status = set_has_var(self._status, pos_command)
    property is_move:
        def __get__(self):
            if has_var(self._status, pos_is_move): return True
            else: return False
        def __set__(self, value):
            if value: self._status = set_has_var(self._status, pos_is_move)
            else: self._status = unset_has_var(self._status, pos_is_move)
