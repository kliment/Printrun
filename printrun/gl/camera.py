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

from threading import Lock

from pyglet.gl import GLdouble, glGetDoublev, glLoadIdentity, \
    glMatrixMode, GL_MODELVIEW, GL_MODELVIEW_MATRIX, glOrtho, \
    GL_PROJECTION, glTranslatef, gluPerspective, \
    glPushMatrix, glPopMatrix, glLoadMatrixd

from .trackball import trackball, mulquat, axis_to_quat, \
                       build_rotmatrix, mat4_translation, \
                       mat4_scaling

import numpy as np

# for type hints
from typing import Optional, List, Tuple, TYPE_CHECKING
from wx import MouseEvent
from ctypes import Array
Build_Dims = Tuple[int, int, int, int, int, int]
if TYPE_CHECKING:
    from .panel import wxGLPanel


class Camera():

    rot_lock = Lock()

    def __init__(self, parent: 'wxGLPanel', build_dimensions: Build_Dims, ortho: bool = True) -> None:

        self.canvas = parent
        self.is_orthographic = ortho
        self.orbit_control = True

        self.scalefactor = 1.0
        self.width = 1.0
        self.height = 1.0
        self.dist = max(build_dimensions[:2])

        self.view_matrix_initialized = False

        self.basequat = [0.0, 0.0, 0.0, 1.0]
        self.zoomed_width = 1.0
        self.zoomed_height = 1.0
        self.angle_z = 0
        self.angle_x = 0
        self.initpos = None
        self.init_trans_pos = None

        self.init_scale = (1.0, 1.0, 1.0)
        self.transl_mat = np.identity(4)
        self.scale_mat = np.identity(4)

        self.platformcenter = (-build_dimensions[3] - build_dimensions[0] / 2,
                               -build_dimensions[4] - build_dimensions[1] / 2)

    def update_size(self, width: int, height: int, scalefactor: float) -> None:
        self.width = width
        self.height = height
        self.scalefactor = scalefactor

    def update_build_dims(self, build_dimensions: Build_Dims) -> None:
        self.dist = max(build_dimensions[:2])
        self.platformcenter = (-build_dimensions[3] - build_dimensions[0] / 2,
                               -build_dimensions[4] - build_dimensions[1] / 2)

    def create_projection_matrix(self) -> None:
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        if self.is_orthographic:
            glOrtho(-self.width / 2, self.width / 2,
                    -self.height / 2, self.height / 2,
                    -25 * self.dist, 25 * self.dist)
        else:
            gluPerspective(45.0, self.width / self.height, 0.1, 20 * self.dist)
            # FIXME: Something here is wrong with the perspective.
            glTranslatef(0, 0, -self.dist)  # Move back

        glMatrixMode(GL_MODELVIEW)

    def create_pseudo2d_matrix(self) -> None:
        '''Create untransformed matrices to render
        coordinates directly on the canvas, quasi 2D.
        Use always in conjunction with revert_...'''

        glPushMatrix()  # backup and clear MODELVIEW
        glLoadIdentity()

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()  # backup and clear PROJECTION
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)

    def revert_pseudo2d_matrix(self) -> None:
        '''Revert current matrices back to the normal,
        saved matrices'''

        glPopMatrix()  # restore PROJECTION

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()  # restore MODELVIEW

    def reset_view_matrix(self, factor: float) -> None:
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        self.transl_mat = np.identity(4)
        self.scale_mat = np.identity(4)

        wratio = self.width / self.dist
        hratio = self.height / self.dist
        minratio = float(min(wratio, hratio))
        self.zoomed_width = wratio / minratio
        self.zoomed_height = hratio / minratio

        self.init_scale = (factor * minratio, factor * minratio, factor * minratio)

        self.view_matrix_initialized = True

    def reset_rotation(self) -> None:
        self.basequat = [0.0, 0.0, 0.0, 1.0]
        self.angle_x = 0.0
        self.angle_z = 0.0

    def get_view_matrix(self, local_transform: bool) -> Array:
        mvmat = (GLdouble * 16)()
        if local_transform:
            glPushMatrix()
            self.update()
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)
            glPopMatrix()
        else:
            glGetDoublev(GL_MODELVIEW_MATRIX, mvmat)

        return mvmat

    def update(self) -> None:
        glMatrixMode(GL_MODELVIEW)
        transl_mat = mat4_translation(self.platformcenter[0],
                                      self.platformcenter[1],
                                      matrix = self.transl_mat.copy())

        view_mat = np.matmul(transl_mat, build_rotmatrix(self.basequat))

        scale_mat = mat4_scaling(self.init_scale[0], self.init_scale[0],
                                 self.init_scale[0],self.scale_mat.copy())

        view_mat = np.matmul(view_mat, scale_mat).reshape((16, 1))

        array_type = GLdouble * len(view_mat)
        view_mat_gl = array_type(*view_mat)
        glLoadMatrixd(view_mat_gl)

    def zoom(self, factor: float, to: Optional[Tuple[float, float]] = None) -> None:
        # TODO: Implement zoom to point
        '''
        delta_x = 0.0
        delta_y = 0.0

        if to:
            delta_x = to[0]
            delta_y = to[1]
            glTranslatef(delta_x, delta_y, 0)
        '''

        mat4_scaling(factor, factor, factor,
                     self.scale_mat)
        '''
        if to:
            glTranslatef(-delta_x, -delta_y, 0)
        '''

    def orbit(self, p1x: float, p1y: float, p2x: float, p2y: float) -> List[float]:
        rz = p2x - p1x
        self.angle_z -= rz
        rot_z = axis_to_quat([0.0, 0.0, 1.0], self.angle_z)

        rx = p2y - p1y
        self.angle_x += rx
        rot_a = axis_to_quat([1.0, 0.0, 0.0], self.angle_x)

        return mulquat(rot_z, rot_a)

    def handle_rotation(self, event: MouseEvent) -> None:
        if self.initpos is None:
            self.initpos = event.GetPosition() * self.scalefactor
        else:
            p1 = self.initpos
            p2 = event.GetPosition() * self.scalefactor
            sz = (self.width, self.height)
            p1x = p1[0] / (sz[0] / 2) - 1
            p1y = 1 - p1[1] / (sz[1] / 2)
            p2x = p2[0] / (sz[0] / 2) - 1
            p2y = 1 - p2[1] / (sz[1] / 2)

            with self.rot_lock:
                if self.orbit_control:
                    self.basequat = self.orbit(p1x, p1y, p2x, p2y)
                else:
                    quat = trackball(p1x, p1y, p2x, p2y, self.dist / 250.0)
                    self.basequat = mulquat(self.basequat, quat)
            self.initpos = p2

    def handle_translation(self, event: MouseEvent) -> None:
        if self.init_trans_pos is None:
            self.init_trans_pos = event.GetPosition() * self.scalefactor
        else:
            p1 = self.init_trans_pos
            p2 = event.GetPosition() * self.scalefactor

            x1, y1, z1 = self.canvas.mouse_to_3d(p1[0], p1[1])
            x2, y2, z2 = self.canvas.mouse_to_3d(p2[0], p2[1])

            mat4_translation(x2 - x1, y2 - y1, z2 - z1, self.transl_mat)

            self.init_trans_pos = p2

