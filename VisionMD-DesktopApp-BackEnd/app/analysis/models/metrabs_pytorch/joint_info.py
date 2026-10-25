"""Inference-only replacement for posepile.joint_info.JointInfo."""


class JointInfo:
    def __init__(self, names, edges):
        self.names = [str(name) for name in names]
        self.stick_figure_edges = [tuple(map(int, edge)) for edge in edges]
        self.n_joints = len(self.names)
        name_to_index = {name: index for index, name in enumerate(self.names)}
        self.mirror_mapping = [
            name_to_index.get(_mirrored_name(name), index)
            for index, name in enumerate(self.names)
        ]


def _mirrored_name(name):
    if name.startswith("left_"):
        return "right_" + name[5:]
    if name.startswith("right_"):
        return "left_" + name[6:]
    if name.startswith("l"):
        return "r" + name[1:]
    if name.startswith("r"):
        return "l" + name[1:]
    return name
