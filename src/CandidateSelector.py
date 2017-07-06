CORRELATION_THRESHOLD = 50
GAUSSIAN_MEAN = 30
GAUSSIAN_STDEV = 3

from CommonDataTypes import *
from scipy import signal
import numpy as np
import PeakDetection

class CandidateSelector:
    def __init__(self, templates):
        self.templates = templates
        self.kernel = np.outer(signal.gaussian(GAUSSIAN_MEAN, GAUSSIAN_STDEV), signal.gaussian(GAUSSIAN_MEAN, GAUSSIAN_STDEV))

    def find_local_maxima(self, correlation_array):
        blurred_correlation_array = signal.fftconvolve(correlation_array[:,:,0], self.kernel, mode='same')
        res = np.nonzero(PeakDetection.detect_peaks(blurred_correlation_array)) #### 2D
        return [(x[0],x[1],0) for x in zip(res[0],res[1]) if blurred_correlation_array[x] > CORRELATION_THRESHOLD]

    def select(self, tomogram):
        max_correlation_per_3loc = np.empty(tomogram.density_map.shape)
        for template_tuple in self.templates:
            for tilted in template_tuple:
                #max_correlation_per_3loc is an array representing the maximum on all correlations generated by all the templates and tilts for each 3-position
                max_correlation_per_3loc = np.maximum(max_correlation_per_3loc, signal.fftconvolve(tomogram.density_map, tilted.density_map, mode='same'))

        positions = self.find_local_maxima(max_correlation_per_3loc)

        return [Candidate(SixPosition(position, None), None) for position in positions]



if __name__ == '__main__':

    from TemplateGenerator import generate_tilted_templates
    from TomogramGenerator import generate_tomogram
    import matplotlib.pyplot as plt

    templates = generate_tilted_templates()
    tomogram = generate_tomogram(templates, None)

    fig, ax = plt.subplots()
    ax.imshow(tomogram.density_map)

    correlation = signal.fftconvolve(tomogram.density_map, templates[1][2].density_map, mode='same')

    fig, ax = plt.subplots()
    ax.imshow(correlation)

    positions = CandidateSelector.find_local_maxima(None, correlation)
    maximums = np.zeros(correlation.shape)
    for position in positions:
        maximums[position] = correlation[position]
    fig, ax = plt.subplots()
    print(len(positions))
    ax.imshow(maximums)

    #plt.show()
