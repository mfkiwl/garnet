import random
import tempfile
import pytest
import os
import glob
import shutil
import math

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


@pytest.fixture()
def io_sides():
    return IOSide.North | IOSide.East | IOSide.South | IOSide.West

@pytest.fixture(scope="module")
def dw_files():
    filenames = ["DW_fp_add.v", "DW_fp_mult.v"]
    dirname = "peak_core"
    result_filenames = []
    for name in filenames:
        filename = os.path.join(dirname, name)
        assert os.path.isfile(filename)
        result_filenames.append(filename)
    return result_filenames

examples_coreir = [
    "add2",
]

lassen_rules = "src/lassen/scripts/rewrite_rules/lassen_rewrite_rules.json"
arch = read_arch("src/peak_generator/examples/misc_tests/test_alu.json")
dse_fc = wrapped_peak_class(arch, debug=True)
dse_asm = asm_arch_closure(arch)(family.PyFamily())

@pytest.mark.parametrize("PE", [
{"fc": dse_fc, "pe_fc_name": "PE_wrapped", "op": dse_asm(), "rules": None},
{"fc": lassen_fc, "pe_fc_name": "PE", "op": lassen_asm.add(), "rules": lassen_rules}, 
])
@pytest.mark.parametrize("app", examples_coreir)
def test_netlist(PE, app, io_sides, dw_files):

    arch_fc = PE["fc"]

    chip_size = 3
    interconnect = create_cgra(chip_size, chip_size, io_sides,
                               num_tracks=3,
                               add_pd=True,
                               mem_ratio=(1, 2),
                               pe_fc = arch_fc)


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
    interconnect = create_cgra(chip_size, chip_size, io_sides,
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

    circuit = interconnect.circuit()
    tester = BasicTester(circuit, circuit.clk, circuit.reset)
    tester.circuit.clk = 0
    tester.reset()
    # set the PE core
    for addr, index in config_data:
        tester.configure(addr, index)
        tester.config_read(addr)
        tester.eval()
        tester.expect(circuit.read_config_data, index)

    tester.done_config()

    src_x0, src_y0 = placement["I0"]
    src_x1, src_y1 = placement["I1"]
    src_name0 = f"glb2io_16_X{src_x0:02X}_Y{src_y0:02X}"
    src_name1 = f"glb2io_16_X{src_x1:02X}_Y{src_y1:02X}"
    dst_x, dst_y = placement["I3"]
    dst_name = f"io2glb_16_X{dst_x:02X}_Y{dst_y:02X}"
    random.seed(0)
    for _ in range(100):
        num_1 = random.randrange(0, 256)
        num_2 = random.randrange(0, 256)
        tester.poke(circuit.interface[src_name0], num_1)
        tester.poke(circuit.interface[src_name1], num_2)

        tester.eval()
        tester.expect(circuit.interface[dst_name], num_1 + num_2)

    with tempfile.TemporaryDirectory() as tempdir:
        for genesis_verilog in glob.glob("genesis_verif/*.*"):
            shutil.copy(genesis_verilog, tempdir)
        for filename in dw_files:
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



apps = [
    "add2",
    #"add1_const",
    #"add4_pipe",
    #"conv_3_3.json",
]

def sample_pnr_input():
    id_to_name = dict(
        I0="io_in",
        I1="io_out",
        p0="PE0",
    )
    inst_to_instr = dict(
        I0=1,
        I1=2,
        p0=17
    )
    netlist = dict(
        e0=[("I0", "io2f_16"), ("p0", "data0"), ("p0", "data1")],
        e1=[("p0", "alu_res"), ("I1", "f2io_16")]
    )
    buses = dict(
        e0=16,
        e1=16,
    )

    return dict(
        id_to_name=id_to_name,
        inst_to_instr=inst_to_instr,
        netlist=netlist,
        buses=buses
    )


@pytest.mark.parametrize("app", apps)
def test_pnr(app, dw_files, io_sides):
    # to account for different CGRA size, we feed in data to the very top-left
    # SB and route through horizontally to reach very top-right SB
    # we configure the top-left PE as multiplier
    chip_size = 2
    interconnect = create_cgra(chip_size, chip_size, io_sides,
                               num_tracks=3,
                               add_pd=True,
                               mem_ratio=(1, 2))

    netlist_info = sample_pnr_input()
    placement, routing = pnr(interconnect, (netlist_info["netlist"], netlist_info["buses"]))
    config_data = interconnect.get_route_bitstream(routing)
