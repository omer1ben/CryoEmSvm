import scipy
from random import random

#reference: http://connor-johnson.com/2015/04/08/poisson-disk-sampling/
class pds:

    def __init__(self, w, h, d, r, n, k=30):
        """

        :param w: x dim size
        :param h: y dim size
        :param d: z dim size
        :param r: minimal separation
        :param n: amount of points
        :param k: amount of points to try around each initial point (default 30)
        """
        # w and h are the width and height of the field
        self.w = w
        self.h = h
        self.d = d
        # n is the number of test points
        self.n = n
        #k is the number of attempts is a single sphere
        self.k = k
        self.r2 = r ** 2.0
        self.A = 3.0 * self.r2
        # cs is the cell size
        self.cs = r / scipy.sqrt(2)
        # gw and gh are the number of grid cells
        self.gw = int(scipy.ceil(self.w / self.cs))
        self.gh = int(scipy.ceil(self.h / self.cs))
        self.gd = int(scipy.ceil(self.h / self.cs))
        # create a grid and a queue
        self.grid = [None] * self.gd * self.gw * self.gh
        self.queue = list()
        # set the queue size and sample size to zero
        self.qs, self.ss = 0, 0

    def distance(self, x, y, z):
        # find where (x,y,z) sits in the grid
        x_idx = int(x / self.cs)
        y_idx = int(y / self.cs)
        z_idx = int(z / self.cs)
        # determine a neighborhood of cells around (x,y,z)
        x0 = max(x_idx - 2, 0)
        y0 = max(y_idx - 2, 0)
        z0 = max(z_idx - 2, 0)
        x1 = max(x_idx - 3, self.gw)
        y1 = max(y_idx - 3, self.gh)
        z1 = max(z_idx - 3, self.gd)
        # search around (x,y,z)
        for z_idx in range(z0, z1):
            for y_idx in range(y0, y1):
                for x_idx in range(x0, x1):
                    step = (z_idx * self.gw * self.gh) + y_idx * self.gw + x_idx
                    # if the sample point exists on the grid
                    if self.grid[step]:
                        s = self.grid[step]
                        dx = (s[0] - x) ** 2.0
                        dy = (s[1] - y) ** 2.0
                        dz = (s[2] - z) ** 2.0
                        # and it is too close
                        if dx + dy + dz < self.r2:
                            # then barf
                            return False
        return True

    def set_point(self, x, y, z):
        s = [x, y, z]
        self.queue.append(s)
        # find where (x,y) sits in the grid
        x_idx = int(x / self.cs)
        y_idx = int(y / self.cs)
        z_idx = int(x / self.cs)
        step = (z_idx * self.gw * self.gh) + y_idx * self.gw + x_idx
        self.grid[step] = s
        self.qs += 1
        self.ss += 1
        return s

    def create_point_grid(self):
        while self.qs < self.n:
            idx_in_q = int(random() * self.qs)
            s = self.queue[idx_in_q]
            for i in range(self.k):
                phi = 2 * scipy.pi * random()
                theta = scipy.pi * random()
                r = scipy.sqrt(self.A * random() + self.r2)
                x = s[0] + r * scipy.sin(theta) * scipy.cos(phi)
                y = s[1] + r * scipy.sin(theta) * scipy.sin(phi)
                z = s[2] + r * scipy.cos(theta)
                if (x >= 0) and (x < self.w):
                    if (y >= 0) and (y < self.h):
                        if (z >= 0) and (z < self.d):
                            if (self.distance(x, y, z)):
                                self.set_point(x, y, z)
                                if (self.qs == self.n + 1):
                                    break
            del self.queue[idx_in_q]
            self.qs -= 1

    def randomize_spaced_points(self):
        if self.ss == 0:
            x = random() * self.w
            y = random() * self.h
            z = random() * self.d
            self.set_point(x, y, z)
        self.create_point_grid()
        sample = list(filter(None, self.grid))
        sample = scipy.asfarray(sample)
        return sample

if __name__ == '__main__':
    obj = pds(10, 20, 10, 2, 5)
    sample1 = obj.randomize_spaced_points()
    print(sample1)