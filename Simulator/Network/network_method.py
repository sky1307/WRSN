import random
import numpy as np
from sklearn.cluster import KMeans

import Simulator.parameter as para
from Simulator.Network.package import Package
from Simulator.Network.network_visualizer import net_visualize


def uniform_com_func(net):
    for node in net.node:
        if node.id in net.target and random.random() <= node.prob and node.is_active:
            package = Package(package_size=net.package_size)
            node.send(net, package)
            # print(package.path)
    return True


def to_string(net):
    min_energy = 10 ** 10
    min_node = -1
    for node in net.node:
        if node.energy < min_energy:
            min_energy = node.energy
            min_node = node
    min_node.print_node()


def count_package_function(net):
    count = 0
    for target_id in net.target:
        package = Package(is_energy_info=True)
        net.node[target_id].send(net, package)
        if package.path[-1] == -1:
            count += 1
    return count


def Kmeans_network_clustering(network=None):
    X = []
    Y = []
    for node in network.node:
        node.set_check_point(200)
        X.append(node.location)
        Y.append(node.avg_energy ** 2)
    X = np.array(X)
    Y = np.array(Y)
    print(Y)
    d = np.sum(Y)
    Y = Y / d
    kmeans = KMeans(n_clusters=network.nb_charging_pos, random_state=0).fit(X, sample_weight=Y)
    charging_pos = []
    for pos in kmeans.cluster_centers_:
        charging_pos.append((int(pos[0]), int(pos[1])))
    charging_pos.append(para.depot)
    print(charging_pos)

    # network.index_node_in_cluster
    for i in range(network.nb_charging_pos):
        network.index_node_in_cluster.append([index for index, label in enumerate(kmeans.labels_) if label == i])

    network.index_node_in_cluster.append([])  # depot
    if para.SIM_plot_network:
        net_visualize(net=network, nodes=network.node, charging_pos=charging_pos)
    return charging_pos
