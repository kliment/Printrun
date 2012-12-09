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

import sys, struct, math

def cross(v1, v2):
    return [v1[1]*v2[2]-v1[2]*v2[1], v1[2]*v2[0]-v1[0]*v2[2], v1[0]*v2[1]-v1[1]*v2[0]]

def genfacet(v):
    veca = [v[1][0]-v[0][0], v[1][1]-v[0][1], v[1][2]-v[0][2]]
    vecb = [v[2][0]-v[1][0], v[2][1]-v[1][1], v[2][2]-v[1][2]]
    vecx = cross(veca, vecb)
    vlen = math.sqrt(sum(map(lambda x:x*x, vecx)))
    if vlen == 0:
        vlen = 1
    normal = map(lambda x:x/vlen, vecx)
    return [normal, v]

I = [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, 1]
]

def transpose(matrix):
    return zip(*matrix)
    #return [[v[i] for v in matrix] for i in xrange(len(matrix[0]))]

def multmatrix(vector, matrix):
    return map(sum, transpose(map(lambda x:[x[0]*p for p in x[1]], zip(vector, transpose(matrix)))))

def applymatrix(facet, matrix = I):
    #return facet
    #return [map(lambda x:-1.0*x, multmatrix(facet[0]+[1], matrix)[:3]), map(lambda x:multmatrix(x+[1], matrix)[:3], facet[1])]
    return genfacet(map(lambda x:multmatrix(x+[1], matrix)[:3], facet[1]))

f = [[0, 0, 0],[[-3.022642, 0.642482, -9.510565],[-3.022642, 0.642482, -9.510565],[-3.022642, 0.642482, -9.510565]]]
m = [
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1]
]

def emitstl(filename, facets = [], objname = "stltool_export", binary = 1):
    if filename is None:
        return
    if binary:
        f = open(filename, "wb")
        buf = "".join(["\0"]*80)
        buf+=struct.pack("<I", len(facets))
        facetformat = struct.Struct("<ffffffffffffH")
        for i in facets:
            l = list(i[0][:])
            for j in i[1]:
                l+=j[:]
            l+=[0]
            #print len(l)
            buf+=facetformat.pack(*l)
        f.write(buf)
        f.close()
        return


    f = open(filename, "w")
    f.write("solid "+objname+"\n")
    for i in facets:
        f.write("  facet normal "+" ".join(map(str, i[0]))+"\n   outer loop\n")
        for j in i[1]:
            f.write("    vertex "+" ".join(map(str, j))+"\n")
        f.write("   endloop"+"\n")
        f.write("  endfacet"+"\n")
    f.write("endsolid "+objname+"\n")
    f.close()



