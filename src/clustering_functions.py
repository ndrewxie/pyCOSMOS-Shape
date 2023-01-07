import numpy as np
from pylab import *
# for 3d plotting
import plotly.graph_objs as go
import plotly.express as px
import plotly.io as pio
pio.renderers.default ="browser"
import pandas as pd
from sklearn.cluster import *
from math import sqrt
from numpy import floor, ceil
import config

def plot_histogram(arr, nbins):
    """
    Plots a histogram given the numpy array arr

    :param arr: numpy array
    :param nbins: Number of bins
    :return: Nothing. Generates a figure PSD.jpg
    """
    figure()
    # The min and max (range) of the histogram are the nearest integers given by floor or ceil
    range = (floor(arr.min()), ceil(arr.max()))
    hist(arr, density =True, bins = nbins, range = range, color ='orange', edgecolor='black', linewidth=1)
    xlabel('Diameter ($\AA$)')
    ylabel('Normalized Distribution')
    xlim(0,)
    ylim(0,)
    savefig('PSD.jpg', format='jpg',dpi=300 ,bbox_inches='tight')
    close()

def xyz_to_abc(x, y, z):
    """
    Converts the x, y, z coordinate in the orthogonal basis into a, b, c which are coordinates in the non-orthogonal
    space of the unit cell

    :param x:
    :param y:
    :param z:
    :return:
    """

    a = x - np.cos(config.gamma)/(np.sin(config.gamma))*y + \
        config.Lx * config.Ly * config.Lz *(np.cos(config.alpha)* np.cos(config.gamma)-np.cos(config.beta))/(config.Volume_of_uc*np.sin(config.gamma))*z
    b = 0   + 1/(np.sin(config.gamma))*y + \
        config.Lx * config.Ly * config.Lz *(np.cos(config.beta)* np.cos(config.gamma)-np.cos(config.alpha))/(config.Volume_of_uc*np.sin(config.gamma))*z
    c = 0   +  0 + config.Lx * config.Ly * config.Lz *np.sin(config.gamma)/config.Volume_of_uc * z

    return a, b, c

def abc_to_xyz(a, b, c):
    """


    :param a:
    :param b:
    :param c:
    :return:
    """

    x = a + b*np.cos(config.gamma) + c*np.cos(config.beta)
    y = 0   + b*np.sin(config.gamma) + c*(np.cos(config.alpha) -
                    np.cos(config.beta)* np.cos(config.gamma))/np.sin(config.gamma)
    z = 0  +  0 + config.Volume_of_uc/(config.Lx*config.Ly*config.Lz*np.sin(config.gamma))*c

    return x, y, z

def read_vpsdpts(INPUT):
    """
    Reads the vpsdpts file generated by Zeo++
    
    Parameters
    ------------------------
    INPUT: string
    filename with vpsdpts extension
    
    Returns
    ------------------------
    x: numpy array
    y: numpy array
    z: numpy array
    diameter: numpy array
    """
    x, y, z, diameter = [], [], [], []
    linenumber = 0

    with open(INPUT) as inp:
        for line in inp:
            linenumber += 1
            if linenumber > 2:
                s = line.split()
                if int(s[0]) == 1: # only considering node sphere, disregarding ghost cell sphere
                    x.append(float(s[1]))
                    y.append(float(s[2]))
                    z.append(float(s[3]))
                    diameter.append(2*float(s[4]))

    # Convert lists into numpy arrays
    x = np.array(x)
    y = np.array(y)
    z = np.array(z)
    diameter = np.array(diameter)

    a, b, c = xyz_to_abc(x, y, z)

    return a, b, c, diameter

def make_histogram(diameter_arr, nbins):
    """
    Divide the array into n bins.
    Makes a histogram from an array and number of bins

    Parameters
    ------------------------
    diameter_arr: numpy array
    nbins: integer

    Returns
    ------------------------
    bin_freq: numpy array
    bin_edges: numpy array
    bin_index: numpy array of len = Number of geometric points
        Tells in which bin does each of the point goes
    """
    # The min and max (range) of the histogram are the nearest integers given by floor or ceil
    range = (floor(diameter_arr.min()), ceil(diameter_arr.max()))
    bin_freq, bin_edges =  np.histogram(diameter_arr, bins =nbins, range = range) # Length nbins + 1
    #bin_freq, bin_edges =  np.histogram(diameter_arr, bins =nbins, range = (0, np.ceil(diameter_arr.max()))) # Length nbins + 1

    bin_index = np.zeros(len(diameter_arr))
    for i, di in enumerate(diameter_arr):
        for j, _ in enumerate(bin_edges):
            if di > bin_edges[j] and di <= bin_edges[j+1]:
                bin_index[i] = j

    return bin_freq, bin_edges, bin_index


