import argparse
from gemstone.common.testers import BasicTester
from gemstone.common.configurable import ConfigurationType
from pydot import Graph
from cgra.util import create_cgra
from memory_core.buffet_core import BuffetCore
from memory_core.fake_pe_core import FakePECore
from memory_core.intersect_core import IntersectCore
from memory_core.io_core_rv import IOCoreReadyValid
from memory_core.lookup_core import LookupCore
from memory_core.repeat_core import RepeatCore
from memory_core.repeat_signal_generator_core import RepeatSignalGeneratorCore
from memory_core.memtile_util import NetlistBuilder
from memory_core.reg_core import RegCore
from memory_core.scanner_core import ScannerCore
from memory_core.write_scanner_core import WriteScannerCore
from sam.onyx.parse_dot import *
from sam.onyx.hw_nodes.hw_node import *
from sam.onyx.hw_nodes.memory_node import MemoryNode
from sam.onyx.hw_nodes.broadcast_node import BroadcastNode
from sam.onyx.hw_nodes.compute_node import ComputeNode
from sam.onyx.hw_nodes.glb_node import GLBNode
from sam.onyx.hw_nodes.buffet_node import BuffetNode
from sam.onyx.hw_nodes.read_scanner_node import ReadScannerNode
from sam.onyx.hw_nodes.write_scanner_node import WriteScannerNode
from sam.onyx.hw_nodes.intersect_node import IntersectNode
from sam.onyx.hw_nodes.reduce_node import ReduceNode
from sam.onyx.hw_nodes.lookup_node import LookupNode
from sam.onyx.hw_nodes.merge_node import MergeNode
from sam.onyx.hw_nodes.repeat_node import RepeatNode
from sam.onyx.hw_nodes.repsiggen_node import RepSigGenNode
import magma as m
import kratos
import _kratos
from lake.modules.glb_write import GLBWrite
from lake.modules.glb_read import GLBRead
from lake.modules.buffet_like import BuffetLike
from lake.top.lake_top import LakeTop
from lake.modules.repeat import Repeat
from lake.modules.repeat_signal_generator import RepeatSignalGenerator
from lake.modules.scanner import Scanner
from lake.modules.write_scanner import WriteScanner
from lake.modules.pe import PE
from lake.modules.intersect import Intersect
from lake.modules.reg_cr import Reg
import os
from canal.util import IOSide
from io_core.io_core_magma import IOCoreValid, IOCore


