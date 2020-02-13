import blossom5.pyMatch as pm
import decorators

"""
:param size:
:param plot_load:

 We define the unit cell, which contains two qubits, a star operator and plaquette operator.

    |       |
- Star  -  Q_0 -     also top (T) qubit
    |       |
-  Q_1  - Plaq  -    also down (D) qubit
    |       |

By doing so, we can define arrays the star and plaquette operators, where their index value define their position
  on the qubit lattice. For the qubit array, there is an extra dimension to store the two qubits per unit cell.

self.array stores the qubit values and has dimension [XZ_error{0,1}, Top_down{0,1}, size, size]
Qubit values are either 0 or 1, which is analogous to the -1, and 1 state, respectively
"""

class toric(metaclass=decorators.FuncCallCounter):
    def __init__(self, *args, **kwargs):

        for key, value in kwargs.items():
            setattr(self, key, value)


    def decode(self):
        self.get_matching()
        self.apply_matching()

        if self.graph.gl_plot: self.graph.gl_plot.plot_lines(self.matching)


    def get_stabs(self):
        verts, decode_verts, plaqs, decode_plaqs = [], [], [], []
        for layer in self.graph.S.values():
            for stab in layer.values():
                if stab.state:
                    if stab.sID[0] == 0:
                        verts.append(stab)
                        decode_verts.append(self.graph.S[self.graph.decode_layer][stab.sID])
                    else:
                        plaqs.append(stab)
                        decode_plaqs.append(self.graph.S[self.graph.decode_layer][stab.sID])
        return verts, plaqs, decode_verts, decode_plaqs


    def get_edges(self, anyons):
        edges = []
        for i0, v0 in enumerate(anyons[:-1]):
            (y0, x0), z0 = v0.sID[1:], v0.z
            for i1, v1 in enumerate(anyons[i0 + 1 :]):
                (y1, x1), z1 = v1.sID[1:], v1.z
                wy = (y0 - y1) % (self.graph.size)
                wx = (x0 - x1) % (self.graph.size)
                wz = abs(z0 - z1)
                weight = min([wy, self.graph.size - wy]) + min([wx, self.graph.size - wx]) + wz
                edges.append([i0, i1 + i0 + 1, weight])

        return edges


    def get_matching(self):
        """
        Uses the BlossomV algorithm to get the matchings. A list of combinations of all the anyons and their respective weights are feeded to the blossom5 algorithm. To apply the matchings, we walk from each matching vertex to where their paths meet perpendicualarly, flipping the edges on the way over.
        """
        verts, plaqs, d_verts, d_plaqs = self.get_stabs()

        def get_matching(anyons, d_anyons):
            output = pm.getMatching(len(anyons), self.get_edges(anyons))
            return [[d_anyons[i0], d_anyons[i1], anyons[i0], anyons[i1]] for i0, i1 in enumerate(output) if i0 > i1]

        self.matching = []
        if verts:
            self.matching += get_matching(verts, d_verts)
        if plaqs:
            self.matching += get_matching(plaqs, d_plaqs)


    def get_distances(self, V0, V1):
        (y0, x0) = V0.sID[1:]
        (y1, x1) = V1.sID[1:]

        dy0 = (y0 - y1) % self.graph.size
        dx0 = (x0 - x1) % self.graph.size
        dy1 = (y1 - y0) % self.graph.size
        dx1 = (x1 - x0) % self.graph.size

        dy, yd = (dy0, "n") if dy0 < dy1 else (dy1, "s")
        dx, xd = (dx0, "e") if dx0 < dx1 else (dx1, "w")

        return dy, yd, dx, xd


    def apply_matching(self):

        for v0, v1, m0, m1 in self.matching:  # Apply the matchings to the graph

            # Get distance between endpoints, take modulo to find min distance
            dy, yd, dx, xd = self.get_distances(v0, v1)
            xv = self.walk_and_flip(v0, m0, dy, yd)
            self.walk_and_flip(v1, m1, dx, xd)

            # Only for keeping track of matching edges
            self.walk_z_matchings(m0, m1, xv)


    def walk_and_flip(self, flipnode, matchnode, length, dir):
        '''
        adds this edge to the matching
        '''
        for _ in range(length):
            (flipnode, flipedge)    = flipnode.neighbors[dir]
            (matchnode, matchedge)  = matchnode.neighbors[dir]
            flipedge.state      = 1 - flipedge.state
            matchedge.matching  = 1 - matchedge.matching
        return flipnode

    def walk_z_matchings(self, m0, m1, xv):
        '''
        apply mathings in z direction
        '''
        dz = m0.z - m1.z
        zd = "u" if dz < 0 else "d"
        for _ in range(dz):
            (xv, edge) = xv.neighbors[zd]
            edge.matching = 1 - edge.matching


