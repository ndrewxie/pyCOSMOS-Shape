import config
import numpy as np
from clustering_functions import *
from cluster_bin import *
from visualize import *
import time
import periodic_distance
import sys
from plot_psd_bar_pore_type import plot_psd_bar_pore_type

if __name__ == "__main__":

    """
    a, b, c are the lengths along the unit cell basis vectors.
    x, y, z are the distances along the orthogonal basis vectors.
    If the unit cell is orthogonal, than a = x, b = y, and c = z.  
    """

    # a, b, c are the array of coordinates of the geometric points
    a, b, c, geom_dia = read_vpsdpts(config.vpsdpts_file)

    # Each bin will be 1 A wide
    # number of bins = max diameter - min dia in psd
    nbins = int(ceil(geom_dia.max()) - floor(geom_dia.min()))
    print("nbins = ", nbins)
    plot_histogram(geom_dia, nbins=nbins)
    np.savetxt('diameters_of_geometric_points.dat', geom_dia)

    # Divide the geom_dia array into nbins
    bin_freq, bin_edges, bin_address_of_points = make_histogram(geom_dia, nbins)

    # np.argsort returns the indices that would sort an array
    # bin_order is the order in which the bins are analyzed
    # bins are analyzed from the highest bin to the lowest
    bin_order = np.argsort(bin_freq)[::-1]
    bin_analyzed = []

    # Identify and analyze primary bins
    # TODO: Modification currently breaks secondary/primary bin classifications (# of points w/ label -1)
    bin_number = 0
    for bin_histo_number in bin_order:
        histo_ak, histo_bk, histo_ck, histo_diak = \
            extract_points_in_a_bin(a, b, c, geom_dia, bin_address_of_points, bin_histo_number)
        if len(histo_ak) == 0:
            continue
        histo_cluster_labels, histo_cluster_center_list = \
            cluster_points_within_a_bin(histo_ak, histo_bk, histo_ck)
        histo_n_clusters = max(histo_cluster_labels) + 1

        for center_indx in range(0, histo_n_clusters):
            # If the number of pore types identified = NumberOfPoreTypes input, break the loop
            if config.pore_type_count == config.NumberOfPoreTypes:
                break

            # 1. Extract the points within this bin
            # (ak, bk, ck) are list of points with the same bin
            histo_mask = (histo_cluster_labels == center_indx)
            ak = histo_ak[histo_mask]
            bk = histo_bk[histo_mask]
            ck = histo_ck[histo_mask]
            diak = (np.array(histo_diak)[histo_mask]).tolist()

            # 2. Cluster the points within the bin
            # cluster_labels = list of len(ak) with labels
            cluster_labels, cluster_center_list = cluster_points_within_a_bin(ak, bk, ck)

            # 3. Calculate the shape, size, and orientation of the cluster
            cluster_shape_list, cluster_size_list, cluster_length_list, cluster_orientation_list = \
                calculate_shape_and_size_of_cluster_within_bin(cluster_labels, \
                                                            bin_number, ak, bk, ck, cluster_center_list)

            # 4, Classify the points as primary or secondary
            # primary_bin = 1
            primary_bin = classify_bin(cluster_shape_list, diak, cluster_labels, bin_number)

            if primary_bin:
                Ncluster = max(cluster_labels) + 1
                config.pore_type_count += primary_bin
                print('New pore type identified, pore type count = ', config.pore_type_count)
                config.all_cluster_center_list.append(cluster_center_list)
                config.all_cluster_diameter_list.append(cluster_size_list)
                config.all_cluster_length_list.append(cluster_length_list)
                config.all_cluster_shape_list.append(cluster_shape_list)
                config.all_cluster_orientation_list.append(cluster_orientation_list)
                config.all_cluster_pore_type_labels.append(Ncluster * [config.pore_type_count])

                # update the pore type matrix
                update_pore_type_matrix(ak, bk, ck, cluster_labels)

                # x, y, z coordinates in 3d
                xk, yk, zk = abc_to_xyz(ak, bk, ck)
                # save xyz file
                save_as_xyz(bin_number, xk, yk, zk, cluster_labels)
                # plot x, y, z coordinates
                plot_xyz(xk, yk, zk, cluster_labels)
            else:
                # uncomment to see secondary bins on browser
                # xk, yk, zk = abc_to_xyz(ak, bk, ck)
                # plot_xyz(xk, yk, zk, cluster_labels)
                print('%d is a secondary bin' % bin_number)
            bin_number += 1

        # new_pore_type_found = cluster_bin(a, b, c, geom_dia, bin_index_of_points, boi)

    print('===================================================================')
    print('All Primary bins identified')
    print('Number of pore types = %d' % config.pore_type_count)

    if config.pore_type_count == 0:
        print('Exiting, change epsilon and minpts params of dbscan')
        exit(1)

    # show_pore_type_matrix()

    # Analyze secondary bins
    print('Analyzing the secondary bins')
    fill_pore_type_matrix()
    shape_analysis_pore_type_matrix()
    show_pore_type_matrix()
    plot_pore_centers_mayavi()

    # calculate and plot pore type histogram
    pore_type_histogram = np.zeros((config.pore_type_count, nbins))

    for xi, yi, zi, di in zip(a, b, c, geom_dia):
        # which bin does each xyz point belong to
        bin_index = np.digitize(di, bin_edges) - 1

        # which pore type each xyz point belong to
        i, j, k = int(floor(xi)), int(floor(yi)), int(floor(zi))
        pore_type = int(config.pore_type_matrix_with_pore_type_labels[i, j, k])

        # store above two information in pore_type_histogram
        pore_type_histogram[pore_type - 1][bin_index] += 1

    # print(pore_type_histogram)
    bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    plot_psd_bar_pore_type(bin_centers, pore_type_histogram)
    show()

    sys.exit()