def periodic_distance(v1, v2):
    """
    Calculated distance between two vectors v1 and v2.
    
    Parameters
    ------------------------
    v1: numpy array
    v2: numpy array
    
    Returns
    ------------------------
    distance: double 
    """
    da = v1[0] - v2[0]
    db = v1[1] - v2[1]
    dc = v1[2] - v2[2]
    
    if abs(da) > config.Lx/2:
        da = config.Lx - abs(da)
    
    if abs(db) > config.Ly/2:
        db = config.Ly - abs(db)
        
    if abs(dc) > config.Lz/2:
        dc = config.Lz - abs(dc)
    
    #squared_distance = da**2 + db**2 + dc**2

    squared_distance = da**2 + db**2 + dc**2 + 2*da*db*np.cos(config.gamma)\
                       + 2*db*dc*np.cos(config.alpha) + 2*dc*da*np.cos(config.beta)
    
    return sqrt(squared_distance)

def update_pore_type_matrix(xk, yk, zk, cluster_labels):
    """
    pore_type_label = can be range(Npores) = 0 or 1
    Assigns the pore_type_labels array into a 3d matrix grid

    :param x_arr:
    :param y_arr:
    :param z_arr:
    :param pore_type_labels:
    :return:
    """
    xgrid, ygrid, zgrid = [], [], []
    pore_type_labels = []
    for i, li in enumerate(cluster_labels):
        if li != -1:  # if not noise
            pore_type_labels.append(config.pore_type_count)
            xgrid.append(xk[i])
            ygrid.append(yk[i])
            zgrid.append(zk[i])

    for i, li in enumerate(pore_type_labels):
        xi, yi, zi = int(floor(xgrid[i])), int(floor(ygrid[i])), int(floor(zgrid[i]))
        config.pore_type_matrix_with_pore_type_labels[xi, yi, zi] = li

def fill_pore_type_matrix():
    """
    based on only the cluster centers and cluster sizes
    does not require information of other bins

    Execute when all primary bins are identified

    Fills out all the elements of the pore type matrix to be either 0, 1, 2 - corresponding to one pore type
    :return:
    """
    print('Updating pore type matrix')
    print('-------------------------')

    all_cluster_pore_type_labels_flatten = [j for sub in config.all_cluster_pore_type_labels for j in sub]
    all_cluster_center_list_flatten = [j for sub in config.all_cluster_center_list for j in sub]
    all_cluster_diameter_list_flatten = [j for sub in config.all_cluster_diameter_list for j in sub]
    all_cluster_shape_list_flatten = [j for sub in config.all_cluster_shape_list for j in sub]
    all_cluster_orientation_list_flatten = [j for sub in config.all_cluster_orientation_list for j in sub]

    # Print pore centers, diameter and pore type to a file
    with open('pore_centers.txt', 'w') as out:
        out.write('Box %1.3f %1.3f %1.3f %1.3f %1.3f %1.3f \n' %(config.Lx, config.Ly, config.Lz, config.alpha_degree
                ,config.beta_degree, config.gamma_degree))
        out.write("xc \t yc \t zc \t diameter \t pore_type \n" )
        for i, center_cord in enumerate(all_cluster_center_list_flatten):
            ac, bc, cc = center_cord
            xc, yc, zc = abc_to_xyz(ac, bc, cc)
            out.write("%1.3f %1.3f %1.3f %1.3f %d \n"%(xc, yc, zc, all_cluster_diameter_list_flatten[i],
                                                       all_cluster_pore_type_labels_flatten[i]))


    # 3d grid in the unit cell
    a = np.arange(0.5, (int(ceil(config.Lx))) + 0.5)
    b = np.arange(0.5, (int(ceil(config.Ly))) + 0.5)
    c = np.arange(0.5, (int(ceil(config.Lz))) + 0.5)

    for i, ai in enumerate(a):
        for j, bi in enumerate(b):
            for k, ci in enumerate(c):

                # proceed only if the pore type matrix has -1
                # This is done to make sure the grid points calculated using the largest and
                # second largest bins, and third largest bins do not get overwritten
                #if config.pore_type_matrix_with_pore_type_labels[i, j, k] != -1: continue


                # calculate distance of the point to each of the cluster surface
                distance_from_cluster_surface = []
                for cc, cluster_center in enumerate(all_cluster_center_list_flatten):
                    # distance from cluster surface.
                    # if distance is negative, the point is inside the cluster

                    if all_cluster_shape_list_flatten[cc] == 'sphere':
                        distance_from_cluster_surface.append(periodic_distance(np.array([ai, bi, ci]), cluster_center)
                                                         - 0.5 * all_cluster_diameter_list_flatten[cc])

                    if all_cluster_shape_list_flatten[cc] == 'channel':
                        # THis distance is not periodic
                        # Find the point on the line which is perpendicular to the grid point
                        vec = np.array([ai, bi, ci])-cluster_center
                        vec_xyz = abc_to_xyz(vec[0], vec[1], vec[2])

                        ox, oy, oz = all_cluster_orientation_list_flatten[cc]
                        orient_xyz = abc_to_xyz(ox, oy, oz)
                        dist = np.linalg.norm(np.cross(np.array(vec_xyz), np.array(orient_xyz)))
                        distance_from_cluster_surface.append(dist - 0.5 * all_cluster_diameter_list_flatten[cc])

                    #distance_from_cluster_surface.append(distance(np.array([ai, bi, ci]), cluster_center))
                # index of the distance_from_cluster_center list where the distance is minimum
                distance_from_cluster_surface = np.array(distance_from_cluster_surface)
                index_min = np.argmin(distance_from_cluster_surface)

                config.pore_type_matrix_with_pore_type_labels[i][j][k] = all_cluster_pore_type_labels_flatten[index_min]
                config.pore_type_matrix_with_cluster_labels[i][j][k] = index_min