class SparseTBBuilder(m.Generator2):
    def __init__(self, nlb: NetlistBuilder = None, graph: Graph = None, bespoke=False, output_dir=None, local_mems=True) -> None:
        assert nlb is not None or bespoke is True, "NLB is none..."
        assert graph is not None, "Graph is none..."

        self.nlb = nlb
        self.graph = graph
        self.core_nodes = {}
        self.glb_dones = []
        self.bespoke = bespoke
        self.core_gens = {}
        self.name_maps = {}
        self.output_dir = output_dir
        self.local_mems = local_mems

        self._ctr = 0

        if bespoke is False:
            self.io = m.IO(
                clk=m.In(m.Clock),
                rst_n=m.In(m.AsyncReset),
                stall=m.In(m.Bit),
                flush=m.In(m.Bit),
                config=m.In(ConfigurationType(32, 32)),
                done=m.Out(m.Bit)
            )

            # CGRA Path
            self.register_cores()
            self.connect_cores()
            # Add flush connection
            flush_in = self.nlb.register_core("io_1", name="flush_in")
            self.nlb.add_connections(connections=self.nlb.emit_flush_connection(flush_in))
            self.nlb.get_route_config()

            self.configure_cores()

            # self.config = self.io.config
            # Now we have the configured CGRA...
            self.nlb.finalize_config()

            # Now attach global buffers based on placement...
            # Get circuit
            self.interconnect_circuit = self.nlb.get_circuit()
            self.interconnect_circuit = self.interconnect_circuit()

            flush_h = self.nlb.get_handle(flush_in, prefix="glb2io_1_")

            m.wire(self.interconnect_circuit['clk'], self.io.clk)
            m.wire(self.io.rst_n, self.interconnect_circuit['reset'])
            m.wire(self.io.stall, self.interconnect_circuit['stall'][0])
            # m.wire(self.io.flush, self.interconnect_circuit['flush'][0])
            # print(str(flush_h))
            m.wire(self.io.flush, self.interconnect_circuit[str(flush_h)][0])

            m.wire(self.interconnect_circuit.config, self.io.config)

            # Get the initial list of inputs to interconnect and cross them off
            self.interconnect_ins = self.get_interconnect_ins()
            # Make sure to remove the flush port or it will get grounded.
            self.interconnect_ins.remove(str(flush_h))

        else:

            self.io = m.IO(
                clk=m.In(m.Clock),
                rst_n=m.In(m.AsyncReset),
                stall=m.In(m.Bit),
                flush=m.In(m.Bit),
                done=m.Out(m.Bit)
            )

            # Custom circuit path

            # First need to instantiate all the children
            self.fabric = kratos.Generator(name='fabric_proxy')
            self._u_clk = self.fabric.clock("clk")
            self._u_rst_n = self.fabric.reset("rst_n")
            self._u_flush = self.fabric.input("flush", 1)
            self._u_clk_en = self.fabric.input("stall", 1)
            self.build_fabric()
            self.wire_fabric()
            self.configure_cores()
            self.add_clk_reset()
            self.zero_alt_inputs()

            # Now we want to magma-ize this
            self.wrap_circ = kratos.util.to_magma(self.fabric,
                                                  flatten_array=False,
                                                  check_multiple_driver=False,
                                                  optimize_if=False,
                                                  check_flip_flop_always_ff=False)

            # Instance it!
            self.wrap_circ = self.wrap_circ()

            m.wire(self.io.clk, self.wrap_circ.clk)
            m.wire(self.io.rst_n, self.wrap_circ.rst_n)
            m.wire(self.io.stall, self.wrap_circ.stall[0])
            m.wire(self.io.flush, self.wrap_circ.flush[0])
            # m.wire(self.interconnect_circuit.config, self.io.config)

        self.attach_glb()

        # AND together all the dones
        if len(self.glb_dones) == 1:
            m.wire(self.io.done, self.glb_dones[0])
        else:
            tmp = self.glb_dones[0]
            for i in range(len(self.glb_dones) - 1):
                tmp = tmp & self.glb_dones[i + 1]
            m.wire(self.io.done, tmp)

        if self.bespoke is False:
            self.wire_interconnect_ins()

    def zero_alt_inputs(self):
        '''
        Go through each child instance and zero their untouched inputs
        '''
        children = self.fabric.child_generator()
        for child in children:
            for cp in self.fabric[child].ports:
                actual_port = self.fabric[child].ports[cp]
                # print(actual_port)
                # print(actual_port.sources)
                # print(actual_port.sinks)
                # print(actual_port.width)
                sourced_mask = [0 for i in range(actual_port.width)]
                if str(actual_port.port_direction) == "PortDirection.In" and str(actual_port.port_type) == "PortType.Data":
                    # If no sources, wire to 0 unless it's a ready path, then wire each bit to 1
                    if len(actual_port.sources) == 0:
                        if 'ready' in actual_port.name:
                            for i in range(actual_port.width):
                                self.fabric.wire(actual_port[i], kratos.const(1, 1))
                        else:
                            self.fabric.wire(actual_port, kratos.const(0, actual_port.width))
                    elif len(actual_port.sources) != 0 and actual_port.width != 1 and actual_port.width != 16:
                        # If there are sources and it's not 1 or 16 wide (implies they are fully driven anyway),
                        # then we need to dissect them
                        try:
                            for p in actual_port.sources:
                                # print(actual_port.port_type)
                                for i in range(p.left.high + 1 - p.left.low):
                                    sourced_mask[i + p.left.low] = 1
                            for i in range(len(sourced_mask)):
                                if sourced_mask[i] == 0:
                                    val = 0
                                    if 'ready' in actual_port.name:
                                        val = 1
                                    self.fabric.wire(actual_port[i], kratos.const(val, 1))
                        except AttributeError:
                            print(f"Couldn't get bit slice, must be fully driven...{actual_port.name}")

    def add_clk_reset(self):
        '''
        Go through each child instance wire up clk, rst_n, flush, clk_en
        '''
        children = self.fabric.child_generator()
        for child in children:
            # print(child)
            self.fabric.wire(self._u_clk, self.fabric[child].ports['clk'])
            self.fabric.wire(self._u_rst_n, self.fabric[child].ports['rst_n'])
            self.fabric.wire(self._u_flush, self.fabric[child].ports['flush'])
            self.fabric.wire(self._u_clk_en, self.fabric[child].ports['clk_en'])

    def wire_fabric(self):
        '''
        Bespoke way of connecting all the blocks in the underlying fabric
        '''
        children = self.fabric.child_generator()
        edges = self.graph.get_edges()
        for edge in edges:
            src = edge.get_source()
            dst = edge.get_destination()
            src_name = src
            dst_name = dst
            # src_inst = self.fabric.children[src_name]
            # dst_inst = self.fabric.children[dst_name]
            addtl_conns = self.core_nodes[src_name].connect(self.core_nodes[dst_name], edge)

            # Need to automatically add in the ready/valid interface in the bespoke case...
            if addtl_conns is not None:
                for c_b, c_l in addtl_conns.items():
                    c_l_init_length = len(c_l)
                    for i in range(c_l_init_length):
                        curr_conn = c_l[i]
                        # TODO: Handle forked connection
                        conn_spec, _ = curr_conn
                        src_c, dst_c = conn_spec
                        src_n, src_s = src_c
                        dst_n, dst_s = dst_c
                        if 'io2f' in src_s or 'f2io' in dst_s:
                            pass
                        else:
                            addtl_conns[c_b].append(([(src_n, f'{src_s}_valid'), (dst_n, f'{dst_s}_valid')], 1))
                            addtl_conns[c_b].append(([(dst_n, f'{dst_s}_ready'), (src_n, f'{src_s}_ready')], 1))

            if addtl_conns is not None:
                conn_list = None
                for conn_block, cl in addtl_conns.items():
                    conn_list = cl
                for addtl_conn in conn_list:
                    # print(addtl_conn)
                    # Now wire them up
                    conn_des, width = addtl_conn

                    conn_src, conn_src_prt = conn_des[0]
                    for i in range(len(conn_des) - 1):
                        # conn_dst, conn_dst_prt = conn_des[1]
                        conn_dst, conn_dst_prt = conn_des[i + 1]

                        if type(conn_src) is _kratos.Port:
                            wire_use_src = conn_src
                        else:
                            conn_src_inst = children[conn_src]
                            try:
                                wire_use_src = conn_src_inst.ports[conn_src_prt]
                            except AttributeError:
                                tk = conn_src_prt.split('_')
                                idx_str = tk[-1]
                                new_port = conn_src_prt.rstrip(f"_{idx_str}")
                                wire_use_src = conn_src_inst.ports[new_port][int(idx_str)]

                        if type(conn_dst) is _kratos.Port:
                            wire_use_dst = conn_dst
                        else:
                            conn_dst_inst = children[conn_dst]
                            try:
                                # print(conn_dst_inst.ports)
                                wire_use_dst = conn_dst_inst.ports[conn_dst_prt]
                            #     # wire_use_src = conn_src_inst.ports[conn_src_prt]
                            except AttributeError:
                                tk = conn_dst_prt.split('_')
                                idx_str = tk[-1]
                                new_port = conn_dst_prt.rstrip(f"_{idx_str}")
                                wire_use_dst = conn_dst_inst.ports[new_port][int(idx_str)]

                        if 'valid_out_18' in wire_use_dst.name or 'valid_out_18' in wire_use_src.name:
                            print("MEK")
                            print("MEK")
                            print("MEK")
                            print("MEK")

                            print(wire_use_src)
                            print(wire_use_dst)

                        self.fabric.wire(wire_use_src, wire_use_dst)

    def build_fabric(self):
        '''
        Go through each node and instantiate the required resources
        '''
        # print(self.core_nodes)

        self.__cache_gens = {}

        for node in self.graph.get_nodes():
            kwargs = {}
            hw_node_type = node.get_attributes()['hwnode']
            new_node_type = None
            core_name = None
            core_inst = None
            new_name = node.get_attributes()['label']
            # print(node.get_attributes())
            if hw_node_type == f"{HWNodeType.GLB}":
                new_node_type = GLBNode
                core_name = "glb"
            elif hw_node_type == f"{HWNodeType.Buffet}":
                new_node_type = BuffetNode
                core_name = "buffet"
                core_inst = BuffetLike(local_memory=self.local_mems)
            elif hw_node_type == f"{HWNodeType.Memory}":
                new_node_type = MemoryNode
                core_name = "memtile"
                # if 'lake' in self.__cache_gens:
                #     core_inst = self.__cache_gens['lake']
                # else:
                #     core_inst = LakeTop()
                #     self.__cache_gens['lake'] = core_inst
                core_inst = LakeTop()
            elif hw_node_type == f"{HWNodeType.ReadScanner}":
                new_node_type = ReadScannerNode
                core_name = "scanner"
                tensor = node.get_attributes()['tensor'].strip('"')
                kwargs = {'tensor': tensor}
                core_inst = Scanner()
            elif hw_node_type == f"{HWNodeType.WriteScanner}":
                new_node_type = WriteScannerNode
                core_name = "write_scanner"
                core_inst = WriteScanner()
            # Can't explain this but it's not a string when it's intersect?
            elif hw_node_type == f"{HWNodeType.Intersect}" or hw_node_type == HWNodeType.Intersect:
                new_node_type = IntersectNode
                core_name = "intersect"
                core_inst = Intersect(use_merger=False)
            elif hw_node_type == f"{HWNodeType.Reduce}":
                new_node_type = ReduceNode
                core_name = "regcore"
                core_inst = Reg()
            elif hw_node_type == f"{HWNodeType.Lookup}":
                new_node_type = LookupNode
                core_name = "lookup"
            elif hw_node_type == f"{HWNodeType.Merge}" or hw_node_type == HWNodeType.Merge:
                new_node_type = MergeNode
                core_name = "intersect"
                outer = node.get_attributes()['outer'].strip('"')
                inner = node.get_attributes()['inner'].strip('"')
                kwargs = {
                    "outer": outer,
                    "inner": inner
                }
                core_inst = Intersect(use_merger=True)
            elif hw_node_type == f"{HWNodeType.Repeat}" or hw_node_type == HWNodeType.Repeat:
                new_node_type = RepeatNode
                core_name = "repeat"
                core_inst = Repeat()
            elif hw_node_type == f"{HWNodeType.Compute}" or hw_node_type == HWNodeType.Compute:
                new_node_type = ComputeNode
                core_name = "fake_pe"
                core_inst = PE()
            # elif hw_node_type == f"{HWNodeType.Broadcast}":
                # new_node = GLBNode()
            elif hw_node_type == f"{HWNodeType.RepSigGen}" or hw_node_type == HWNodeType.RepSigGen:
                new_node_type = RepSigGenNode
                core_name = "repeat_signal_generator"
                core_inst = RepeatSignalGenerator()
            else:
                raise NotImplementedError(f"{hw_node_type} not supported....")

            assert new_node_type is not None
            assert core_name != ""
            # print(node.get_attributes()['type'])
            if new_node_type == GLBNode:
                conn_id = self.get_next_seq()
                # Have to handle the GLB nodes slightly differently
                # Instead of directly registering a core, we are going to register the io,
                # connect them to the appropriate block, then instantiate and wire a
                # systemverilog wrapper of the simulation level transactions for GLB
                if node.get_attributes()['type'].strip('"') == 'fiberlookup':
                    # GLB write wants a data input, ready, valid
                    glb_name = "GLB_TO_CGRA"
                    direction = "write"
                    num_blocks = 1
                    file_number = 0
                    # data = self.nlb.register_core("io_16", name="data_in_")
                    # ready = self.nlb.register_core("io_1", name="ready_out_")
                    # valid = self.nlb.register_core("io_1", name="valid_in_")
                    data = self.fabric.input(f'data_in_{conn_id}', 17)
                    ready = self.fabric.output(f'ready_out_{conn_id}', 1)
                    valid = self.fabric.input(f'valid_in_{conn_id}', 1)
                    tx_size = 7
                    if node.get_attributes()['mode'].strip('"') == 1 or node.get_attributes()['mode'].strip('"') == '1':
                        file_number = 1
                        tx_size = 12
                    # glb_writer = m.define_from_verilog_file()
                elif node.get_attributes()['type'].strip('"') == 'fiberwrite':
                    # GLB read wants a data output, ready, valid
                    direction = "read"
                    glb_name = "CGRA_TO_GLB"
                    # print(node.get_attributes())
                    # print(node.get_attributes()['mode'].strip('"'))
                    # data = self.nlb.register_core("io_16", name="data_out_")
                    # ready = self.nlb.register_core("io_1", name="ready_in_")
                    # valid = self.nlb.register_core("io_1", name="valid_out_")
                    data = self.fabric.output(f'data_out_{conn_id}', 17)
                    ready = self.fabric.input(f'ready_in_{conn_id}', 1)
                    if conn_id == 18:
                        print("HELLO")
                    valid = self.fabric.output(f'valid_out_{conn_id}', 1)
                    if 'vals' in node.get_attributes()['mode'].strip('"'):
                        # print("NUM 1")
                        num_blocks = 1
                    else:
                        # print("NUM 2")
                        num_blocks = 2
                    tx_size = 1
                elif node.get_attributes()['type'].strip('"') == 'arrayvals':
                    # GLB write wants a data input, ready, valid
                    glb_name = "GLB_TO_CGRA"
                    data = self.fabric.input(f'data_in_{conn_id}', 17)
                    ready = self.fabric.output(f'ready_out_{conn_id}', 1)
                    valid = self.fabric.input(f'valid_in_{conn_id}', 1)
                    # data = self.nlb.register_core("io_16", name="data_in_")
                    # ready = self.nlb.register_core("io_1", name="ready_out_")
                    # valid = self.nlb.register_core("io_1", name="valid_in_")
                    direction = "write"
                    num_blocks = 1
                    tx_size = 7
                    file_number = 2
                else:
                    raise NotImplementedError
                self.core_nodes[node.get_name()] = GLBNode(name=glb_name,
                                                           data=data,
                                                           valid=valid,
                                                           ready=ready,
                                                           direction=direction,
                                                           num_blocks=num_blocks,
                                                           file_number=file_number,
                                                           tx_size=tx_size,
                                                           IO_id=self.get_next_seq(),
                                                           bespoke=True)
            else:
                # reg_ret = self.nlb.register_core(core_tag, flushable=True, name=new_name)
                inst_name = f"{core_name}_{self.get_next_seq()}"
                self.name_maps[inst_name] = node.get_attributes()['label'].strip('"')
                self.core_nodes[node.get_name()] = new_node_type(name=inst_name, **kwargs)
                # Need to flatten first - but not if memory tile because of some bad code
                if new_node_type == MemoryNode:
                    self.core_gens[node.get_name()] = core_inst.dut
                    self.fabric.add_child(inst_name, core_inst.dut)
                else:
                    self.core_gens[node.get_name()] = core_inst
                    flattened = _kratos.create_wrapper_flatten(core_inst.internal_generator, f"{core_inst.name}_flat")
                    flattened_gen = kratos.Generator(f"{core_inst.name}_flat", internal_generator=flattened)
                    self.fabric.add_child(inst_name, flattened_gen)

    def get_next_seq(self):
        tmp = self._ctr
        self._ctr += 1
        return tmp

    def get_interconnect_ins(self):
        '''
        Need to ascertain all inputs to interconnect so we can later make sure they are driven
        Want to do this early so we can delete references while processing the glb attachments
        '''
        in_list = []

        all_ports = self.interconnect_circuit.interface
        # print(all_ports)
        for port in all_ports:
            # print(port)
            if 'glb2io' in port:
                in_list.append(port)

        return in_list

    def wire_interconnect_ins(self):
        '''
        Here we are going to wire all of the relevant interconnect inputs to 0
        '''
        for ic_in in self.interconnect_ins:
            # Get width from name
            width = int(ic_in.split("_")[1])
            m.wire(self.interconnect_circuit[ic_in], m.Bits[width](0))

    def attach_glb(self):

        self._all_dones = []

        glb_nodes = [node for node in self.core_nodes.values() if type(node) == GLBNode]
        # print(glb_nodes)
        if len(glb_nodes) < 3:
            print('STOPPING')
            exit()
        for node in glb_nodes:
            # Now we can realize and connect the glb nodes based on the placement
            glb_data = node.get_data()
            glb_ready = node.get_ready()
            glb_valid = node.get_valid()
            glb_num_blocks = node.get_num_blocks()
            glb_file_number = node.get_file_number()
            glb_tx_size = node.get_tx_size()

            # Get the handle for these pins, then instantiate glb
            glb_dir = node.get_direction()
            if glb_dir == 'write':

                # In the bespoke case we can use the data ports
                if self.bespoke:
                    data_h = self.wrap_circ[glb_data.name]
                    ready_h = self.wrap_circ[glb_ready.name]
                    valid_h = self.wrap_circ[glb_valid.name]
                else:
                    data_h = self.nlb.get_handle(glb_data, prefix="glb2io_16_")
                    # ready_h = self.nlb.get_handle(glb_ready, prefix="io2glb_1_")
                    # valid_h = self.nlb.get_handle(glb_valid, prefix="glb2io_1_")

                    # Get rid of these signals from leftover inputs...
                    self.interconnect_ins.remove(str(data_h))
                    self.interconnect_ins.remove(str(valid_h))

                    data_h = self.interconnect_circuit[str(data_h)]
                    ready_h = self.interconnect_circuit[str(ready_h)]
                    valid_h = self.interconnect_circuit[str(valid_h)]

                class _Definition(m.Generator2):
                    def __init__(self, TX_SIZE, FILE_NAME, ID_no) -> None:
                        # super().__init__()
                        self.name = f"glb_write_wrapper_{TX_SIZE}_{ID_no}"
                        self.io = m.IO(**{
                            "clk": m.In(m.Clock),
                            "rst_n": m.In(m.AsyncReset),
                            "data": m.Out(m.Bits[17]),
                            "ready": m.In(m.Bit),
                            "valid": m.Out(m.Bit),
                            "done": m.Out(m.Bit),
                            "flush": m.In(m.Bit)
                        })
                        self.verilog = f"""
                glb_write  #(.TX_SIZE({TX_SIZE}), .FILE_NAME({FILE_NAME}))
                test_glb_inst
                (
                    .clk(clk),
                    .rst_n(rst_n),
                    .data(data),
                    .ready(ready),
                    .valid(valid),
                    .done(done),
                    .flush(flush)
                );
                """

                file_full = f"\"/home/max/Documents/SPARSE/garnet/generic_memory_{glb_file_number}.txt\""
                test_glb = _Definition(TX_SIZE=glb_tx_size, FILE_NAME=file_full, ID_no=self.get_next_seq())()

                m.wire(test_glb['data'], data_h)
                m.wire(ready_h[0], test_glb['ready'])
                m.wire(test_glb['valid'], valid_h[0])
                m.wire(test_glb.clk, self.io.clk)
                m.wire(test_glb.rst_n, self.io.rst_n)
                m.wire(test_glb.flush, self.io.flush)

            elif glb_dir == 'read':

                if self.bespoke:
                    data_h = self.wrap_circ[glb_data.name]
                    ready_h = self.wrap_circ[glb_ready.name]
                    valid_h = self.wrap_circ[glb_valid.name]
                else:
                    data_h = self.nlb.get_handle(glb_data, prefix="io2glb_16_")
                    # ready_h = self.nlb.get_handle(glb_ready, prefix="glb2io_1_")
                    # valid_h = self.nlb.get_handle(glb_valid, prefix="io2glb_1_")

                    # Get rid of this signal from leftover inputs...
                    self.interconnect_ins.remove(str(ready_h))

                    data_h = self.interconnect_circuit[str(data_h)]
                    ready_h = self.interconnect_circuit[str(ready_h)]
                    valid_h = self.interconnect_circuit[str(valid_h)]

                class _Definition(m.Generator2):
                    def __init__(self, NUM_BLOCKS, FILE_NAME1, FILE_NAME2, ID_no) -> None:
                        # super().__init__()
                        self.name = f"glb_read_wrapper_{NUM_BLOCKS}_{ID_no}"
                        self.io = m.IO(**{
                            "clk": m.In(m.Clock),
                            "rst_n": m.In(m.AsyncReset),
                            "data": m.In(m.Bits[17]),
                            "ready": m.Out(m.Bit),
                            "valid": m.In(m.Bit),
                            "done": m.Out(m.Bit),
                            "flush": m.In(m.Bit)
                        })

                        self.verilog = f"""
                glb_read #(.NUM_BLOCKS({NUM_BLOCKS}), .FILE_NAME1({FILE_NAME1}), .FILE_NAME2({FILE_NAME2}))
                test_glb_inst
                (
                    .clk(clk),
                    .rst_n(rst_n),
                    .data(data),
                    .ready(ready),
                    .valid(valid),
                    .done(done),
                    .flush(flush)
                );
                """

                ID_no = self.get_next_seq()
                f1 = f"\"{self.output_dir}/generic_memory_out_id_{ID_no}_block_0.txt\""
                # f1 = f"\"/home/max/Documents/SPARSE/garnet/generic_memory_out_id_{ID_no}_block_0.txt\""
                f2 = f"\"{self.output_dir}/generic_memory_out_id_{ID_no}_block_1.txt\""
                # f2 = f"\"/home/max/Documents/SPARSE/garnet/generic_memory_out_id_{ID_no}_block_1.txt\""

                test_glb = _Definition(NUM_BLOCKS=glb_num_blocks, FILE_NAME1=f1, FILE_NAME2=f2, ID_no=ID_no)()

                m.wire(data_h, test_glb['data'])
                m.wire(test_glb['ready'], ready_h[0])
                m.wire(valid_h[0], test_glb['valid'])
                m.wire(test_glb.clk, self.io.clk)
                m.wire(test_glb.rst_n, self.io.rst_n)
                m.wire(test_glb.flush, self.io.flush)
            else:
                raise NotImplementedError(f"glb_dir was {glb_dir}")

            self.glb_dones.append(test_glb.done)

    def register_cores(self):
        '''
        Go through each core and register it, also add it to dict of core nodes
        '''

        for node in self.graph.get_nodes():
            kwargs = {}
            hw_node_type = node.get_attributes()['hwnode']
            new_node_type = None
            core_tag = None
            new_name = node.get_attributes()['label']
            # print(node.get_attributes())
            if hw_node_type == f"{HWNodeType.GLB}":
                new_node_type = GLBNode
                core_tag = "glb"
            elif hw_node_type == f"{HWNodeType.Buffet}":
                new_node_type = BuffetNode
                core_tag = "buffet"
            elif hw_node_type == f"{HWNodeType.Memory}":
                new_node_type = MemoryNode
                core_tag = "memtile"
            elif hw_node_type == f"{HWNodeType.ReadScanner}":
                new_node_type = ReadScannerNode
                core_tag = "scanner"
                tensor = node.get_attributes()['tensor'].strip('"')
                kwargs = {'tensor': tensor}
            elif hw_node_type == f"{HWNodeType.WriteScanner}":
                new_node_type = WriteScannerNode
                core_tag = "write_scanner"
            # Can't explain this but it's not a string when it's intersect?
            elif hw_node_type == f"{HWNodeType.Intersect}" or hw_node_type == HWNodeType.Intersect:
                new_node_type = IntersectNode
                core_tag = "intersect"
            elif hw_node_type == f"{HWNodeType.Reduce}":
                new_node_type = ReduceNode
                core_tag = "regcore"
            elif hw_node_type == f"{HWNodeType.Lookup}":
                new_node_type = LookupNode
                core_tag = "lookup"
            elif hw_node_type == f"{HWNodeType.Merge}" or hw_node_type == HWNodeType.Merge:
                new_node_type = MergeNode
                core_tag = "intersect"
                outer = node.get_attributes()['outer'].strip('"')
                inner = node.get_attributes()['inner'].strip('"')
                kwargs = {
                    "outer": outer,
                    "inner": inner
                }
            elif hw_node_type == f"{HWNodeType.Repeat}" or hw_node_type == HWNodeType.Repeat:
                new_node_type = RepeatNode
                core_tag = "repeat"
            elif hw_node_type == f"{HWNodeType.Compute}" or hw_node_type == HWNodeType.Compute:
                new_node_type = ComputeNode
                core_tag = "fake_pe"
            # elif hw_node_type == f"{HWNodeType.Broadcast}":
                # new_node = GLBNode()
            elif hw_node_type == f"{HWNodeType.RepSigGen}" or hw_node_type == HWNodeType.RepSigGen:
                new_node_type = RepSigGenNode
                core_tag = "repeat_signal_generator"
            else:
                raise NotImplementedError(f"{hw_node_type} not supported....")

            assert new_node_type is not None
            assert core_tag != ""
            # print(node.get_attributes()['type'])
            if new_node_type == GLBNode:
                # Have to handle the GLB nodes slightly differently
                # Instead of directly registering a core, we are going to register the io,
                # connect them to the appropriate block, then instantiate and wire a
                # systemverilog wrapper of the simulation level transactions for GLB
                if node.get_attributes()['type'].strip('"') == 'fiberlookup':
                    # GLB write wants a data input, ready, valid
                    glb_name = "GLB_TO_CGRA"
                    data = self.nlb.register_core("io_16", name="data_in_")
                    ready = self.nlb.register_core("io_1", name="ready_out_")
                    valid = self.nlb.register_core("io_1", name="valid_in_")
                    direction = "write"
                    num_blocks = 1
                    file_number = 0
                    tx_size = 7
                    if node.get_attributes()['mode'].strip('"') == 1 or node.get_attributes()['mode'].strip('"') == '1':
                        file_number = 1
                        tx_size = 12
                    # glb_writer = m.define_from_verilog_file()
                elif node.get_attributes()['type'].strip('"') == 'fiberwrite':
                    # GLB read wants a data output, ready, valid
                    data = self.nlb.register_core("io_16", name="data_out_")
                    ready = self.nlb.register_core("io_1", name="ready_in_")
                    valid = self.nlb.register_core("io_1", name="valid_out_")
                    direction = "read"
                    glb_name = "CGRA_TO_GLB"
                    # print(node.get_attributes())
                    # print(node.get_attributes()['mode'].strip('"'))
                    if 'vals' in node.get_attributes()['mode'].strip('"'):
                        # print("NUM 1")
                        num_blocks = 1
                    else:
                        # print("NUM 2")
                        num_blocks = 2
                    tx_size = 1
                elif node.get_attributes()['type'].strip('"') == 'arrayvals':
                    # GLB write wants a data input, ready, valid
                    glb_name = "GLB_TO_CGRA"
                    data = self.nlb.register_core("io_16", name="data_in_")
                    ready = self.nlb.register_core("io_1", name="ready_out_")
                    valid = self.nlb.register_core("io_1", name="valid_in_")
                    direction = "write"
                    num_blocks = 1
                    tx_size = 7
                    file_number = 2
                else:
                    raise NotImplementedError
                self.core_nodes[node.get_name()] = GLBNode(name=glb_name,
                                                           data=data,
                                                           valid=valid,
                                                           ready=ready,
                                                           direction=direction,
                                                           num_blocks=num_blocks,
                                                           file_number=file_number,
                                                           tx_size=tx_size)
            else:
                reg_ret = self.nlb.register_core(core_tag, flushable=True, name=new_name)
                self.core_nodes[node.get_name()] = new_node_type(name=reg_ret, **kwargs)

    def connect_cores(self):
        '''
        Iterate through the edges of the graph and connect each core up
        '''
        # self.display_names()
        edges = self.graph.get_edges()
        for edge in edges:
            src = edge.get_source()
            dst = edge.get_destination()
            src_name = src
            dst_name = dst
            addtl_conns = self.core_nodes[src_name].connect(self.core_nodes[dst_name], edge)
            if addtl_conns is not None:
                self.nlb.add_connections(addtl_conns, defer_placement=True)

    def configure_cores(self):
        '''
        Go through nodes and configure each based on the attributes...
        '''
        for node in self.graph.get_nodes():
            node_attr = node.get_attributes()
            # print(node)
            # print(node_attr)
            node_config_ret = self.core_nodes[node.get_name()].configure(node_attr)
            if node_config_ret is not None:
                node_config_tuple, node_config_kwargs = node_config_ret
            # GLB tiles return none so that we don't try to config map them...
            if self.bespoke:
                if node_attr['hwnode'] == 'HWNodeType.GLB':
                    # print("SAW GLB...skipping")
                    continue
                node_name = node.get_name()
                # node_inst = self.fabric[self.core_gens[node_name].get_name()]
                node_inst = self.core_gens[node_name]
                # print(node_inst)
                if node_attr['hwnode'] == 'HWNodeType.Memory':
                    node_cfg = node_inst.get_bitstream(node_config_kwargs)
                else:
                    node_cfg = node_inst.get_bitstream(**node_config_kwargs)
                # Now for the configurations, wire them directly
                # print(node_cfg)
                for cfg_port, cfg_val in node_cfg:
                    # Now we need the flattened wrapper/actually used instance
                    child_inst = self.fabric[self.core_nodes[node.get_name()].get_name()]
                    self.fabric.wire(child_inst.ports[cfg_port], kratos.const(cfg_val, child_inst.ports[cfg_port].width))

            else:
                if node_attr['hwnode'] == 'HWNodeType.GLB':
                    # print("SAW GLB...skipping")
                    continue
                self.nlb.configure_tile(self.core_nodes[node.get_name()].get_name(), node_config_tuple)

    def display_names(self):
        if self.bespoke:
            # print(self.core_nodes)
            # print(self.name_maps)
            for key, val in self.name_maps.items():
                print(f"{key} => {val}")
        else:
            self.nlb.display_names()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Sparse TB Generator')
    parser.add_argument('--sam_graph',
                        type=str,
                        default="/home/max/Documents/SPARSE/sam/compiler/sam-outputs/dot/mat_identity.gv")
    parser.add_argument('--output_dir',
                        type=str,
                        default="/home/max/Documents/SPARSE/garnet/mek_outputs")
    parser.add_argument('--test_dump_dir',
                        type=str,
                        default="/home/max/Documents/SPARSE/garnet/mek_dump/")
    parser.add_argument('--trace', action="store_true")
    parser.add_argument('--bespoke', action="store_true")
    parser.add_argument('--remote_mems', action="store_true")
    args = parser.parse_args()
    bespoke = args.bespoke
    output_dir = args.output_dir

    # Clean up output dir...
    # If it doesn't exist, make it
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    else:
        # Otherwise clean it
        for filename in os.listdir(output_dir):
            ret = os.remove(output_dir + "/" + filename)

    nlb = None
    interconnect = None
    if bespoke is False:
        # chip_width = 20
        chip_width = 20
        # chip_height = 32
        chip_height = 5
        num_tracks = 3
        # altcore = [(ScannerCore, {}), (IntersectCore, {}),
        altcore = [(IOCoreReadyValid, {}), (ScannerCore, {}),
        # altcore = [(ScannerCore, {}),
                   (WriteScannerCore, {}), (BuffetCore, {'local_mems': not args.remote_mems})]

        interconnect = create_cgra(width=chip_width, height=chip_height,
                                #    io_sides=NetlistBuilder.io_sides(),
                                   io_sides=IOSide.None_,
                                   num_tracks=num_tracks,
                                   add_pd=False,
                                   # Soften the flush...?
                                   harden_flush=False,
                                   altcore=altcore,
                                   ready_valid=True)

        # circuit = interconnect.circuit()
        # import magma
        # magma.compile("tests", circuit)
        # exit(0)

        nlb = NetlistBuilder(interconnect=interconnect, cwd=args.test_dump_dir)

    # Get SAM graph
    sdg = SAMDotGraph(filename=args.sam_graph, local_mems=not args.remote_mems)
    graph = sdg.get_graph()

    stb = SparseTBBuilder(nlb=nlb, graph=graph, bespoke=bespoke, output_dir=output_dir, local_mems=not args.remote_mems)

    stb.display_names()

    tester = BasicTester(stb, stb.clk, stb.rst_n)

    tester.zero_inputs()

    if nlb is not None:
        tester.reset()
    else:
        # pulse reset manually
        tester.poke(stb.rst_n, 0)
        tester.step(2)
        tester.poke(stb.rst_n, 1)
        tester.step(2)

    tester.step(2)
    # Stall during config
    tester.poke(stb.io.stall, 1)

    # After stalling, we can configure the circuit
    # with its configuration bitstream
    if nlb is not None:
        cfgdat = nlb.get_config_data()
        for addr, index in cfgdat:
            tester.configure(addr, index)
            # if readback is True:
            #     self._tester.config_read(addr)
            tester.eval()

        tester.done_config()

        tester.poke(stb.io.stall, 0)
    tester.eval()

    # Get flush handle and apply flush to start off app
    tester.poke(stb.io.flush, 1)
    tester.eval()
    tester.step(2)
    tester.step(2)
    # tester.step(2)
    # tester.step(2)
    # tester.step(2)
    # for i in range(1000):
    #     tester.step(2)
    tester.poke(stb.io.flush, 0)
    tester.eval()
    for i in range(1000):
        tester.step(2)
    tester.wait_until_high(tester.circuit.done, timeout=500)

    from conftest import run_tb_fn
    run_tb_fn(tester, trace=args.trace, disable_ndarray=True, cwd="mek_dump")
    # run_tb_fn(tester, trace=True, disable_ndarray=True, cwd="./")

    stb.display_names()
