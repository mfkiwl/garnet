from mapper import CreateNetlist
import pytest
import os
from canal.util import IOSide
from archipelago import pnr
from cgra import create_cgra, compress_config_data
from lassen import PE_fc

import metamapper.coreir_util as cutil
from metamapper.common_passes import VerifyNodes, print_dag
from metamapper import CoreIRContext
from metamapper.irs.coreir import gen_CoreIRNodes
from metamapper.node import Nodes, Constant
import metamapper.peak_util as putil
from metamapper.coreir_mapper import Mapper

@pytest.fixture()
def io_sides():
    return IOSide.North | IOSide.East | IOSide.South | IOSide.West

examples_coreir = [
    "add2",
    "conv_3_3",
]

lassen_rules = "src/lassen/scripts/rewrite_rules/lassen_rewrite_rules.json"

@pytest.mark.parametrize("app", examples_coreir)
def test_netlist(app, io_sides):


    chip_size = 3
    interconnect = create_cgra(chip_size, chip_size, io_sides,
                               num_tracks=3,
                               add_pd=True,
                               mem_ratio=(1, 2))


    print("STARTING TEST")
    c = CoreIRContext(reset=True)
    file_name = f"coreir_examples/post_mapped/{app}.json"
    cutil.load_libs(["commonlib"])
    CoreIRNodes = gen_CoreIRNodes(16)
    cmod = cutil.load_from_json(file_name) #libraries=["lakelib"])
    dag = cutil.coreir_to_dag(CoreIRNodes, cmod)
    print_dag(dag)
    arch_fc = PE_fc
    name = "PE"
    ArchNodes = Nodes("Arch")
    putil.load_from_peak(ArchNodes, arch_fc)
    mapper = Mapper(CoreIRNodes, ArchNodes, lazy=True, rule_file = lassen_rules)
    mapped_dag = mapper.do_mapping(dag, prove_mapping=False)
    print_dag(mapped_dag)

    node_info = {
        ArchNodes.dag_nodes["PE"] : 'p',
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
                               mem_ratio=(1, 2))

    placement, routing = pnr(interconnect, (netlist_info["netlist"], netlist_info["buses"]))
    config_data = interconnect.get_route_bitstream(routing)
    print(config_data)

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