def show_pore_type_matrix():
    """
    plot x, y, z coordinates in 3d
    Assumed grid of 1A width in all directions
    Also saves the pore type matrix in a csv file
    :return:
    """
    a = arange(0.5, (int(ceil(config.Lx))) + 0.5)
    b = arange(0.5, (int(ceil(config.Ly))) + 0.5)
    c = arange(0.5, (int(ceil(config.Lz))) + 0.5)

    xx, yy, zz, pore_type_label_1d = [], [], [], []

    cluster_center_label_1d = []
    for i, ia in enumerate(a):
        for j, jb in enumerate(b):
            for k, kc in enumerate(c):
                ix, jy, kz = abc_to_xyz(ia, jb, kc)

                xx.append(ix)
                yy.append(jy)
                zz.append(kz)
                pore_type_label_1d.append(config.pore_type_matrix_with_pore_type_labels[i][j][k])
                cluster_center_label_1d.append(config.pore_type_matrix_with_cluster_labels[i][j][k])

    d = {'x':xx, 'y':yy, 'z':zz, 'color':pore_type_label_1d}
    df = pd.DataFrame(data = d)
    df.to_csv(config.File_pore_type_matrix, index =False)

    df["color"] = df["color"].astype(str)
    fig = px.scatter_3d(df, x = 'x', y = 'y', z='z', color = 'color',)
    fig.update_traces(marker=dict(size=6,
                                  line=dict(width=0.5,
                                            color='Black')),
                      selector=dict(mode='markers'),
                      marker_symbol = 'square')

    fig.write_html("pore_type_matrix_with_pore_type_labels.html")
    fig.show()

    d = {'x':xx, 'y':yy, 'z':zz, 'color':cluster_center_label_1d}
    df = pd.DataFrame(data = d)
    df.to_csv('pore_type_matrix_with_cluster_center_label.csv', index =False)

    df["color"] = df["color"].astype(str)
    fig = px.scatter_3d(df, x = 'x', y = 'y', z='z', color = 'color',)
    fig.update_traces(marker=dict(size=6,
                                  line=dict(width=0.5,
                                            color='Black')),
                      selector=dict(mode='markers'),
                      marker_symbol = 'square')

    fig.write_html("pore_type_matrix_with_cluster_center_labels.html")
    fig.show()
def dbscan(ak, bk, ck, periodic_distance_matrix, eps, min_samples):
    """
    DBSCAN to cluster points
    """
    sol = DBSCAN(eps = eps, min_samples = min_samples,metric = "precomputed", n_jobs =8).fit(periodic_distance_matrix)
    labels = sol.labels_ # can be -1, 0, 1, 2 ..., Ncluster-1

    # calculate cluster centers
    #cluster_center_list, cluster_diameter_list = best_cluster_center(ak, bk, ck, labels)
    cluster_center_list = best_cluster_center(ak, bk, ck, labels)

    #return labels, cluster_center_list, cluster_diameter_list
    return labels, cluster_center_list

