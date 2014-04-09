#!/usr/bin/env python

from SPARQLWrapper import SPARQLWrapper, JSON
from flask import render_template
import re
from urllib import unquote_plus
import networkx as nx
from networkx.readwrite import json_graph
import json
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from rdflib.serializer import Serializer
import rdfextras
from math import log

from app import app, socketio






concept_type_color_dict = {'popg': '#9edae5', 'inpo': '#ffbb78', 'elii': '#dbdb8d', 'idcn': '#9edae5', 'neop': '#2ca02c', 'vita': '#9467bd', 'inpr': '#c5b0d5', 'phsu': '#c5b0d5', 'blor': '#98df8a', 'hops': '#c7c7c7', 'menp': '#f7b6d2', 'phsf': '#d62728', 'ftcn': '#e377c2', 'anim': '#ff9896', 'food': '#bcbd22', 'grpa': '#ffbb78', 'geoa': '#2ca02c', 'hcpp': '#98df8a', 'lbtr': '#c7c7c7', 'ocdi': '#17becf', 'tisu': '#17becf', 'orch': '#7f7f7f', 'tmco': '#dbdb8d', 'clas': '#bcbd22', 'lipd': '#c49c94', 'dsyn': '#f7b6d2', 'horm': '#aec7e8', 'bact': '#2ca02c', 'grup': '#e377c2', 'bacs': '#ffbb78', 'enty': '#c5b0d5', 'resa': '#98df8a', 'medd': '#9467bd', 'cell': '#bcbd22', 'fndg': '#ff7f0e', 'sbst': '#ff9896', 'prog': '#ff9896', 'celf': '#aec7e8', 'chvf': '#1f77b4', 'diap': '#aec7e8', 'celc': '#8c564b', 'hcro': '#ff7f0e', 'inbe': '#9467bd', 'clna': '#ffbb78', 'acab': '#d62728', 'bodm': '#9467bd', 'patf': '#e377c2', 'carb': '#c7c7c7', 'bpoc': '#d62728', 'dora': '#8c564b', 'moft': '#7f7f7f', 'plnt': '#7f7f7f', 'ortf': '#f7b6d2', 'bmod': '#9edae5', 'sosy': '#dbdb8d', 'enzy': '#d62728', 'qnco': '#1f77b4', 'imft': '#7f7f7f', 'antb': '#1f77b4', 'bdsy': '#c5b0d5', 'nnon': '#9467bd', 'socb': '#c49c94', 'ocac': '#8c564b', 'bdsu': '#8c564b', 'rcpt': '#ff9896', 'nsba': '#c5b0d5', 'mnob': '#e377c2', 'orga': '#1f77b4', 'orgf': '#c7c7c7', 'lbpr': '#d62728', 'orgt': '#aec7e8', 'gngm': '#f7b6d2', 'virs': '#17becf', 'fngs': '#98df8a', 'aapp': '#17becf', 'opco': '#c49c94', 'irda': '#98df8a', 'famg': '#2ca02c', 'acty': '#ff7f0e', 'inch': '#bcbd22', 'cnce': '#9edae5', 'topp': '#ffbb78', 'spco': '#2ca02c', 'lang': '#dbdb8d', 'podg': '#aec7e8', 'mobd': '#ff9896', 'qlco': '#c49c94', 'npop': '#ff7f0e', 'hlca': '#1f77b4', 'phpr': '#ff7f0e', 'strd': '#8c564b'}


def uri_to_label(uri):
    
    if '#' in uri:
        (base,hash_sign,local_name) = uri.rpartition('#')
        base_uri = local_name.encode('utf-8')
    else :
        base_uri = re.sub("http.*/","",uri.encode('utf-8'))
        
    
    return shorten(unquote_plus(base_uri).replace('_',' ').lstrip('-').lstrip(' '))
    
def shorten(text):
    if len(text)>22:
        return text[:10] + "..." + text[-10:]
    else :
        return text


def get_activities(graph_uri, endpoint_uri):
    emit('Retrieving activities...')
    q = render_template('activities.q', graph_uri=graph_uri)
    
    sparql = SPARQLWrapper(endpoint_uri)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(q)
    
    app.logger.debug(u"Query:\n{}".format(q))

    results = sparql.query().convert()
    
    activities = []
    
    for result in results["results"]["bindings"]:
        activity_uri = result['activity']['value']
        
        emit('{}...'.format(activity_uri))
        
        if 'label' in result :
            activity_id = result['label']['value']
        else :
            activity_id = uri_to_label(activity_uri)
        
        
        activities.append({'id': activity_uri, 'text': activity_id})
        
    return activities


