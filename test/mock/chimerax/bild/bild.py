import numpy


def get_cylinder(radius, p0, p1, closed=True, xform=None, pure=False):
    vertices = numpy.array([[0., 0., 0.], [1., 1., 1.], [2., 2., 2.]])
    triangles = numpy.array([[0, 1, 2]])
    normals = numpy.array([[1., 0., 0.]])
    return vertices, normals, triangles