class planar(toric):

    def decode(self):
        self.get_matching()
        self.remove_virtual()
        self.apply_matching()
        if self.graph.gl_plot: self.graph.gl_plot.plot_lines(self.matching)


    def get_stabs(self):
        verts, plaqs, tv, tp = [], [], [], []
        dvert, dplaq, dv, dp = [], [], [], []
        for layer in self.graph.S.values():
            for stab in layer.values():
                (type, y, x) = stab.sID
                if stab.state:
                    if type == 0:
                        verts.append(stab)
                        dvert.append(self.graph.S[self.graph.decode_layer][(type, y, x)])

                        if x < self.graph.size/2:
                            tv.append(self.graph.B[stab.z][(type, y, 0)])
                            dv.append(self.graph.B[self.graph.decode_layer][(type, y, 0)])
                        else:
                            tv.append(self.graph.B[stab.z][(type, y, self.graph.size)])
                            dv.append(self.graph.B[self.graph.decode_layer][(type, y, self.graph.size)])
                    else:
                        plaqs.append(stab)
                        dplaq.append(self.graph.S[self.graph.decode_layer][(type, y, x)])
                        if y < self.graph.size/2:
                            tp.append(self.graph.B[stab.z][(type, -1, x)])
                            dp.append(self.graph.B[self.graph.decode_layer][(type, -1, x)])
                        else:
                            tp.append(self.graph.B[stab.z][(type, self.graph.size - 1, x)])
                            dp.append(self.graph.B[self.graph.decode_layer][(type, self.graph.size - 1, x)])
        verts += tv
        plaqs += tp
        dvert += dv
        dplaq += dp
        return verts, plaqs, dvert, dplaq


    def get_edges(self, anyons):

        edges = []
        mid = len(anyons)//2
        for i0, v0 in enumerate(anyons[:mid-1]):
            (y0, x0), z0 = v0.sID[1:], v0.z
            for i1, v1 in enumerate(anyons[i0 + 1 :mid]):
                (y1, x1), z1 = v1.sID[1:], v1.z
                wy = abs(y0 - y1)
                wx = abs(x0 - x1)
                wz = abs(z0 - z1)
                weight = wy + wx + wz
                edges.append([i0, i1 + i0 + 1, weight])


        for i0, v0 in enumerate(anyons[mid:-1], start=mid):
            for i1, v1 in enumerate(anyons[i0 + 1:], start=i0 + 1):
                edges.append([i0, i1, 0])


        for i in range(mid):
            (type, ys, xs) = anyons[i].sID
            (type, yb, xb) = anyons[mid + i].sID
            weight = abs(xb - xs) if type == 0 else abs(yb - ys)
            edges.append([i, mid + i, weight])

        return edges


    def get_distances(self, V0, V1):

        y0, x0 = V0.sID[1:]
        y1, x1 = V1.sID[1:]
        dy = y0 - y1
        dx = x0 - x1

        yd = "n" if dy > 0 else "s"
        xd = "w" if dx < 0 else "e"

        return abs(dy), yd, abs(dx), xd


    def remove_virtual(self):
        matching = []
        for V1, V2, V3, V4, in self.matching:
            if not (V1.type == 1 and V2.type == 1):
                matching.append([V1, V2, V3, V4])
        self.matching = matching
