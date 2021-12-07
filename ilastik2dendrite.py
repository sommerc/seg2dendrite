import os
import h5py
import skan
import json
import numpy
import logging
import argparse
import networkx as nx
from skimage import morphology, measure, filters


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


def segment_prob_map(ilastik_fn, sigma, thresh):
    with h5py.File(ilastik_fn, "r") as hf:
        axis_tags = json.loads(hf["exported_data"].attrs["axistags"])["axes"]

        zyx_idx = [[d["key"] for d in axis_tags].index(dd) for dd in "zyx"]

        zyx_sel = [0,] * len(axis_tags)
        for d in zyx_idx:
            zyx_sel[d] = slice(None)

        prob_map = hf["exported_data"][()][tuple(zyx_sel)]

    if prob_map.dtype != numpy.uint8:
        logging.warn(
            f"  Probability map seems to have wrong pixel type. Expected uint8. got {prob_map.dtype}"
        )

    assert (
        len(prob_map.shape) == 3
    ), f"Wrong dimensions. Expected 3D, got shape: '{prob_map.shape}'"

    img = filters.gaussian(prob_map, sigma=sigma, preserve_range=True)
    seg = measure.label(img > (255 * thresh))
    return seg


def remove_small_segments(seg, min_size):
    seg = measure.label(seg)
    rp = measure.regionprops(seg)
    rp = sorted(rp, key=lambda r: r.area, reverse=True)
    logging.info(
        f"  - Found {len(rp)} segments sizes (px): {','.join([str(r.area) for r in rp[:10]])} ..."
    )

    seg = morphology.remove_small_objects(seg, min_size=min_size)

    return measure.label(seg).astype(numpy.uint16)


def skeletonize(seg_binary, vx_size=(1, 1, 1)):
    skel_img = morphology.skeletonize_3d(seg_binary)

    skel = skan.Skeleton(skel_img, spacing=vx_size)
    skel_branches = skan.summarize(skel)

    return skel, skel_branches


# def _get_shortest_longest_path(graph_dend):
#     predecessors, d = nx.floyd_warshall_predecessor_and_distance(graph_dend)

#     max_path = 0
#     a = None
#     b = None
#     for i in graph_dend.nodes():
#         for j in graph_dend.nodes():
#             if i != j:
#                 dist = d[i][j]
#                 if dist > max_path:
#                     max_path = dist
#                     a = i
#                     b = j

#     return nx.reconstruct_path(a, b, predecessors)


def shortest_dendrite_path(graph_b):
    graph_dend = graph_b.subgraph([n for n in graph_b.nodes if graph_b.degree(n) > 1])

    graph_dend2 = graph_dend.subgraph(
        [n for n in graph_dend.nodes if graph_dend.degree(n) > 1]
    )

    mst = nx.algorithms.minimum_spanning_tree(graph_dend2)
    mst_df = nx.algorithms.traversal.depth_first_search.dfs_edges(mst)
    return list(mst_df)


def flatten(t):
    return [item for sublist in t for item in sublist]


def convert_graph_to_swc(graph_b, dend_edges, pos3d, radius=1):
    dend_nodes = set(flatten(dend_edges))

    spine_candidates = set(graph_b.nodes).difference(set(dend_nodes))

    # node remapping to 1..n
    node_mapping = {dend_edges[0][0]: -1}

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

    c = dend_edges[0][0]
    for sp in graph_b.edges(dend_edges[0][0]):
        if sp[1] in spine_candidates:
            add_spine_rec(sp[1], c)

    for b, c in dend_edges:
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


def run(ilastik_seg_fn, min_size, rl, sigma, thresh):
    logging.info(f"File:    {ilastik_seg_fn}")
    logging.info(f"MinSize: {min_size}")
    logging.info(f"ResoLev: {rl}")
    logging.info(f"Sigma:   {sigma}")
    logging.info(f"Thresh:  {thresh}")
    logging.info("-" * 80)
    base_fn = os.path.splitext(ilastik_seg_fn)[0]

    logging.info(f"  - Read probability maps and segment")
    img_seg = segment_prob_map(ilastik_seg_fn, sigma, thresh)

    img_seg = remove_small_segments(img_seg, min_size)
    logging.info(f"  - Removed segments smaller {min_size} px")

    logging.info(f"  - Creating {img_seg.max()} .swc filament objects")
    for seg_id in range(1, 1 + img_seg.max()):
        logging.info(f"  {seg_id}: Skeletonize")
        skel, skel_branches = skeletonize(img_seg == seg_id)
        pos_3d = extract_pos_3d(skel_branches, rl)

        logging.info(f"   : Build branch graph")
        graph_branches = build_branch_graph(skel_branches)

        logging.info(f"   : Compute minimum spanning tree")
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
    description = """Extract skeletons from ilastik dendrite probability maps and export to .swc for import in Imaris"""

    parser = argparse.ArgumentParser(description=description)

    parser.add_argument(
        "ilastik_h5",
        nargs="+",
        type=str,
        help="ilastik probability map (single channel) in 8-bit",
    )
    parser.add_argument(
        "-ms",
        "--min_size",
        type=int,
        default=10000,
        help="Minimum object size in pixel",
    )
    parser.add_argument(
        "-rl", "--resolution_level", type=int, default=2, help="Resolution level used",
    )
    parser.add_argument(
        "-s",
        "--smooth_sigma",
        type=float,
        nargs=3,
        default=(0.5, 0.5, 0.5),
        help="Smooth prob. map  before thresholding. Gaussian sigma in px for ZYX",
    )

    parser.add_argument(
        "-t", "--threshold", type=float, default=0.5, help="Probability map threshold",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    logging.basicConfig(format="%(message)s", level=logging.INFO)

    args = get_args()

    for ilastik_fn in args.ilastik_h5:
        run(
            ilastik_fn,
            args.min_size,
            args.resolution_level,
            args.smooth_sigma,
            args.threshold,
        )

