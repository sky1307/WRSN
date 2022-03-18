import Simulator.parameter as para


class Package:
    def __init__(self, is_energy_info=False, package_size=400):
        self.path = []
        self.is_energy_info = is_energy_info
        if not is_energy_info:
            self.size = package_size
        else:
            self.size = para.b_energy
        self.is_success = False

    # def get_size(self):
    #     return para.b if not self.is_energy_info else para.b_energy

    def update_path(self, node_id):
        self.path.append(node_id)