def get_named_graphs(endpoint_uri):
    emit('Retrieving graphs...')
    q = render_template('named_graphs.q')
    sparql = SPARQLWrapper(endpoint_uri)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(q)
    
    app.logger.debug(u"Query:\n{}".format(q))

    results = sparql.query().convert()

    graphs = []
    
    for result in results["results"]["bindings"]:
        graph_uri = result['graph']['value']
        emit('{}...'.format(graph_uri))
        
        graphs.append({'uri': graph_uri, 'id': graph_uri, 'text': graph_uri})
        
    return graphs    
    








def build_graph(G, endpoint_uri, name=None, source=None, target=None, query=None, intermediate = None):
    emit('Building edges from {} to {}'.format(source, target))
    
    sparql = SPARQLWrapper(endpoint_uri)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(query)
    
    app.logger.debug(u"Query:\n{}".format(query))
    
    results = sparql.query().convert()

    

    for result in results["results"]["bindings"]:
        app.logger.debug(u"Result:\n{}".format(result))
        
        if not intermediate :
            app.logger.debug("No intermediate node")
            
            if name and not source:
                source_binding = uri_to_label(name).replace("'","");
                source_uri = name
            elif not source :
                source_binding = "example"
                source_uri = "http://prov.data2semantics.org/resource/example"
            else :
                if source+"_label" in result:
                    app.logger.debug("{}_label in result".format(source))
                    source_binding = shorten(result[source+"_label"]["value"])
                else :
                    app.logger.debug("No {}_label in result!!".format(source))
                    source_binding = uri_to_label(result[source]["value"]).replace("'","")
            
            source_uri = result[source]["value"]
                
            if target+"_label" in result:
                target_binding = shorten(result[target+"_label"]["value"])
            else :
                target_binding = uri_to_label(result[target]["value"]).replace("'","")
            
            
            if source+"_type" in result :
                source_type = result[source+"_type"]["value"]
            else :
                source_type = re.sub('\d+$','',source)
            
            if target+"_type" in result :
                target_type = result[target+"_type"]["value"]
            else :
                target_type = re.sub('\d+$','',target)
                
            target_uri = result[target]["value"]
            
            
            G.add_node(source_uri, label=source_binding, type=source_type, uri=source_uri)
            G.add_node(target_uri, label=target_binding, type=target_type, uri=result[target]["value"])
            G.add_edge(source_uri, target_uri, value=10)
            
            
            

        else :
            
            if source+"_label" in result:
                source_binding = shorten(result[source+"_label"]["value"])
            else :
                source_binding = uri_to_label(result[source]["value"]).replace("'","")
                
            if intermediate+"_label" in result:
                intermediate_binding = shorten(result[intermediate+"_label"]["value"])
            else :
                intermediate_binding = uri_to_label(result[intermediate]["value"]).replace("'","")
                
            if target+"_label" in result:
                target_binding = shorten(result[target+"_label"]["value"])
            else :
                target_binding = uri_to_label(result[target]["value"]).replace("'","")
            
            G.add_node(result[source]["value"], label=source_binding, type=re.sub('\d+$','',source), uri=result[source]["value"])
            G.add_node(result[intermediate]["value"], label=intermediate_binding, type=re.sub('\d+$','',intermediate), uri=result[intermediate]["value"])
            G.add_node(result[target]["value"], label=target_binding, type=re.sub('\d+$','',target), uri=result[target]["value"])
            
            G.add_edge(result[source]["value"], result[intermediate]["value"], value=10)
            G.add_edge(result[intermediate]["value"], result[target]["value"], value=10)

    app.logger.debug('Query-based graph building complete...')
    emit('Query-based graph building complete...')

    return G


