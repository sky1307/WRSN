import csv

from scipy.spatial import distance

import Simulator.parameter as para
from Simulator.Network.network_method import uniform_com_func, to_string, count_package_function, \
    Kmeans_network_clustering
from Optimizer.A3C.Server_method import synchronize
from Optimizer.A3C.Worker_method import all_asynchronize


class Network:
    def __init__(self, list_node=None, mc_list=None, target=None, server=None, package_size=400, nb_charging_pos=81):
        self.node = list_node
        self.set_neighbor()
        self.set_level()
        self.mc_list = mc_list
        self.target = target
        self.charging_pos = []
        self.request_list = []  # Full list of requesting massages: ['id', 'energy', 'avg_energy',
        # 'energy_estimate', 'time']
        self.request_id = []
        self.package_size = package_size
        self.nb_charging_pos = nb_charging_pos
        self.active = False
        self.package_lost = False
        self.index_node_in_cluster = []  # index_node_in_cluster[index] = list of id Node \in cluster index

        self.Server = server
        self.T = para.A3C_synchronize_T

    def set_neighbor(self):
        for node in self.node:
            for other in self.node:
                if other.id != node.id and distance.euclidean(node.location, other.location) <= node.com_ran:
                    node.neighbor.append(other.id)

    def set_level(self):
        queue = []
        for node in self.node:
            if distance.euclidean(node.location, para.base) < node.com_ran:
                node.level = 1
                queue.append(node.id)
        while queue:
            for neighbor_id in self.node[queue[0]].neighbor:
                if not self.node[neighbor_id].level:
                    self.node[neighbor_id].level = self.node[queue[0]].level + 1
                    queue.append(neighbor_id)
            queue.pop(0)

    def set_charging_pos(self, func=Kmeans_network_clustering):
        self.charging_pos = func(self)
        # for mc in self.mc_list:
        #     mc.optimizer.update_charging_pos(self.charging_pos)
        self.active = True

    def communicate(self, func=uniform_com_func):
        return func(self)

    def run_per_second(self, t):
        # ========= Synchronize at t = 0 and t % T == 0 ===========
        if t == 0:
            if self.Server is None:
                print("A3C without global Server ??? Recheck your declaration")
                exit(100)
            else:
                synchronize(self.Server, self.mc_list)

        if t % self.T == 0 and t > para.SIM_partition_time:  # after T (s)
            if all_asynchronize(MCs=self.mc_list, Server=self.Server, moment=t):
                print(f"Synchronize at time {t}")
                synchronize(self.Server, self.mc_list)
        # ==========================================================
        state = self.communicate()
        self.request_id = []
        for index, node in enumerate(self.node):
            if node.energy_thresh > node.energy > 0:
                node.request(network=self, t=t)
                self.request_id.append(index)
            else:
                node.is_request = False
        if self.request_id:
            for index, node in enumerate(self.node):
                if index not in self.request_id and (t - node.check_point[-1]["time"]) > 50:
                    node.set_check_point(t)
        if self.active:
            for mc in self.mc_list:
                mc.run(net=self, time_stamp=t)
        return state

    def simulate_max_time(self, max_time=2000000, file_name="log/information_log.csv"):
        with open(file_name, "w") as information_log:
            writer = csv.DictWriter(information_log, fieldnames=["time", "nb_dead_node", "nb_package"])
            writer.writeheader()
        nb_dead = 0
        nb_package = len(self.target)
        dead_time = 0
        t = 0
        while t <= max_time:
            t = t + 1
            if (t - 1) % para.SIM_log_frequency == 0:
                print("time = ", t, ", lowest energy node: ", self.node[self.find_min_node()].energy, "at",
                      self.node[self.find_min_node()].location)
                print('\tnumber of dead sensor nodes: {}'.format(self.count_dead_node()))
                print('\tnumber of monitored targets: {}'.format(self.count_package()))
                with open(file_name, 'a') as information_log:
                    node_writer = csv.DictWriter(information_log, fieldnames=["time", "nb_dead_node", "nb_package"])
                    node_writer.writerow(
                        {"time": t, "nb_dead_node": self.count_dead_node(), "nb_package": self.count_package()})
                for mc in self.mc_list:
                    print("\tMC#{} at{} is {}".format(mc.id, mc.current, mc.get_status()))

            ######################################
            if t == para.SIM_partition_time:
                self.set_charging_pos()
            ######################################

            state = self.run_per_second(t)
            current_dead = self.count_dead_node()
            current_package = self.count_package()
            if not self.package_lost:
                if current_package < len(self.target):
                    self.package_lost = True
                    dead_time = t
            if current_dead != nb_dead or current_package != nb_package:
                nb_dead = current_dead
                nb_package = current_package
                with open(file_name, 'a') as information_log:
                    node_writer = csv.DictWriter(information_log, fieldnames=["time", "nb_dead_node", "nb_package"])
                    node_writer.writerow({"time": t, "nb_dead_node": current_dead, "nb_package": current_package})

        print('\nFinished with {} dead sensors, {} packages'.format(self.count_dead_node(), self.count_package()))
        return dead_time, nb_dead

    def simulate(self, max_time=2000000, file_name='log/log.csv'):
        if max_time:
            life_time = self.simulate_max_time(max_time=max_time, file_name=file_name)
        else:
            life_time = self.simulate_lifetime(file_name=file_name)
        return life_time

    def print_net(self, func=to_string):
        func(self)

    def find_min_node(self):
        min_energy = 10 ** 10
        min_id = -1
        for node in self.node:
            if min_energy > node.energy > 0:
                min_energy = node.energy
                min_id = node.id
        return min_id

    def count_dead_node(self):
        count = 0
        for node in self.node:
            if node.energy <= 0:
                count += 1
        return count

    def count_package(self, count_func=count_package_function):
        count = count_func(self)
        return count

    ##############################################################################################
    def simulate_lifetime(self, file_name="log/energy_log.csv"):
        energy_log = open(file_name, "w")
        node_log = open('log/dead_node.csv', 'w')
        writer = csv.DictWriter(energy_log, fieldnames=["time", "mc energy", "min energy"])
        writer.writeheader()
        node_writer = csv.DictWriter(node_log, fieldnames=['time', 'dead_node'])
        node_writer.writeheader()
        node_log.close()
        t = 0
        while t <= 2000000:
            t = t + 1
            if (t - 1) % para.SIM_log_frequency == 0:
                node_log = open('log/dead_node.csv', 'a')
                node_writer = csv.DictWriter(node_log, fieldnames=['time', 'dead_node'])
                node_writer.writerow({"time": t, "dead_node": self.count_dead_node()})
                node_log.close()
                print('number of dead node: {}'.format(self.count_dead_node()))
                print("time = ", t, ", lowest energy node: ", self.node[self.find_min_node()].energy, "at",
                      self.node[self.find_min_node()].location)
                for mc in self.mc_list:
                    print("\tMC#{} at{} is {}".format(mc.id, mc.current, mc.get_status()))
            state = self.run_per_second(t)
            if not (t - 1) % 50:
                for mc in self.mc_list:
                    writer.writerow(
                        {"time": t, "mc energy": mc.energy, "min energy": self.node[self.find_min_node()].energy})

        print(t, self.node[self.find_min_node()].energy)
        for mc in self.mc_list:
            print("\tMC#{} at{}".format(mc.id, mc.current))
            writer.writerow({"time": t, "mc energy": mc.energy, "min energy": self.node[self.find_min_node()].energy})
        energy_log.close()
        return t
