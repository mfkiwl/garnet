import metamapper.coreir_util as cutil
from metamapper.common_passes import VerifyNodes, print_dag
from metamapper import CoreIRContext
from metamapper.irs.coreir import gen_CoreIRNodes
from metamapper.node import Nodes, Constant
import pytest
from metamapper.coreir_mapper import Mapper
import metamapper.peak_util as putil
from hwtypes import BitVector, Bit
from hwtypes.adt import Tuple
from lassen import PE_fc as lassen_fc

from DagVisitor import Visitor

class CreateNetlist(Visitor):

    def __init__(self, node_info):
        self.node_info = node_info

    #Translate an ADT to a dictionary of names and widths
    def T_to_nets(self, T, input=False):
        print(T)
        if T is BitVector[16]:
            net_id = f"e{self.net_id}"
            self.net_to_sp[net_id] = []
            self.buses[net_id] = 16
            self.net_id += 1
            if input:
                I_id = f"I{self.node_id}"
                self.node_id +=1
                self.net_to_id[net_id] = I_id
                self.net_to_sp[net_id].append((I_id, "io2f_16"))
            return net_id
        elif T is Bit:
            net_id = f"e{self.net_id}"
            self.net_to_sp[net_id] = []
            self.buses[net_id] = 1
            self.net_id += 1
            if input:
                I_id = f"i{self.node_id}"
                self.node_id +=1
                self.net_to_id[net_id] = I_id
                self.net_to_sp[net_id].append((I_id, "io2f_1"))
            return net_id
        elif issubclass(T, Tuple):
            d = {}
            for i, subT in T.field_dict.items():
                d[i] = self.T_to_nets(subT, input)
            return d
        else:
            raise NotImplementedError(str(T))

    def doit(self, dag):
        print_dag(dag)
        self.net_id = 0
        self.node_id = 0

        self.buses = {}
        self.node_to_nets = {} #Recursive structure on select paths
        self.net_to_id = {}
        self.node_to_id = {}
        self.net_to_sp = {}
        self.run(dag)


        #Filter out unused nets ('net_to_sp' needs > 1 entry)
        for e in list(self.net_to_sp.keys()):
            if len(self.net_to_sp[e]) < 2:
                del self.net_to_sp[e]
                del self.buses[e]
        breakpoint()
        return dict(
            id_to_instr=None,
            inst_to_instr=None,
            netlist=self.net_to_sp,
            buses=self.buses,
            node_to_id=self.node_to_id,
            net_to_id=self.net_to_id
        )

    def generic_visit(self, node):
        Visitor.generic_visit(self, node)

        # Create a node_id
        if type(node) not in self.node_info:
            raise ValueError(f"Cannot handle {node}, not in {self.node_info}")
        node_id = f"{self.node_info[type(node)]}{self.node_id}"
        self.node_to_id[node] = node_id
        self.node_id += 1

        # Get the child name -> nets
        fields = list(node.nodes.peak_nodes[node.node_name].Py.input_t.field_dict)
        for field, child in zip(fields, node.children()):
            if isinstance(child, Constant):
                continue
            net_id = self.node_to_nets[child]
            self.net_to_sp[net_id].append((node_id, field))

        #Create output nets and add to net_to_sp
        net_info = self.T_to_nets(node.type)
        self.node_to_nets[node] = net_info
        for field, net_id in net_info.items():
            assert isinstance(net_id, str)
            self.net_to_sp[net_id].append((node_id, field))
            self.net_to_id[net_id] = node_id

    def visit_Input(self, node):
        net_info = self.T_to_nets(node.type, input=True)
        self.node_to_nets[node] = net_info


    def visit_Select(self, node):
        Visitor.generic_visit(self, node)
        child = node.children()[0]
        n2n = self.node_to_nets[child]
        self.node_to_nets[node] = n2n[node.field]

    def visit_Constant(self, node):
        pass

    def visit_Output(self, node):
        Visitor.generic_visit(self, node)
        for (field, T), child in zip(node.type.field_dict.items(), node.children()):
            net_id = self.node_to_nets[child]
            node_id = f"I{self.node_id}"
            self.node_id += 1
            self.net_to_sp[net_id].append((node_id, "f2io_16"))
            self.net_to_id[net_id] = node_id
