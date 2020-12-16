import random
import tempfile
import pytest
import os
import glob
import shutil
import math
import sys

from mapper import CreateNetlist
from canal.util import IOSide
from archipelago import pnr
from cgra import create_cgra, compress_config_data
from gemstone.common.testers import BasicTester
from peak import family

from lassen import PE_fc as lassen_fc
from lassen import asm as lassen_asm

import metamapper.coreir_util as cutil
from metamapper.common_passes import VerifyNodes, print_dag
from metamapper import CoreIRContext
from metamapper.irs.coreir import gen_CoreIRNodes
from metamapper.node import Nodes, Constant
import metamapper.peak_util as putil
from metamapper.coreir_mapper import Mapper

from peak_gen.arch import read_arch
from peak_gen.peak_wrapper import wrapped_peak_class
from peak_gen.asm import asm_arch_closure


def copy_file(src_filename, dst_filename, override=False):
    if (
        not override
        and os.path.isfile(dst_filename)
        and filecmp.cmp(src_filename, dst_filename, shallow=False)
    ):
        return
    shutil.copy2(src_filename, dst_filename)

def io_sides():
    return IOSide.North | IOSide.East | IOSide.South | IOSide.West

def dw_files():
    filenames = ["DW_fp_add.v", "DW_fp_mult.v"]
    dirname = "peak_core"
    result_filenames = []
    for name in filenames:
        filename = os.path.join(dirname, name)
        assert os.path.isfile(filename)
        result_filenames.append(filename)
    return result_filenames

def get_max_col():
    max_x = 0
    for addr, _ in config_data:
        x = (addr & 0xFFFF) >> 8
        if x > max_x:
            max_x = x
    return max_x + 1

def get_input_output(netlist):
    inputs = []
    outputs = []
    for _, net in netlist.items():
        for blk_id, port in net:
            if port == "io2f_16":
                inputs.append(blk_id)
            elif port == "f2io_16":
                outputs.append(blk_id)
            elif port == "io2f_1":
                inputs.append(blk_id)
            elif port == "f2io_1":
                outputs.append(blk_id)
    return inputs, outputs

def get_io_interface(inputs, outputs, placement, id_to_name):
    input_interface = []
    output_interface = []
    reset_port_name = ""
    valid_port_name = ""
    en_port_name = []

    for blk_id in inputs:
        x, y = placement[blk_id]
        bit_width = 16 if blk_id[0] == "I" else 1
        name = f"glb2io_{bit_width}_X{x:02X}_Y{y:02X}"
        input_interface.append(name)
        blk_name = id_to_name[blk_id]
        if "reset" in blk_name:
            reset_port_name = name
        if "in_en" in blk_name:
            en_port_name.append(name)
    for blk_id in outputs:
        x, y = placement[blk_id]
        bit_width = 16 if blk_id[0] == "I" else 1
        name = f"io2glb_{bit_width}_X{x:02X}_Y{y:02X}"
        output_interface.append(name)
        blk_name = id_to_name[blk_id]
        if "valid" in blk_name:
            valid_port_name = name
    return input_interface, output_interface,\
            (reset_port_name, valid_port_name, en_port_name)


lassen_rules = "src/lassen/scripts/rewrite_rules/lassen_rewrite_rules.json"

PE = {"fc": lassen_fc, "pe_fc_name": "PE", "op": lassen_asm.add(), "rules": lassen_rules}

arch_fc = PE["fc"]
app = "add2"
c = CoreIRContext(reset=True)
file_name = f"coreir_examples/post_mapped/{app}.json"
cutil.load_libs(["commonlib"])
CoreIRNodes = gen_CoreIRNodes(16)
cmod = cutil.load_from_json(file_name) #libraries=["lakelib"])
dag = cutil.coreir_to_dag(CoreIRNodes, cmod)
print_dag(dag)
ArchNodes = Nodes("Arch")
putil.load_from_peak(ArchNodes, arch_fc)
mapper = Mapper(CoreIRNodes, ArchNodes, lazy=True, rule_file=PE["rules"])
mapped_dag = mapper.do_mapping(dag, prove_mapping=False)
print_dag(mapped_dag)
node_info = {
    ArchNodes.dag_nodes[PE["pe_fc_name"]] : 'p',
    CoreIRNodes.dag_nodes["coreir.reg"][0]: 'R',
    CoreIRNodes.dag_nodes["coreir.reg"][1]: 'R',
    #CoreIRNodes.peak_nodes["corebit.reg"]: 'r'
}
netlist_info = CreateNetlist(node_info).doit(mapped_dag)
print("N")
for k, v in netlist_info["netlist"].items():
    print(f"  {k}")
    for _v in v:
        print(f"    {_v}")

print("B")
for k,v in netlist_info["buses"].items():
    print(f"  {k}, {v}")

chip_size = 2
interconnect = create_cgra(chip_size, chip_size, io_sides(),
                        num_tracks=3,
                        add_pd=True,
                        mem_ratio=(1, 2),
                        pe_fc=arch_fc)

placement, routing = pnr(interconnect, (netlist_info["netlist"], netlist_info["buses"]))
config_data = interconnect.get_route_bitstream(routing)
print(config_data)
x, y = placement["p2"]
tile = interconnect.tile_circuits[(x, y)]
add_bs = tile.core.get_config_bitstream(PE["op"])
for addr, data in add_bs:
    config_data.append((interconnect.get_config_addr(addr, 0, x, y), data))
config_data = compress_config_data(config_data)
inputs, outputs = get_input_output(netlist_info["netlist"])
net_to_id = netlist_info["net_to_id"]
id_to_name = {net_to_id[i] : i for i in net_to_id}
input_interface, output_interface,\
            (reset, valid, en) = get_io_interface(inputs, outputs, placement, id_to_name)


input_filename = sys.argv[1]
output_filename = sys.argv[2]

print(input_filename, output_filename)
circuit = interconnect.circuit()
tester = BasicTester(circuit, circuit.clk, circuit.reset)
file_in = tester.file_open(input_filename, "r",
                            chunk_size=1)
file_out = tester.file_open(output_filename, "w",
                            chunk_size=1)

tester.reset()

for addr, index in config_data:
    tester.configure(addr, index)
    tester.config_read(addr)
    tester.eval()
    tester.expect(circuit.read_config_data, index)

tester.done_config()


input_port_names = input_interface
input_port_names.sort()
output_port_names = output_interface
output_port_names.sort()

_loop_size = os.path.getsize(input_filename)

loop = tester.loop(_loop_size * len(input_port_names))
for input_port_name in input_port_names:
    value = loop.file_read(file_in)
    loop.poke(circuit.interface[input_port_name], value)
    loop.eval()
for output_port_name in output_port_names:
    loop.file_write(file_out, circuit.interface[output_port_name])

loop.step(2)


tester.file_close(file_in)
tester.file_close(file_out)


tempdir = "temp/"
if not os.path.isdir(tempdir):
    os.makedirs(tempdir, exist_ok=True)
for genesis_verilog in glob.glob("genesis_verif/*.*"):
    shutil.copy(genesis_verilog, tempdir)
for filename in dw_files():
    shutil.copy(filename, tempdir)
shutil.copy(os.path.join("tests", "test_memory_core",
                            "sram_stub.v"),
            os.path.join(tempdir, "sram_512w_16b.v"))
for aoi_mux in glob.glob("tests/*.sv"):
    shutil.copy(aoi_mux, tempdir)
tester.compile_and_run(target="verilator",
                        magma_output="coreir-verilog",
                        magma_opts={"coreir_libs": {"float_DW"}},
                        directory=tempdir,
                        flags=["-Wno-fatal"])