# @Date    : 2022-04-21 08:00:50
# @Author  : Barnabas Szucs (szucsbarnabas98@protonmail.com)

from __future__ import unicode_literals
from utilities import BpmnGraphParser
from timeit import default_timer as timer
import igraph as ig
import networkx as nx
from tqdm import tqdm
from itertools import product
from igraph import Plot
import igraph as ig
import os
import signal
from statistics import mean  
from itertools import combinations
import argparse
import timeit

parser = argparse.ArgumentParser(description='BPMN similarity exhaustive search')
parser.add_argument('timeout', type=int, help='Give the timeout in seconds(!), defaults to 10 minutes.', default=600)

class TimeOutException(Exception):
    pass


def signal_handler(signum, frame):
    raise TimeOutException("Timed out!")

signal.signal(signal.SIGALRM, signal_handler)


helper_dict = dict()

def bron_kerbosch1(M, clique, candidates, excluded):
    if not candidates and not excluded:
        yield clique
        return
    for v in list(candidates):
        if helper_dict.get(M.vs[v]) is None:
            helper_dict[M.vs[v]] = set(M.neighbors(M.vs[v]))
        v_neighbors = helper_dict[M.vs[v]]
        new_candidates = candidates.intersection(v_neighbors)
        new_excluded = excluded.intersection(v_neighbors)
        yield from bron_kerbosch1(M, clique + [v], new_candidates, new_excluded)
        candidates.remove(v)
        excluded.add(v)

def bron_kerbosch2(M, clique, candidates, excluded):
    if not candidates and not excluded:
        yield clique
        return
    pivot = pick_random(M, candidates, excluded)
    if helper_dict.get(M.vs[pivot]) is None:
        helper_dict[M.vs[pivot]] = set(M.neighbors(M.vs[pivot]))
    p = candidates.difference(helper_dict[M.vs[pivot]])
    for v in list(p):
        if helper_dict.get(M.vs[v]) is None:
            helper_dict[M.vs[v]] = set(M.neighbors(M.vs[v]))
        v_neighbors = helper_dict[M.vs[v]]
        new_candidates = candidates.intersection(v_neighbors)
        new_excluded = excluded.intersection(v_neighbors)
        yield from bron_kerbosch2(M, clique + [v], new_candidates, new_excluded)
        candidates.remove(v)
        excluded.add(v)

def pick_random(M, candidates: set, excluded: set):
    union = candidates.union(excluded)
    elem = union.pop()
    return elem
  
def node_product(G, H):
    def _dict_product(d1, d2):
        return {k: (d1.get(k), d2.get(k)) for k in set(d1) | set(d2)}
    for u, v in product(G, H):
        yield ((u, v), _dict_product(G.nodes[u], H.nodes[v]))

def modular_product_graph(G: ig.Graph, H: ig.Graph) -> ig.Graph:
    print(f"Started modular product creation.")
    _G = G.to_networkx().to_undirected()
    _H = H.to_networkx().to_undirected()
    _GD = G.to_networkx()
    _HD = H.to_networkx()
    
    GH = nx.Graph()
    GH.add_nodes_from(node_product(_G, _H))
    for node_i in tqdm(GH.nodes()):
        for node_j in GH.nodes():
            if node_i == node_j:
                continue
            gh_node_candidate_one  = GH.nodes[node_i]
            gh_node_candidate_two  = GH.nodes[node_j]
            g_inner_node_one = gh_node_candidate_one['id'][0]
            g_inner_node_two = gh_node_candidate_two['id'][0]
            
            h_inner_node_one = gh_node_candidate_one['id'][1]
            h_inner_node_two = gh_node_candidate_two['id'][1]
            adjacent_in_g = (g_inner_node_one in _G.adj[g_inner_node_two])
            adjacent_in_h = (h_inner_node_one in _H.adj[h_inner_node_two])
            if adjacent_in_g and adjacent_in_h:
                g_inner_node_one_type = gh_node_candidate_one['type'][0]
                g_inner_node_two_type = gh_node_candidate_two['type'][0]
                h_inner_node_one_type = gh_node_candidate_one['type'][1]
                h_inner_node_two_type = gh_node_candidate_two['type'][1]
                if (g_inner_node_one_type != h_inner_node_one_type) or (g_inner_node_two_type != h_inner_node_two_type):
                    continue
                # TODO make it to filter edges to have the same direction
                g_one_to_g_two = not set(_GD.out_edges(g_inner_node_one)).intersection(set(_GD.in_edges(g_inner_node_two)))
                g_two_to_g_one = not set(_GD.out_edges(g_inner_node_two)).intersection(set(_GD.in_edges(g_inner_node_one)))
                h_one_to_h_two = not set(_HD.out_edges(h_inner_node_one)).intersection(set(_HD.in_edges(h_inner_node_two)))
                h_two_to_h_one = not set(_HD.out_edges(h_inner_node_two)).intersection(set(_HD.in_edges(h_inner_node_one)))
                if (g_one_to_g_two and h_one_to_h_two) or (g_two_to_g_one and h_two_to_h_one):
                    GH.add_edge(node_i, node_j)
            elif not adjacent_in_g and not adjacent_in_h:
                if(g_inner_node_one == g_inner_node_two) or (h_inner_node_one == h_inner_node_two):
                    continue
                GH.add_edge(node_i, node_j)

    igraph_format = ig.Graph.from_networkx(GH)
    igraph_format.vs.select(_degree=0).delete()
    print("Finished modular product creation.")
    return igraph_format