def build_full_graph(graph_uri, endpoint_uri):
    app.logger.debug(u"Building full graph")
    emit("Building full provenance graph...")
    
    G = nx.DiGraph()
    
    q_activity_to_resource = render_template('activity_to_resource.q', graph_uri=graph_uri)
    app.logger.debug("Running activity_to_resource")
    emit("Running activity_to_resource")
    G = build_graph(G, endpoint_uri, source="activity", target="entity", query=q_activity_to_resource)
    
    q_resource_to_activity = render_template('resource_to_activity.q', graph_uri=graph_uri)
    app.logger.debug("Running resource to activity")
    emit("Running activity_to_resource")
    G = build_graph(G, endpoint_uri, source="entity", target="activity", query=q_resource_to_activity)
    
    q_derived_from = render_template('derived_from.q', graph_uri = graph_uri)
    app.logger.debug("Running derived from")
    emit("Running derived from")
    G = build_graph(G, endpoint_uri, source="entity1", target="entity2", query=q_derived_from)
    
    q_informed_by = render_template('informed_by.q', graph_uri = graph_uri)
    app.logger.debug("Running informed by")
    emit("Running informed by")
    G = build_graph(G, endpoint_uri, source="activity1", target="activity2", query=q_informed_by)
    
    emit("Building full provenance graph complete...")
    return G
    
def extract_activity_graph(G, activity_uri, activity_id):
    app.logger.debug(u"Extracting graph for {} ({})".format(activity_uri, activity_id))
    emit("Extracting graph for {} ({})".format(activity_uri, activity_id))
    
    origin_node_id = activity_uri

    outG = nx.ego_graph(G,origin_node_id,50)
    inG = nx.ego_graph(G.reverse(),origin_node_id,50)
    
    inG = inG.reverse()
    
    sG = nx.compose(outG,inG)
    
    # origin_node_id = "{}".format(activity_id.lower())
    
    #
    sG.node[origin_node_id]['type'] = 'origin'
    
    names = {}
    for n, nd in sG.nodes(data=True):
        if nd['type'] == 'activity' or nd['type'] == 'origin':
            label = nd['label']         
            names[n] = label
        else :
            names[n] = nd['label']
    
    nx.set_node_attributes(sG,'label', names)
    
     
    
    deg = nx.degree(sG)
    nx.set_node_attributes(sG,'degree',deg)
    

    assign_weights(sG, [])
            
            
    # print sG.edges(data=True)
    
    
    
    g_json = json_graph.node_link_data(sG) # node-link format to serialize

    start_nodes = 0
    end_nodes = 0
    max_degree = 1
    for n in sG.nodes():
        if sG.in_degree(n) == 0 :
            start_nodes += 1
        elif sG.out_degree(n) == 0 :
            end_nodes += 1
            
        if sG.in_degree(n) > max_degree :
            max_degree = sG.in_degree(n)
        if sG.out_degree(n) > max_degree :
            max_degree = sG.out_degree(n)
            
    # Initially set width to largest: number of start nodes vs. end nodes        
    if end_nodes > start_nodes :
        width = end_nodes
    else :
        width = start_nodes
        
    # But if the maximum degree exceeds that width, set the width to the max_degree
    if max_degree > width :
        width = max_degree
            
        # print sG.nodes(n)
    
    try:
        diameter = nx.diameter(sG.to_undirected())
    except Exception:
        app.logger.warning("Could not determine diameter, setting to arbitrary value of 25")
        emit("Could not determine diameter, setting to arbitrary value of 25")
        diameter = 25
    
    types = len(set(nx.get_node_attributes(sG,'type').values()))
    
    if types > 11:
        types = 11
    elif types < 3 :
        types = 3
    
    return g_json, width, types, diameter


def assign_weights(sG, next_nodes = []):
    emit("Assigning weights to nodes")
    weight_dict = {}
    new_next_nodes = []
    if next_nodes == []:
        for (s,t) in sG.edges():
            if sG.in_degree(s) == 0 :
                weight_dict[(s,t)] = log(10)
                next_nodes.append(t)
        # Loop!
        nx.set_edge_attributes(sG,'value',weight_dict)
        assign_weights(sG, next_nodes)
    else :
        for node in next_nodes :
            out_degree = sG.out_degree(node)
            
            if out_degree == 0 :
                continue
            
            incoming = sG.in_edges([node],data=True)
            
            accumulated_weight = 0
            for (s,t,data) in incoming :
                if data['value']:
                    accumulated_weight += data['value']
                
                
            out_weight = accumulated_weight/out_degree
            
            outgoing = sG.out_edges([node])
            
            for (s,t) in outgoing :
                weight_dict[(s,t)] = out_weight
                new_next_nodes.append(t)
        
        nx.set_edge_attributes(sG,'value',weight_dict)
        
        if new_next_nodes != [] :
            assign_weights(sG, new_next_nodes)
        else :
            return


def emit(message):
    socketio.emit('message',
                  {'data': message },
                  namespace='/log')


        
    
    
    