def best_cluster_center(ak, bk, ck, labels):
    """

    Calculates the center of the cluster

    x_arr, y_arr, z_arr: numpy array of data points
    :param ak:
    :param bk:
    :param ck:
    :param labels:
    labels: numpy array of length x_arr. Element of this array can be 0, 1, 2 ...
    :return:
    """

    cluster_center_list = []
    cluster_diameter_list = []

    # Number of clusters identified within this bin,
    # Ncluster does not accuont for -1 labels which corresponds to the noise
    Ncluster = max(np.unique(labels))+1

    if Ncluster == 0: # if only one cluster
        if labels[0] == -1:
            print('All data points classified as noise')
            # return empty list
            return (cluster_center_list, cluster_diameter_list)

    # Initialize the center of each cluster
    # x_center = [x_cluster_0, x_cluster_1 ....]
    a_center = np.zeros(Ncluster)
    b_center = np.zeros(Ncluster)
    c_center = np.zeros(Ncluster)

    # Center = mean over all the points with same labels
    for li in range(Ncluster):
        mask = labels == li # all points with the same labels
        a_center[li] = np.mean(ak[mask])
        b_center[li] = np.mean(bk[mask])
        c_center[li] = np.mean(ck[mask])


    """
    # To calculate actual center of the cluster
    For each cluster:
        For each mirror image of center:
            calculate avg_distance_from_center
    """
    # calculating the actual center of the cluster which has the minimum distance squared from all its points

    for li in range(Ncluster):
        sum_distance_from_center_list = [] # one element for each image of cluster center

        for da in [0, config.Lx/2, -config.Lx/2]:
            for db in [0, config.Ly/2, -config.Ly/2]:
                for dc in [0, config.Lz/2, -config.Lz/2]:
                    a_new_center = a_center[li] + da
                    b_new_center = b_center[li] + db
                    c_new_center = c_center[li] + dc

                    # new center should be inside the unit cell
                    a_new_center, b_new_center, c_new_center = put_point_in_box(a_new_center, b_new_center, c_new_center)
                    new_center = np.array([a_new_center, b_new_center, c_new_center])

                    # the sum of squares of the distance
                    sum_distance2_from_center = 0
                    #mask = labels == li
                    #points = np.array(ak[mask], bk[mask], ck[mask])
                    #sum_distance2_from_center = np.sum(distance(new_center, points)**2)

                    for j, lj in enumerate(labels):
                        if lj == li:
                            point = np.array([ak[j], bk[j], ck[j]])
                            sum_distance2_from_center += periodic_distance(new_center, point) ** 2

                    sum_distance_from_center_list.append(sum_distance2_from_center)

        index_min = np.argmin(sum_distance_from_center_list)
        #index_min = min(range(len(sum_distance_from_center_list)), key=sum_distance_from_center_list.__getitem__)

        #print(li, index_min)
        index = 0
        #Npoints_in_cluster = 0

        for da in [0, config.Lx/2, -config.Lx/2]:
            for db in [0, config.Ly/2, -config.Ly/2]:
                for dc in [0, config.Lz/2, -config.Lz/2]:
                    if index == index_min:
                        a_new_center = a_center[li] + da
                        b_new_center = b_center[li] + db
                        c_new_center = c_center[li] + dc

                        # new center should be inside the unit cell
                        a_new_center, b_new_center, c_new_center = put_point_in_box(a_new_center, b_new_center, c_new_center)


                        # cluster_diameter based on radius of gyration
                        #radius_of_gyration = sqrt(sum_distance_from_center_list[index]/np.count_nonzero(labels==li))
                        #max_cluster_size = 2*(3./4/np.pi* np.count_nonzero(labels==li)/config.rho)**(1/3.)

                        #cluster_diameter = 2*radius_of_gyration
                        #cluster_diameter = max_cluster_size

                        cluster_center_list.append(np.array([a_new_center, b_new_center, c_new_center]))
                        #cluster_diameter_list.append(cluster_diameter)
                        #print('-----------Cluster # %d ---------------' %li)
                        #print('Center (a, b, c) = %1.3g, %1.3g, %1.3g' %(a_new_center, b_new_center, c_new_center))
                        #print('2Rg = %1.3g A, Cluster size = %1.3g' %(2*radius_of_gyration, max_cluster_size))
                        #print('---------------------------------------')

                    index += 1

        """
        cluster_center = cluster_center_list[-1]
        radius_list = [] # distance of each point within a cluster to its center
        for a, b, dc, lj in zip(ak, bk, ck, labels):
            if lj == li: # only those points that belong to the cluster
                radius = distance(cluster_center, np.array([a, b, dc]))
                radius_list.append(radius)
        """
    return cluster_center_list
    #return(cluster_center_list, cluster_diameter_list)

def put_point_in_box(a, b, c):
    """
    :param a:
    :param b:
    :param c:
    :return: The new coordinate inside the unit cell
    """
    if a > config.Lx:
        a -= config.Lx
    if a < 0:
        a += config.Lx

    if b > config.Ly:
        b -= config.Ly
    if b < 0:
        b += config.Ly

    if c > config.Lz:
        c -= config.Lz
    if c < 0:
        c += config.Lz

    return a, b, c