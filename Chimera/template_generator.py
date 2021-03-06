import chimera
from VolumeViewer import open_volume_file, volume_from_grid_data
from VolumeData import Array_Grid_Data
from Matrix import euler_xform
import numpy as np
import sys, pickle, argparse



def create_pdb_model(pdb_name, resolution):
    """
    Creates chimera model object from pdb file
    Centers model at center of frame (for future rotations)
    Model object is numbered #1
    
    :param pdb_name: path to pdb file
    :param resolution: sampeling resolution
    """
    
    # create model from pdb file
    chan = chimera.openModels.open(pdb_name)[0]
    chimera.runCommand('molmap #0 %s modelId 1' % str(resolution))
    model = chimera.specifier.evalSpec('#1').models()[0]
    chan.destroy()

    # center (for later rotations)
    trans = tuple(np.array(model.openState.cofr.data()) * -1)
    model.openState.globalXform(euler_xform([0,0,0],trans))
    
    return model

def create_cube_matrix(side):
    """
    Creates cube density map matrix - a cube of size side^3
    centered in an empty matirx of size (2*side)^3

    :param side: number of pixels in cube edge
    """
    
    matrix = np.zeros((side*2,side*2,side*2))
    matrix[side//2:side//2+side,side//2:side//2+side,side//2:side//2+side] = np.ones((side,side,side))
    return matrix


def create_sphere_matrix(rad):
    """
    Creates sphere density map matrix - a sphere of radius rad
    centered in an empty matirx of size (2*rad)^3

    :param rad: sphere radius in number of pixels
    """
    
    matrix = np.zeros((2*rad,2*rad,2*rad))
    for x in range(2*rad):
        for y in range(2*rad):
            for z in range(2*rad):
                if (x-rad)**2 + (y-rad)**2 + (z-rad)**2 <= rad**2:
                    matrix[x,y,z] = 1
    return matrix

def create_geometric_model(shape_name, var):
    """
    Creates chimera model object from a geometric shape
    Centers model at center of frame (for future rotations)
    Model object is numbered #1
    
    :param shpae_name: one of known shapes - cube, sphere
    :param var: geomteric shpae paramter (cube side, sphere radius)
    """
    
    if shape_name == 'cube':
        matrix = create_cube_matrix(var)
    elif shape_name == 'sphere':
        matrix = create_sphere_matrix(var)
    else:
        raise('unkown shape!')

    # create model
    v = volume_from_grid_data(Array_Grid_Data(matrix))
    tmp_model = chimera.specifier.evalSpec('#0').models()[0]
    trans = tuple(np.array(tmp_model.openState.cofr.data()) * -1)
    tmp_model.openState.globalXform(euler_xform([0,0,0],trans))

    # change model number to #1 for consitency
    model = tmp_model.copy()
    tmp_model.close()
    return model


def create_model(model_type, model_str, model_var):
    if model_type == 'G':
        return create_geometric_model(model_str, model_var)
    elif model_type == 'P':
        return create_pdb_model(model_str, model_var)
    else:
        raise('unkown model type!')


def calc_com(matrix):
    """
    Calcultates the center of mass of a density map

    :param matrix: density map matrix
    """
    return np.round([np.dot(np.array(range(matrix.shape[i])),np.sum(np.sum(matrix,max((i+1)%3,(i+2)%3)),min((i+1)%3,(i+2)%3))) for i in range(3)] / sum(sum(sum(matrix))))

def calc_dim(matrix):
    """
    Calcultates the size of a box that can contain all non zero cells of
    the density map rotated at any angle arround the center of mass

    :param matrix: density map matrix
    """

    # calc radius around center of mass
    rad = 0
    com = calc_com(matrix)
    for x in range(matrix.shape[0]):
        for y in range(matrix.shape[1]):
            for z in range(matrix.shape[2]):
                if matrix[x,y,z] > 0:
                    rad = max(rad, np.sqrt(sum((np.array([x,y,z])-com)**2)))

    # get box dimensions (and add some spares)
    return int(np.ceil(2 * rad * 1.1))



def generate_tilts(angle_res):
    """
    Creates set of all possible euler_angle tilts according to resolution

    :param angle_res: resolution of tilts (for each euler angle)
    """
    
    tilts = []
    for phi in range(0,360,angle_res):
        tilts.append((phi,0,0))
        for theta in range(angle_res, 180, angle_res):
            for psi in range(0, 360, angle_res):
                tilts.append((phi,theta, psi))
        tilts.append((phi,180,0))
        
    return tilts


def create_tilted_model(model, euler_angles):
    """
    Creates tilted model based on original model and euler angles
    Resamples the density map after tilting

    :param model: orignal model to be tilted
    :param euler_angles: 3-tuple of euler angles
    """
    
    # copy
    tmp_model = model.copy()

    # rotate
    rot = euler_xform(euler_angles, [0,0,0])
    tmp_model.openState.globalXform(rot)

    # resample
    chimera.runCommand('vop #0 resample onGrid #1')
    tilted_model = chimera.specifier.evalSpec('#2').models()[0]
    tmp_model.close()
    
    return tilted_model
    

def get_matrix_and_center(matrix, dim):
    """
    Get model density map and place inside a box with side
    of size dim, centered around center of mass

    :param matrix: density map matrix
    :param dim: box side
    """

    # expand matrix
    big_matrix = np.zeros(tuple((2*dim*np.ones((1,3)) + matrix.shape)[0]))
    shape = tuple([slice(dim,dim + matrix.shape[i]) for i in range(3)])
    big_matrix[shape] += matrix

    # center and truncate
    com = [int(x) for x in calc_com(big_matrix)]
    shape = tuple([slice(com[i]-dim//2, com[i]-dim//2+dim) for i in range(3)])
    truncated_matrix = big_matrix[shape]

    return truncated_matrix


def tilt_and_save(model, euler_angles, dim, output_name):
    """
    Creates and saves a density map of the model tilted according
    to the supplied euler angles

    :param model: orignal model to be tilted
    :param euler_angles: 3-tuple of euler angles
    :param dim: density map box side
    :param output_name: name of density map file
    """
    
    tilted = create_tilted_model(model, euler_angles)
    matrix = get_matrix_and_center(tilted.matrix(), dim)
    print(euler_angles, calc_com(matrix))
    tilted.close()
    np.save(output_name, matrix)


def flow(criteria, angle_res, output_path):
    """
    Creates desnsity map of given models at all possible tilts according
    to given angle resolution and saves to file

    :param criteria: list of tempalte types in the following format:
                     (template_type, template_str, template_var) where
                     - template_type = G: geometric / P: pdb
                     - template_str = shape name / pdb file path
                     - template_var = parameter for model generation (resolution/ radius...)
    :param angle_res: tilt "grid" resolution
    :param output_path: diretory where output is saved
    """
    
    # get dim
    print('a')
    dim = 0
    for criterion in criteria:
        model = create_model(*criterion)
        dim = max(dim,calc_dim(model.matrix()))
        model.close()
    print('b')

    # create tilted density maps
    tilts = generate_tilts(angle_res)
    for template_id, criterion in enumerate(criteria):
        model = create_model(*criterion) # create model
        for tilt_id, tilt in enumerate(tilts): # iterate on tilts
            output_name = output_path + str(template_id) + '_' + str(tilt_id)
            tilt_and_save(model, tilt, dim, output_name)
        model.close() # close model
    print('c')
    # create meta data
    template_ids = dict([(template_id, criterion) for template_id, criterion in enumerate(criteria)])
    tilt_ids = dict([(tilt_id, tilt) for tilt_id, tilt in enumerate(tilts)])
    pickle.dump(template_ids, open(output_path + 'template_ids.p', 'wb'))
    pickle.dump(tilt_ids, open(output_path + 'tilt_ids.p', 'wb'))
    print('d')


def parse_config(template_type, config_path):
    with open(config_path) as f:
        #return [(template_type, line.split(':')[0], [int(val) for val in line.split(':')[1].split(',')]) for line in f.readlines()]
        return [(template_type, line.split(':')[0], int(line.split(':')[1])) for line in f.readlines()]

def main(argv):
    # parse arguments
    parser = argparse.ArgumentParser(description = '')
    parser.add_argument('-o', '--output_path', required=True, nargs=1, type=str, help='output dir')
    parser.add_argument('-a', '--angle_res', required=True, nargs=1, type=int, help='angle resolution')
    parser.add_argument('-g', '--geometric_config_path', nargs=1, type=str, help='output dir')
    parser.add_argument('-p', '--pdb_config_path', nargs=1, type=str, help='output dir')
    args = parser.parse_args(argv)  

    # set sdtout and stderr
    #stdpath = r'C:\Users\Matan\PycharmProjects\Workshop\Chimera\Templates\\'
    sys.stdout = open(args.output_path[0] + 'output.txt', 'w')
    sys.stderr = open(args.output_path[0] + 'error.txt', 'w')
    print('Start!')

    # get criteria
    criteria = []
    if args.geometric_config_path:
        criteria += parse_config('G', args.geometric_config_path[0])
    if args.pdb_config_path:
        criteria += parse_config('P', args.pdb_config_path[0])
    

    print(criteria)
    print(args.output_path[0])
    print(args.angle_res[0])

    # run
    flow(criteria, args.angle_res[0], args.output_path[0])
    print('Done!')
    

if __name__ == '__main__':
    main(sys.argv[1:])
    # output_path = r'C:\Users\Matan\PycharmProjects\Workshop\Chimera\Templates\\'
    # sys.stdout = open(output_path + 'output.txt', 'w')
    # sys.stderr = open(output_path + 'error.txt', 'w')
    # pdb_name = r'C:\Users\Matan\Dropbox\Study\S-3B\Workshop\Tutotrial\1k4c.pdb'
    # criteria = [('P',pdb_name,10),('G','cube',10),('G','sphere',10)]
    # 
    # flow(criteria, 30, output_path)
    