class stl:
    def __init__(self, filename = None):
        self.facet = [[0, 0, 0],[[0, 0, 0],[0, 0, 0],[0, 0, 0]]]
        self.facets = []
        self.facetsminz = []
        self.facetsmaxz = []

        self.name = ""
        self.insolid = 0
        self.infacet = 0
        self.inloop = 0
        self.facetloc = 0
        if filename is None:
            return
        self.f = list(open(filename))
        if not self.f[0].startswith("solid"):
            print "Not an ascii stl solid - attempting to parse as binary"
            f = open(filename, "rb")
            buf = f.read(84)
            while(len(buf)<84):
                newdata = f.read(84-len(buf))
                if not len(newdata):
                    break
                buf+=newdata
            facetcount = struct.unpack_from("<I", buf, 80)
            facetformat = struct.Struct("<ffffffffffffH")
            for i in xrange(facetcount[0]):
                buf = f.read(50)
                while(len(buf)<50):
                    newdata = f.read(50-len(buf))
                    if not len(newdata):
                        break
                    buf+=newdata
                fd = list(facetformat.unpack(buf))
                self.name = "binary soloid"
                self.facet = [fd[:3],[fd[3:6], fd[6:9], fd[9:12]]]
                self.facets+=[self.facet]
                facet = self.facet
                self.facetsminz+=[(min(map(lambda x:x[2], facet[1])), facet)]
                self.facetsmaxz+=[(max(map(lambda x:x[2], facet[1])), facet)]
            f.close()
            return
        for i in self.f:
            if not self.parseline(i):
                return

    def translate(self, v = [0, 0, 0]):
        matrix = [
        [1, 0, 0, v[0]],
        [0, 1, 0, v[1]],
        [0, 0, 1, v[2]],
        [0, 0, 0, 1]
        ]
        return self.transform(matrix)

    def rotate(self, v = [0, 0, 0]):
        import math
        z = v[2]
        matrix1 = [
        [math.cos(math.radians(z)),-math.sin(math.radians(z)), 0, 0],
        [math.sin(math.radians(z)), math.cos(math.radians(z)), 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1]
        ]
        y = v[0]
        matrix2 = [
        [1, 0, 0, 0],
        [0, math.cos(math.radians(y)),-math.sin(math.radians(y)), 0],
        [0, math.sin(math.radians(y)), math.cos(math.radians(y)), 0],
        [0, 0, 0, 1]
        ]
        x = v[1]
        matrix3 = [
        [math.cos(math.radians(x)), 0,-math.sin(math.radians(x)), 0],
        [0, 1, 0, 0],
        [math.sin(math.radians(x)), 0, math.cos(math.radians(x)), 0],
        [0, 0, 0, 1]
        ]
        return self.transform(matrix1).transform(matrix2).transform(matrix3)

    def scale(self, v = [0, 0, 0]):
        matrix = [
        [v[0], 0, 0, 0],
        [0, v[1], 0, 0],
        [0, 0, v[2], 0],
        [0, 0, 0, 1]
        ]
        return self.transform(matrix)


    def transform(self, m = I):
        s = stl()
        s.facets = [applymatrix(i, m) for i in self.facets]
        s.insolid = 0
        s.infacet = 0
        s.inloop = 0
        s.facetloc = 0
        s.name = self.name
        for facet in s.facets:
            s.facetsminz+=[(min(map(lambda x:x[2], facet[1])), facet)]
            s.facetsmaxz+=[(max(map(lambda x:x[2], facet[1])), facet)]
        return s

    def export(self, f = sys.stdout):
        f.write("solid "+self.name+"\n")
        for i in self.facets:
            f.write("  facet normal "+" ".join(map(str, i[0]))+"\n")
            f.write("   outer loop"+"\n")
            for j in i[1]:
                f.write("    vertex "+" ".join(map(str, j))+"\n")
            f.write("   endloop"+"\n")
            f.write("  endfacet"+"\n")
        f.write("endsolid "+self.name+"\n")
        f.flush()

    def parseline(self, l):
        l = l.strip()
        if l.startswith("solid"):
            self.insolid = 1
            self.name = l[6:]
            #print self.name

        elif l.startswith("endsolid"):
            self.insolid = 0
            return 0
        elif l.startswith("facet normal"):
            l = l.replace(", ",".")
            self.infacet = 11
            self.facetloc = 0
            self.facet = [[0, 0, 0],[[0, 0, 0],[0, 0, 0],[0, 0, 0]]]
            self.facet[0]=map(float, l.split()[2:])
        elif l.startswith("endfacet"):
            self.infacet = 0
            self.facets+=[self.facet]
            facet = self.facet
            self.facetsminz+=[(min(map(lambda x:x[2], facet[1])), facet)]
            self.facetsmaxz+=[(max(map(lambda x:x[2], facet[1])), facet)]
        elif l.startswith("vertex"):
            l = l.replace(", ",".")
            self.facet[1][self.facetloc]=map(float, l.split()[1:])
            self.facetloc+=1
        return 1
if __name__ == "__main__":
    s = stl("../../Downloads/frame-vertex-neo-foot-x4.stl")
    for i in xrange(11, 11):
        working = s.facets[:]
        for j in reversed(sorted(s.facetsminz)):
            if(j[0]>i):
                working.remove(j[1])
            else:
                break
        for j in (sorted(s.facetsmaxz)):
            if(j[0]<i):
                working.remove(j[1])
            else:
                break

        print i, len(working)
    emitstl("../../Downloads/frame-vertex-neo-foot-x4-a.stl", s.facets, "emitted_object")
#stl("../prusamendel/stl/mendelplate.stl")
