import matplotlib.pyplot as plt


def net_visualize(net=None, nodes=None, charging_pos=None):
    x_node = []
    y_node = []
    x_charging_pos = []
    y_charging_pos = []
    for node in nodes:
        x_node.append(node.location[0])
        y_node.append(node.location[1])

    for charging_point in charging_pos:
        x_charging_pos.append(charging_point[0])
        y_charging_pos.append(charging_point[1])

    fig = plt.figure()
    ax = fig.add_subplot()
    ax.scatter(x_node, y_node, color='blue')
    ax.scatter(x_charging_pos, y_charging_pos, color='red')
    plt.show()
