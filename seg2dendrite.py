import os
import h5py
import skan
import numpy
import logging
import argparse
import networkx as nx
from skimage import morphology, measure


def build_branch_graph(skel_branches):
    graph_b = nx.Graph()
    graph_b.add_weighted_edges_from(
        zip(
            skel_branches["node-id-src"],
            skel_branches["node-id-dst"],
            skel_branches["branch-distance"],
        )
    )
    return graph_b


def extract_pos_2d(skan_branches, scale=2):
    pos_dict = {}

    for i, row in skan_branches.iterrows():
        for typ in ["src", "dst"]:
            node_id = int(row[f"node-id-{typ}"])
            y, x = row[f"image-coord-{typ}-1"], row[f"image-coord-{typ}-2"]
            pos_dict[node_id] = (scale * x, scale * y)

    return pos_dict


def extract_pos_3d(skan_branches, scale=2):
    pos_dict = {}

    for i, row in skan_branches.iterrows():
        for typ in ["src", "dst"]:
            node_id = int(row[f"node-id-{typ}"])
            z, y, x = (
                row[f"image-coord-{typ}-0"],
                row[f"image-coord-{typ}-1"],
                row[f"image-coord-{typ}-2"],
            )
            pos_dict[node_id] = (scale * x, scale * y, scale * z)

    return pos_dict


def read_ilastik_seg(ilastik_seg_fn):
    with h5py.File(ilastik_seg_fn, "r") as hf:
        return hf["exported_data"][()][0, ..., 0]


def remove_small_segments(seg, min_size):
    seg = measure.label(seg)
    rp = measure.regionprops(seg)
    rp = sorted(rp, key=lambda r: r.area, reverse=True)
    logging.info(
        f"  - Found {len(rp)} segments size=: {','.join([str(r.area) for r in rp])}"
    )

    for r in rp:
        if r.area < min_size:
            seg[r.coords[:, 0], r.coords[:, 1], r.coords[:, 2]] = 0

    return measure.label(seg).astype(numpy.uint8)


def skeletonize(seg_binary, vx_size=(1, 1, 1)):
    skel_img = morphology.skeletonize_3d(seg_binary)

    skel = skan.Skeleton(skel_img, spacing=vx_size)
    skel_branches = skan.summarize(skel)

    return skel, skel_branches


def shortest_dendrite_path(graph_b):
    graph_dend = graph_b.subgraph([n for n in graph_b.nodes if graph_b.degree(n) > 1])

    predecessors, d = nx.floyd_warshall_predecessor_and_distance(graph_dend)

    max_path = 0
    a = None
    b = None
    for i in graph_dend.nodes():
        for j in graph_dend.nodes():
            if i != j:
                dist = d[i][j]
                if dist > max_path:
                    max_path = dist
                    a = i
                    b = j

    return nx.reconstruct_path(a, b, predecessors)


def convert_graph_to_swc(graph_b, shortest_path, pos3d, radius=1):
    spine_candidates = set(graph_b.nodes).difference(set(shortest_path))

    # node remapping to 1..n
    node_mapping = {}

    # init node counter and output
    i = 1
    output = []

    # recursuve spine traverser
    def add_spine_rec(c, b, typ=1, r=radius):
        nonlocal i
        if c not in node_mapping:
            node_mapping[c] = i
        i += 1

        output.append((node_mapping[c], typ,) + pos3d[c] + (r, node_mapping[b]))
        spine_candidates.remove(c)

        if graph_b.degree(c) > 1:
            for sp in graph_b.edges(c):
                if sp[1] in spine_candidates:
                    add_spine_rec(sp[1], c)

    c = shortest_path[0]
    node_mapping[c] = 1
    output.append((node_mapping[c], 0,) + pos3d[c] + (radius, -1))
    i += 1
    for sp in graph_b.edges(c):
        if sp[1] in spine_candidates:
            add_spine_rec(sp[1], c, typ=0)

    for b, c in zip(shortest_path[:-1], shortest_path[1:]):
        if c not in node_mapping:
            node_mapping[c] = i
        i += 1

        output.append((node_mapping[c], 0,) + pos3d[c] + (radius, node_mapping[b]))

        for sp in graph_b.edges(c):
            if sp[1] in spine_candidates:
                add_spine_rec(sp[1], c)

    return output


def write_swc(fn, swc_table):
    lines = list(map(lambda t: " ".join(map(str, t)) + "\n", swc_table))

    with open(fn, "wt") as fh:
        fh.writelines(lines)


def run(ilastik_seg_fn, min_size, scale):
    logging.info(f"File:    {ilastik_seg_fn} ")
    logging.info(f"MinSize: {min_size} ")
    logging.info(f"Scale:   {scale} (reso. level)")
    logging.info("-" * 80)
    base_fn = os.path.splitext(ilastik_seg_fn)[0]

    logging.info("  - Read segmentation")
    img_seg = read_ilastik_seg(ilastik_seg_fn)

    img_seg = remove_small_segments(img_seg, min_size)
    logging.info(f"  - Removed segments smaller {min_size} px")

    logging.info(f"  - Creating {img_seg.max()} .swc filament objects")
    for seg_id in range(1, 1 + img_seg.max()):
        logging.info(f"  {seg_id}: Skeletonize")
        skel, skel_branches = skeletonize(img_seg == seg_id)
        pos_3d = extract_pos_3d(skel_branches, scale)

        logging.info(f"   : Build branch graph")
        graph_branches = build_branch_graph(skel_branches)

        logging.info(f"   : Compute longest shortest path")
        shortest_path = shortest_dendrite_path(graph_branches)

        if len(shortest_path) < 3:
            logging.info(f"   : Skeleton too short. skipping...")
            continue

        logging.info(f"   : Relabel graph for .swc format")
        swc_table = convert_graph_to_swc(
            graph_branches, shortest_path, pos_3d, radius=1
        )

        logging.info(f"   : Write output .swc file")
        write_swc(base_fn + f"_fil{seg_id:02d}.swc", swc_table)
    logging.info("Done")


def get_args():
    description = """Extract skeletons from ilastik dendtite segmentation and export to .swc for import in Imaris"""

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("ilastik_seg_h5", nargs="+", type=str)
    parser.add_argument("-ms", "--min_size", type=int, default=10000)
    parser.add_argument("-s", "--scale", type=int, default=2)

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    args = get_args()

    for ilastik_fn in args.ilastik_seg_h5:
        run(ilastik_fn, args.min_size, args.scale)

