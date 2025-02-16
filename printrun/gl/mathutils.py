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

import math
import numpy as np
from numpy.linalg import inv

# for type hints
from typing import List
from ctypes import Array, c_int, c_double

def cross(v1: List[float], v2: List[float]) -> List[float]:
    return [v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0]]

def trackball(p1x: float, p1y: float, p2x: float, p2y: float, r: float) -> List[float]:
    TRACKBALLSIZE = r

    if p1x == p2x and p1y == p2y:
        return [0.0, 0.0, 0.0, 1.0]

    p1 = [p1x, p1y, project_to_sphere(TRACKBALLSIZE, p1x, p1y)]
    p2 = [p2x, p2y, project_to_sphere(TRACKBALLSIZE, p2x, p2y)]
    a = cross(p2, p1)

    d = map(lambda x, y: x - y, p1, p2)
    t = math.sqrt(sum(x * x for x in d)) / (2.0 * TRACKBALLSIZE)

    t = min(t, 1.0)
    t = max(t, -1.0)
    phi = 2.0 * math.asin(t)

    return axis_to_quat(a, phi)

def axis_to_quat(a: List[float], phi: float) -> List[float]:
    lena = math.sqrt(sum(x * x for x in a))
    q = [x * (1 / lena) for x in a]
    q = [x * math.sin(phi / 2.0) for x in q]
    q.append(math.cos(phi / 2.0))
    return q

def build_rotmatrix(q: List[float]) -> np.ndarray:
    m = np.zeros((16, 1)) # (GLdouble * 16)()
    m[0] = 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
    m[1] = 2.0 * (q[0] * q[1] - q[2] * q[3])
    m[2] = 2.0 * (q[2] * q[0] + q[1] * q[3])
    m[3] = 0.0

    m[4] = 2.0 * (q[0] * q[1] + q[2] * q[3])
    m[5] = 1.0 - 2.0 * (q[2] * q[2] + q[0] * q[0])
    m[6] = 2.0 * (q[1] * q[2] - q[0] * q[3])
    m[7] = 0.0

    m[8] = 2.0 * (q[2] * q[0] - q[1] * q[3])
    m[9] = 2.0 * (q[1] * q[2] + q[0] * q[3])
    m[10] = 1.0 - 2.0 * (q[1] * q[1] + q[0] * q[0])
    m[11] = 0.0

    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0
    return m.reshape((4, 4))

def project_to_sphere(r: float, x: float, y: float) -> float:
    d = math.sqrt(x * x + y * y)
    if d < r * 0.70710678118654752440:
        return math.sqrt(r * r - d * d)

    t = r / 1.41421356237309504880
    return t * t / d

def mulquat(q1: List[float], rq: List[float]) -> List[float]:
    return [q1[3] * rq[0] + q1[0] * rq[3] + q1[1] * rq[2] - q1[2] * rq[1],
            q1[3] * rq[1] + q1[1] * rq[3] + q1[2] * rq[0] - q1[0] * rq[2],
            q1[3] * rq[2] + q1[2] * rq[3] + q1[0] * rq[1] - q1[1] * rq[0],
            q1[3] * rq[3] - q1[0] * rq[0] - q1[1] * rq[1] - q1[2] * rq[2]]

def quat_rotate_vec(quat: List[float],
                    vector_list: list[np.ndarray]) -> list[np.ndarray]:
    rmat = build_rotmatrix(quat)
    vecs_out = []
    for vec in vector_list:
        vec_in = np.append(vec, 0.0)
        vecs_out.append(np.matmul(vec_in, rmat)[:3])

    return vecs_out

def mat4_translation(x_val: float, y_val: float,
                     z_val: float) -> np.ndarray:
    """
    Returns a 4x4 translation matrix
    """

    matrix = np.identity(4)
    matrix[3][0] = x_val
    matrix[3][1] = y_val
    matrix[3][2] = z_val

    return matrix

def mat4_rotation(x: float, y: float,
                  z: float, angle_deg: float) -> np.ndarray:
    """
    Returns a 4x4 rotation matrix, enter rotation angle in degree
    """

    matrix = np.identity(4)
    co = np.cos(np.radians(angle_deg))
    si = np.sin(np.radians(angle_deg))
    matrix[0][0] = x * x * (1 - co) + co
    matrix[1][0] = x * y * (1 - co) - z * si
    matrix[2][0] = x * z * (1 - co) + y * si
    matrix[0][1] = x * y * (1 - co) + z * si
    matrix[1][1] = y * y * (1 - co) + co
    matrix[2][1] = y * z * (1 - co) - x * si
    matrix[0][2] = x * z * (1 - co) - y * si
    matrix[1][2] = y * z * (1 - co) + x * si
    matrix[2][2] = z * z * (1 - co) + co

    return matrix

def mat4_scaling(x_val: float, y_val: float, z_val: float) -> np.ndarray:
    """
    Returns a 4x4 scaling matrix
    """

    matrix = np.identity(4)
    matrix[0][0] = x_val
    matrix[1][1] = y_val
    matrix[2][2] = z_val

    return matrix

def pyg_to_gl_mat4(pyg_matrix) -> Array:
    """
    Converts a pyglet Mat4() matrix into a c_types_Array which
    can be directly passed into OpenGL calls.
    """
    array_type = c_double * 16
    return array_type(*pyg_matrix.column(0),
                      *pyg_matrix.column(1),
                      *pyg_matrix.column(2),
                      *pyg_matrix.column(3))

def np_to_gl_mat(np_matrix: np.ndarray) -> Array:
    """
    Converts a numpy matrix into a c_types_Array which
    can be directly passed into OpenGL calls.
    """
    array_type = c_double * np_matrix.size
    return array_type(*np_matrix.reshape((np_matrix.size, 1)))

def np_unproject(winx: float, winy: float, winz: float,
                 mv_mat: Array[c_double], p_mat: Array[c_double],
                 viewport: Array[c_int], pointx: c_double,
                 pointy: c_double, pointz: c_double) -> bool:
    '''
    gluUnProject in Python with numpy. This is a direct
    implementation of the Khronos OpenGL Wiki code:
    https://www.khronos.org/opengl/wiki/GluProject_and_gluUnProject_code

    Parameters:
        winx, winy, winz: Window coordinates.
        mv_mat: Model-view matrix as a ctypes array.
        p_mat: Projection matrix as a ctypes array.
        viewport: Viewport as a ctypes array [x, y, width, height].
        pointx, pointy, pointz: Output variables for object coordinates.

    Returns:
        bool: True if successful, False otherwise.
    '''
    modelview_mat = np.asarray(mv_mat).reshape((4, 4))
    projection_mat = np.asarray(p_mat).reshape((4, 4))

    mat_a = projection_mat.T @ modelview_mat.T

    try:
        mat_inv = inv(mat_a)
    except np.linalg.LinAlgError:
        return False

    # Normalized screen coordinates between -1 and 1
    coords_in = np.zeros(4)
    coords_in[0] = (winx - float(viewport[0])) / float(viewport[2]) * 2.0 - 1.0
    coords_in[1] = (winy - float(viewport[1])) / float(viewport[3]) * 2.0 - 1.0
    coords_in[2] = 2.0 * winz - 1.0
    coords_in[3] = 1.0

    # Object coordinates
    coords_out = mat_inv @ coords_in
    if coords_out[3] == 0.0:
        return False

    coords_out[3] = 1.0 / coords_out[3]
    pointx.value = coords_out[0] * coords_out[3]
    pointy.value = coords_out[1] * coords_out[3]
    pointz.value = coords_out[2] * coords_out[3]
    return True

