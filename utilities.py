from __future__ import unicode_literals
from typing import List
import xml.etree.ElementTree as ET
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser.BpmnParser import BpmnParser
from SpiffWorkflow.bpmn.specs.events import StartEvent
from SpiffWorkflow.bpmn.specs.events import EndEvent
from SpiffWorkflow.bpmn.specs.ParallelGateway import ParallelGateway
from SpiffWorkflow.bpmn.specs.InclusiveGateway import InclusiveGateway
from SpiffWorkflow.specs.StartTask import StartTask
from timeit import default_timer as timer

import igraph as ig
import networkx as nx
import matplotlib.pyplot as plt
from tqdm import tqdm
import copy as cp
# @Author  : Rafael Fernandes (basask@collabo.com.br)
class BpmnGraphParser(object):

    def __init__(self, file_path: str, entrypoint=None):
        entrypoint = entrypoint or 'main_process'
        bpmn = ET.parse(file_path)
        self.parser = BpmnParser()
        self.parser.add_bpmn_xml(bpmn, filename=file_path)
        ##################################################
        try:
            self.spec = self.parser.get_spec(entrypoint)
        except Exception as e:
            entry_point_from_exception_message = str(e).split(':')[1].replace('?', '').strip()
            self.spec = self.parser.get_spec(entry_point_from_exception_message)
        ##################################################
        self.workflow = BpmnWorkflow(self.spec)
        self.graph = ig.Graph(directed=True)
        self.data = {}
        self.data_watch = True
        self.vertices = {}
        self.vertice_id = 0
        self.edges = {}
        self.edge_id = 0
        self.filename = file_path.split('/')[-1].split('.')[0]

    def set_data(self, data):
        self.data = data
        self.data_watch = True

    def get_start_task(self, task=None):
        task = task or self.workflow.task_tree
        if isinstance(task.task_spec, StartEvent):
            return task
        for subtask in task.children:
            subtask_child = self.get_start_task(subtask)
            if subtask_child:
                return subtask_child
        return None

    def get_tasks_node_ids(self, *tasks):
        try:
            return [self.vertices[task.task_spec.id] for task in tasks]
        except:
            pass

    def link_tasks(self, task_source, task_target, **kwargs):
        edge_ids = self.get_tasks_node_ids(task_source, task_target)
        if edge_ids:
            edge_signature = '{}-{}'.format(*edge_ids)
            if edge_signature not in self.edges.keys():
                self.graph.add_edge(edge_ids[0], edge_ids[1], **kwargs)
                edge_conf = dict(kwargs)
                edge_conf['source'] = edge_ids[0]
                edge_conf['target'] = edge_ids[1]
                self.edges[edge_signature] = edge_conf

            return self.edges[edge_signature]

    @staticmethod
    def get_task_type(task):
        if isinstance(task.task_spec, ParallelGateway):
            return 'split'
        if isinstance(task.task_spec, InclusiveGateway):
            return 'join'
        if isinstance(task.task_spec, StartEvent):
            return 'start'
        return 'task'

    def map_graph(self, task=None):
        task = task or self.get_start_task()
        if isinstance(task.task_spec, EndEvent):
            return

        if task.task_spec.id not in self.vertices.keys():

            task_data = self.data.get(task.get_name(), {})
            self.graph.add_vertex(
                self.get_task_type(task),
                type=self.get_task_type(task),
                domain=task.task_spec.lane or 'default',
                id=self.vertice_id,
                label=f"{self.filename}_{self.vertice_id}",
                parameters=task_data.get('parameters', {})
            )
            self.vertices[task.task_spec.id] = self.vertice_id
            self.vertice_id += 1

        
        if not isinstance(task.task_spec, StartTask):
            self.link_tasks(task.parent, task)
        
        for child in task.children:
            self.map_graph(child)

    def get_graph(self, data=None):

        if data:
            self.set_data(data)

        if self.data_watch:
            self.map_graph()
            self.data_watch = False

        return self.graph