def get_max_clique_bk1(input_graph, debug=False):
    P = set([vertex.index for vertex in input_graph.vs()])
    R = []
    X = set()
    C = []
    start = timer()

    try:
        t_clique = []
        for clique in bron_kerbosch1(input_graph, R, P, X):
            if len(clique) > len(t_clique):
                C.append(clique)
                t_clique = clique
    except Exception:
        print("Timeout!")

    end = timer()
    if debug:
        print(f"BK1 Elapsed time(msec): {(end - start)*1000}")
    max_clique = max(C, key=lambda clique: len(clique))
    return max_clique

def get_max_clique_bk2(input_graph, debug=False):
    P = set([vertex.index for vertex in input_graph.vs()])
    R = []
    X = set()
    C = []
    start = timer()

    try:
        t_clique = []
        for clique in bron_kerbosch2(input_graph, R, P, X):
            if len(clique) > len(t_clique):
                C.append(clique)
                t_clique = clique
    except Exception:
        print("Timeout!")

    end = timer()
    if debug:
        print(f"BK2 Elapsed time(msec): {(end - start)*1000}")
    max_clique = max(C, key=lambda clique: len(clique))
    return max_clique

def color_similarity(modular_product, max_clique_in_product, graph_candidate_one, graph_candidate_two):
    vertex_set1 = set()
    vertex_set2 = set()

    for vertex_id in max_clique_in_product:
        first_graph_id = modular_product.vs[vertex_id]['id'][0]
        second_graph_id = modular_product.vs[vertex_id]['id'][1]
        vertex_set1.add(first_graph_id)
        vertex_set2.add(second_graph_id)


    mces_one = graph_candidate_one.es.select(_between = (vertex_set1, vertex_set1))
    mces_two = graph_candidate_two.es.select(_between = (vertex_set2, vertex_set2))
    mces_one['color'] = "red"
    mces_two['color'] = "red"
    mces_one['width'] = 5
    mces_two['width'] = 5
    common_edge_count = 0
    for edge in mces_one:
        common_edge_count += 1
        graph_candidate_one.vs[edge.source]['color'] = 'blue'
        graph_candidate_one.vs[edge.target]['color'] = 'blue'

    for edge in mces_two:
        graph_candidate_two.vs[edge.source]['color'] = 'blue'
        graph_candidate_two.vs[edge.target]['color'] = 'blue'

    return common_edge_count

def visualize_similarity(graph_candidate_one, graph_candidate_two, modular_product, max_clique_in_product, output_filename, debug=False):
    color_similarity(modular_product, max_clique_in_product, graph_candidate_one, graph_candidate_two)
    colsep, rowsep = 100, 100
    width, height = 400, 400

    # Construct the plot
    plot = Plot(f"output/{output_filename}", bbox=(4*width, 4*height), background="white")

    # Create the graph and add it to the plot
    plot.add(graph_candidate_one, bbox=(colsep/2, rowsep/2, -colsep/2 + width*(2), -rowsep/2 + height*(2)))
    plot.add(graph_candidate_two, bbox=(colsep/2, rowsep/2 + height*(3), -colsep/2 + width*(3), -rowsep/2 + height*(2)))

    plot.save()
    if debug:
        plot.redraw()
        plot.show()


if __name__ == "__main__":
    args = parser.parse_args()
    test_pairs = list(combinations(os.listdir("data/"), 2))

    for test_pair in test_pairs:
        input_1_filename, input_2_filename = test_pair
        bpmn_one, bpmn_two = BpmnGraphParser(f"data/{input_1_filename}"), BpmnGraphParser(f"data/{input_2_filename}")
        G, H = bpmn_one.get_graph(), bpmn_two.get_graph()
        print(f"G fájlneve: {input_1_filename}, H fájlneve: {input_2_filename}")
        print(f"G élszáma: {len(G.es)}, H élszáma: {len(H.es)}")
        MODULAR_PRODUCT_GRAPH = modular_product_graph(G, H)
        print(f"Moduláris szorzatgráf csúcsszáma: {len(MODULAR_PRODUCT_GRAPH.vs)}, átlagos szomszédszám: {mean([len(MODULAR_PRODUCT_GRAPH.neighbors(vertex)) for vertex in MODULAR_PRODUCT_GRAPH.vs])}")
        print("-----------------------------------------------------------------------")
        # signal.alarm(args.timeout)
        # ret1 = timeit.timeit(lambda: get_max_clique_bk1(MODULAR_PRODUCT_GRAPH), number=1)
        # ret2 = timeit.timeit(lambda: get_max_clique_bk2(MODULAR_PRODUCT_GRAPH), number=1)
        # print(f"BK1:{ret1}, BK2:{ret2}")
        max_clique = get_max_clique_bk2(MODULAR_PRODUCT_GRAPH, True)
        print(f"Talált maximum klikk mérete: {len(max_clique)}")
        print("-----------------------------------------------------------------------")
        # visualize_similarity(G, H, MODULAR_PRODUCT_GRAPH, max_clique, output_filename=f"{input_1_filename}-{input_2_filename}_similarity.png")
        # layout = MODULAR_PRODUCT_GRAPH.layout('grid')
        # ig.plot(MODULAR_PRODUCT_GRAPH, layout=layout)

    # max_clique = get_max_clique_bk2(MODULAR_PRODUCT_GRAPH)