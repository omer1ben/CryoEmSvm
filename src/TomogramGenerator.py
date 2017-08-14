from CommonDataTypes import *

from Constants import TOMOGRAM_DIMENSION,TOMOGRAM_DIMENSIONS,TOMOGRAM_DIMENSIONS_2D
import numpy as np
'''
TOMOGRAM_DIMENSION = 40
TOMOGRAM_DIMENSIONS = (TOMOGRAM_DIMENSION,TOMOGRAM_DIMENSION)
TOMOGRAM_DIMENSIONS_2D = (TOMOGRAM_DIMENSION,TOMOGRAM_DIMENSION,1)
'''

#def put_template(dm, template_dm, position):
#    dm[position[0] - template_dm.shape[0]//2:position[0] + template_dm.shape[0]//2,position[1] - template_dm.shape[1]//2:position[1] + template_dm.shape[1]//2] += template_dm

def put_template(tomogram_dm, template_dm, position):
    """
    3D READY
    :param tomogram_dm:  dm is density map
    :param template_dm: dm is density map
    :param position: center posistion
    :return:
    """
    corner = [position[i] - template_dm.shape[i] // 2 for i in range(len(tomogram_dm.shape))]
    shape = tuple([slice(corner[i],corner[i] + template_dm.shape[i]) for i in range(len(corner))])
    tomogram_dm[shape] += template_dm

def generate_tomogram_with_given_candidates(templates, composition, dimensions=TOMOGRAM_DIMENSIONS_2D):
    """
    3D READY!
    :param templates: list of lists: first dimension is different template_ids second dimension is tilt_id
    :param composition: list of candidates to put in the tomogram
    :param dimensions: the dimensions of the Tomogram- tuple of sizes e.g. (100,100) for 2D, or (100,100,100) for 3D
    :return: Tomogram object
    """
    tomogram_dm = np.zeros(dimensions)
    for candidate in composition:
        put_template(tomogram_dm, templates[candidate.label][candidate.six_position.tilt_id].density_map, candidate.six_position.COM_position)
    return Tomogram(tomogram_dm, tuple(composition))


def randomize_spaced_out_points(tomogram_dim, separation, n_points):
    """
    randomize n points in the space defined by a square of side tomogram_dim spaced so that no two points are closer than separation
    :param tomogram_dim: side length. currently assuming tomogram is square
    :param separation: minimal separation between any two points
    :param n_points: amount of points to randomize
    :return: list of random positions
    """
    import poisson_disk
    obj = poisson_disk.pds(tomogram_dim, tomogram_dim, tomogram_dim, separation, n_points)
    return obj.randomize_spaced_points()


def generate_random_tomogram(templates, criteria):
    """
    :param templates:  list of lists: first dimension is different template_ids second dimension is tilt_id
    :param criteria: list of integers. criteria[i] means how many instances of template_id==i should appear in the resulting tomogram
    :return:
    """
    n = sum(criteria)
    separation = templates[0][0].dm.shape[0] * (3**0.5)
    points = randomize_spaced_out_points(TOMOGRAM_DIMENSION, separation, n)
    ids = [[i]*criteria[i] for i in len(criteria)]
    import itertools
    flat_ids = list(itertools.chain.from_iterable(ids))
    import random
    shuffle = random.shuffle(flat_ids)
    return [Candidate(SixPosition(pos_id[0],EulerAngle.rand_tilt_id()), label=pos_id[1] ) for pos_id in zip(points,shuffle)]


if __name__ == '__main__':

    from TemplateGenerator import generate_tilted_templates
    from FeaturesExtractor import FeaturesExtractor
    import matplotlib.pyplot as plt

    templates = generate_tilted_templates()

    criteria = (Candidate.fromTuple(1, 0, 10, 10), Candidate.fromTuple(1, 2, 27, 18), Candidate.fromTuple(0, 0, 10, 28))
    tomogram = generate_tomogram_with_given_candidates(templates, criteria)

    import CandidateSelector
    import Labeler

    selector = CandidateSelector.CandidateSelector(templates)
    candidates = selector.select(tomogram)
    labeler = Labeler.PositionLabeler(tomogram.composition)
    features_extractor = FeaturesExtractor(templates)
    for candidate in candidates:
        labeler.label(candidate)
        candidate.set_features(features_extractor.extract_features(tomogram, candidate))


    #print(len(candidates))
    for candidate in candidates:
        print(candidate)

    fig, ax = plt.subplots()
    ax.imshow(tomogram.density_map[:,:,0])

    fig, ax = plt.subplots()
    candidate_positions = np.zeros(tomogram.density_map[:,:,0].shape)
    for candidate in candidates:
        pos = candidate.six_position.COM_position
        if candidate.label == 1:
            col = 0.9
        elif candidate.label == 2:
            col = 0.6
        else:
            col = 0.3
        candidate_positions[pos[0]][pos[1]] = col
    ax.imshow(candidate_positions)

    plt.show()

