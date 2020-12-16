import random
import tempfile
import pytest
import os
import glob
import shutil
import math
import argparse
import magma
import json
from canal.util import IOSide
from archipelago import pnr
from cgra import create_cgra, compress_config_data
from gemstone.common.testers import BasicTester
from peak import family
import filecmp
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


def io_sides():
    return IOSide.North | IOSide.East | IOSide.South | IOSide.West

def cw_files():
    filenames = ["CW_fp_add.v", "CW_fp_mult.v"]
    dirname = "peak_core"
    result_filenames = []
    for name in filenames:
        filename = os.path.join(dirname, name)
        assert os.path.isfile(filename)
        result_filenames.append(filename)
    return result_filenames

def copy_file(src_filename, dst_filename, override=False):
    if (
        not override
        and os.path.isfile(dst_filename)
        and filecmp.cmp(src_filename, dst_filename, shallow=False)
    ):
        return
    shutil.copy2(src_filename, dst_filename)

def generate_testbench(PE, bitstream_json):
    # detect the environment
    if shutil.which("xrun"):
        use_xcelium = True
    else:
        use_xcelium = False

    arch_fc = PE["fc"]
    chip_size = 16
    interconnect = create_cgra(chip_size, chip_size, IOSide.North,
                               num_tracks=5,
                               add_pd=False,
                               use_sram_stub=True,
                               add_pond=False,
                               mem_ratio=(1, 4),
                               pe_fc=arch_fc)

    print("Created CGRA")
    circuit = interconnect.circuit()
    print("Created interconnect circuit")
    tester = BasicTester(circuit, circuit.clk, circuit.reset)
    print("Created Tester")
    if self.use_xcelium:
        tester.zero_inputs()
    tester.circuit.clk = 0
    tester.reset()
    # set the PE core
    bitstream_name = bitstream_json["bitstream"]
    bitstream_file = open(bitstream_name, 'r')
    bitstream_data = bitstream_file.read()
    
    bitstream = bitstream_data.split("\n")
    for x in bitstream:
        addr, index = x.split(" ")
        addr = int(addr, 16)
        index = int(index, 16)
        tester.configure(addr, index)
        tester.config_read(addr)
        tester.eval()
        tester.expect(circuit.read_config_data, index)

    tester.done_config()
    print("Done Config")

    file_in = tester.file_open(bitstream_json["input_filename"], "r",
                                chunk_size=1)
    file_out = tester.file_open("tbg_dse_out", "w",
                                chunk_size=1)

    input_port_names = bitstream_json["input_port_name"]
    input_port_names.sort()
    output_port_names = bitstream_json["output_port_name"]
    output_port_names.sort()

    _loop_size = os.path.getsize(bitstream_json["input_filename"])

    loop = tester.loop(_loop_size * len(input_port_names) + 1)
    for input_port_name in input_port_names:
        value = loop.file_read(file_in)
        loop.poke(circuit.interface[input_port_name], value)
        #loop.eval() # commented this out for realistic simulation accuracy
    for output_port_name in output_port_names:
        loop.file_write(file_out, circuit.interface[output_port_name])

    loop.step(2)


    tester.file_close(file_in)
    tester.file_close(file_out)

    tempdir = "temp/garnet"
    if not os.path.isdir(tempdir):
        os.makedirs(tempdir, exist_ok=True)
    # copy files over
    if self.use_xcelium:
        # coreir always outputs as verilog even though we have system-
        # verilog component
        copy_file("garnet.v",
                  os.path.join(tempdir, "Interconnect.sv"))
    else:
        copy_file("garnet.v",
                  os.path.join(tempdir, "Interconnect.v"))

    base_dir = os.path.abspath(os.path.dirname(__file__))
    # cad_dir = "/cad/synopsys/dc_shell/J-2014.09-SP3/dw/sim_ver/"
    cad_dir = "/cad/cadence/GENUS_19.10.000_lnx86/share/synth/lib/chipware/sim/verilog/CW/"
   

    # std cells
    for std_cell in glob.glob(os.path.join(base_dir, "tests/*.sv")):
        copy_file(std_cell,
                    os.path.join(tempdir, os.path.basename(std_cell)))

    for genesis_verilog in glob.glob(os.path.join(base_dir,
                                                    "genesis_verif/*.*")):
        copy_file(genesis_verilog,
                    os.path.join(tempdir, os.path.basename(genesis_verilog)))

 
    if self.use_xcelium:
        # Check for clock period override in env (mflowgen)
        clk_period = 1.1
        clk_period_env = os.getenv("clock_period")
        if clk_period_env is not None:
            clk_period = float(clk_period_env)

        verilogs = list(glob.glob(os.path.join(tempdir, "*.v")))
        verilogs += list(glob.glob(os.path.join(tempdir, "*.sv")))
        verilog_libraries = [os.path.basename(f) for f in verilogs]
        # sanity check since we just copied
        assert "Interconnect.sv" in verilog_libraries
        if "Interconnect.v" in verilog_libraries:
            # ncsim will freak out if the system verilog file has .v
            # extension
            verilog_libraries.remove("Interconnect.v")
            os.remove(os.path.join(tempdir, "Interconnect.v"))
        tester.compile_and_run(target="system-verilog",
                               skip_compile=True,
                               skip_run=args.tb_only,
                               simulator="xcelium",
                               # num_cycles is an experimental feature
                               # need to be merged in fault
                               num_cycles=1000000,
                               no_warning=True,
                               dump_vcd=True,
                               clock_step_delay=(clk_period / 2.0),
                               timescale="1ns/1ps",
                               include_verilog_libraries=verilog_libraries,
                               directory=tempdir)

    else:
        verilator_lib = os.path.join(tempdir, "obj_dir", "VGarnet__ALL.a")
        skip_build = os.path.isfile(verilator_lib)
        tester.compile_and_run(target="verilator",
                                skip_compile=True,
                                skip_verilator=skip_build,
                                directory=tempdir,
                                    flags=["-Wno-fatal"])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bitstream', type=str, default='./bitstream.json')
    parser.add_argument('--arch', type=str, default="./PE.json")
    args = parser.parse_args()

    arch = read_arch(f"{args.arch}")
    dse_fc = wrapped_peak_class(arch)
    dse_asm = asm_arch_closure(arch)(family.PyFamily())

    PE = {"fc": dse_fc, "pe_fc_name": "PE_wrapped", "op": dse_asm(), "rules": None}

    with open(args.bitstream) as f:
        bitstream_json = json.load(f)




    generate_testbench(PE, bitstream_json)
