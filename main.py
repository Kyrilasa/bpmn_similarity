# @Date    : 2022-04-21 08:00:50
# @Author  : Barnabas Szucs (szucsbarnabas98@protonmail.com)

from __future__ import unicode_literals
from utilities import BpmnGraphParser
from timeit import default_timer as timer

import igraph as ig
import networkx as nx
import matplotlib.pyplot as plt
from tqdm import tqdm
from itertools import product
from igraph import Plot

helper_dict = dict()


def bronker_bosch1(M, clique, candidates, excluded, C):
    global bk1_counter
    bk1_counter += 1
    if not candidates and not excluded:
        C += [clique]
        return
    for v in list(candidates):
        v_neighbors = set(M.neighbors(M.vs[v]))
        new_candidates = candidates.intersection(v_neighbors)
        new_excluded = excluded.intersection(v_neighbors)
        bronker_bosch1(M, clique + [v], new_candidates, new_excluded, C)
        candidates.remove(v)
        excluded.add(v)
    return C

def bronker_bosch2(M, clique: set, candidates, excluded, C):
    if not candidates and not excluded:
        C += [clique]
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
        bronker_bosch2(M, clique + [v], new_candidates, new_excluded, C)
        candidates.remove(v)
        excluded.add(v)
    return C


def pick_random(M, candidates: set, excluded: set):
    union = candidates.union(excluded)
    elem = union.pop()
    return elem
    # elem = max(union, key=lambda x: len(intersect(candidates, M.neighbors(M.vs[x]))))
    # return elem
  
def node_product(G, H):
    def _dict_product(d1, d2):
        return {k: (d1.get(k), d2.get(k)) for k in set(d1) | set(d2)}
    for u, v in product(G, H):
        yield ((u, v), _dict_product(G.nodes[u], H.nodes[v]))

def modular_product_graph(G: ig.Graph, H: ig.Graph) -> ig.Graph:
    print(f"Started modular product creation.")
    _G = G.to_networkx().to_undirected()
    _H = H.to_networkx().to_undirected()
    
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
                #IF MATCH TASK TYPES TOO uncomment this.
                g_inner_node_one_type = gh_node_candidate_one['type'][0]
                g_inner_node_two_type = gh_node_candidate_two['type'][0]
                h_inner_node_one_type = gh_node_candidate_one['type'][1]
                h_inner_node_two_type = gh_node_candidate_two['type'][1]
                if (g_inner_node_one_type != h_inner_node_one_type) or (g_inner_node_two_type != h_inner_node_two_type):
                    continue
                GH.add_edge(node_i, node_j)
            elif not adjacent_in_g and not adjacent_in_h:
                if(g_inner_node_one == g_inner_node_two) or (h_inner_node_one == h_inner_node_two):
                    continue
                GH.add_edge(node_i, node_j)
    igraph_format = ig.Graph.from_networkx(GH)
    igraph_format.vs.select(_degree=0).delete()
    print("Finished modular product creation.")
    return igraph_format

if __name__ == "__main__":
    filename = './data/model_2.bpmn'
    filename2 = './data/model_4.bpmn'
    bpmnObject = BpmnGraphParser(filename)
    bpmnObject2 = BpmnGraphParser(filename2)
    g = bpmnObject.get_graph()
    g2 = bpmnObject2.get_graph()

    MODULAR_PRODUCT_GRAPH = modular_product_graph(g, g2)
    
    # P = set([vertex.index for vertex in MODULAR_PRODUCT_GRAPH.vs()])
    # R = []
    # X = set()
    # C = []
    # start = timer()
    # C_3 = bronker_bosch1(MODULAR_PRODUCT_GRAPH, R, P, X, C)
    # end = timer()
    # print(f"Elapsed time: {end - start}")
    # print(bk1_counter)
    P = set([vertex.index for vertex in MODULAR_PRODUCT_GRAPH.vs()])
    R = []
    X = set()
    C = []
    start = timer()
    C_4 = bronker_bosch2(MODULAR_PRODUCT_GRAPH, R, P, X, C)
    end = timer()
    print(f"Elapsed time: {end - start}")

    max_clique = max(C_4, key=lambda clique: len(clique))

    for vertex_id in max_clique:
        first_graph_id = MODULAR_PRODUCT_GRAPH.vs[vertex_id]['id'][0]
        second_graph_id = MODULAR_PRODUCT_GRAPH.vs[vertex_id]['id'][1]
        # print(MODULAR_PRODUCT_GRAPH.vs[vertex_id])
        # print(list(g.vs))
        g.vs[first_graph_id]['color'] = 'blue' 
        g2.vs[second_graph_id]['color'] = 'blue'      

    shape = (1, 1)
    colsep, rowsep = 70, 70
    width, height = 200, 200

    # Construct the plot
    plot = Plot("plot.png", bbox=(4*width, 4*height), background="white")

    # Create the graph and add it to the plot
    plot.add(g, bbox=(colsep/2, rowsep/2, -colsep/2 + width*(2), -rowsep/2 + height*(2)))
    plot.add(g2, bbox=(colsep/2, rowsep/2 + height*(3), -colsep/2 + width*(3), -rowsep/2 + height*(2)))
    plot.redraw()

    plot.show()