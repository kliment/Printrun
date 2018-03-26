# Imported from python-rectangle-packer commit 32fce1aaba
# https://github.com/maxretter/python-rectangle-packer
#
# Python Rectangle Packer - Packs rectangles around a central point
# Copyright (C) 2013 Max Retter
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import math

import Polygon
import Polygon.Utils


class Vector2:
    """Simple 2d vector / point class."""

    def __init__(self, x=0, y=0):
        self.x = float(x)
        self.y = float(y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def add(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def sub(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def scale(self, factor):
        return Vector2(self.x * factor, self.y * factor)

    def magnitude(self):
        return math.sqrt(self.dot_product(self))

    def unit(self):
        """Build unit vector."""
        return self.scale(1 / self.magnitude())

    def dot_product(self, other):
        return self.x * other.x + self.y * other.y

    def distance(self, other):
        """Distance forumla for other point."""
        return math.sqrt(
            (other.x - self.x) ** 2 +
            (other.y - self.y) ** 2
        )


class Rect:
    """Simple rectangle object."""
    def __init__(self, width, height, data={}):
        self.width = width
        self.height = height
        self.data = data

        # upper left
        self.position = Vector2()

    def half(self):
        """Half width and height."""
        return Vector2(
            self.width / 2,
            self.height / 2
        )

    def expand(self, width, height):
        """Builds a new rectangle based on this one with given offsets."""
        expanded = Rect(self.width + width, self.height + height)
        expanded.set_center(self.center())

        return expanded

    def point_list(self):
        top = self.position.y
        right = self.position.x + self.width
        bottom = self.position.y + self.height
        left = self.position.x

        return PointList([
            (left, top),
            (right, top),
            (right, bottom),
            (left, bottom),
        ])

    def center(self):
        """Center of rect calculated from position and dimensions."""
        return self.position.add(self.half())

    def set_center(self, center):
        """Set the position based on a new center point."""
        self.position = center.sub(self.half())

    def area(self):
        """Area: length * width."""
        return self.width * self.height


class PointList:
    """Methods for transforming a list of points."""
    def __init__(self, points=[]):
        self.points = points
        self._polygon = None

    def polygon(self):
        """Builds a polygon from the set of points."""
        if not self._polygon:
            self._polygon = Polygon.Polygon(self.points)

        return self._polygon

    def segments(self):
        """Returns a list of LineSegment objects."""
        segs = []
        for i, point in enumerate(self.points[1:]):
            index = i + 1

            segs.append(LineSegment(
                Vector2(self.points[index - 1][0], self.points[index - 1][1]),
                Vector2(self.points[index][0], self.points[index][1])
            ))

        segs.append(LineSegment(
            Vector2(self.points[-1][0], self.points[-1][1]),
            Vector2(self.points[0][0], self.points[0][1]),
        ))

        return segs


class LineSegment:
    def __init__(self, start, end):
        self.start = start
        self.end = end

    def length(self):
        """Length of segment vector."""
        return self.end.sub(self.start).magnitude()

    def closest_point_to_point(self, point):
        """Point along segment that is closest to given point."""
        segment_vector = self.end.sub(self.start)
        point_vector = point.sub(self.start)

        seg_mag = segment_vector.magnitude()

        # project point_vector on segment_vector
        projection = segment_vector.dot_product(point_vector)

        # scalar value used to interpolate new point along segment_vector
        scalar = projection / seg_mag ** 2

        # clamp on [0,1]
        scalar = 1.0 if scalar > 1.0 else scalar
        scalar = 0.0 if scalar < 0.0 else scalar

        # interpolate scalar along segment and add start point back in
        return self.start.add(segment_vector.unit().scale(scalar * seg_mag))

    def closest_distance_to_point(self, point):
        """Helper method too automatically return distance."""
        closest_point = self.closest_point_to_point(point)
        return closest_point.distance(point)


class Packer:
    def __init__(self):
        self._rects = []

    def add_rect(self, width, height, data={}):
        self._rects.append(Rect(width, height, data))

    def pack(self, padding=0, center=Vector2()):
        # init everything
        placed_rects = []
        sorted_rects = sorted(self._rects, key=lambda rect: -rect.area())
        # double padding due to halfing later on
        padding *= 2

        for rect in sorted_rects:

            if not placed_rects:
                # first rect, right on target.
                rect.set_center(center)

            else:
                # Expand each rectangle based on new rect size and padding
                # get a list of points
                # build a polygon
                point_lists = [
                    pr.expand(rect.width + padding, rect.height + padding).point_list().polygon()
                    for pr in placed_rects
                ]

                # take the union of all the polygons (relies on + operator override)
                # the [0] at the end returns the first "contour", which is the only one we need
                bounding_points = PointList(sum(
                    point_lists[1:],
                    point_lists[0]
                )[0])

                # find the closest segment
                closest_segments = sorted(
                    bounding_points.segments(),
                    key=lambda segment: segment.closest_distance_to_point(center)
                )

                # get the closest point
                place_point = closest_segments[0].closest_point_to_point(center)

                # set the rect position
                rect.set_center(place_point)

            placed_rects.append(rect)

        return placed_rects
