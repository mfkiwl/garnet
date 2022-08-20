from lake.utils.util import transform_strides_and_ranges, trim_config
import random
from gemstone.common.testers import BasicTester
from cgra.util import create_cgra, compress_config_data
from canal.util import IOSide
from archipelago import pnr
from _kratos import create_wrapper_flatten
import lassen.asm as asm


def io_sides():
    return IOSide.North | IOSide.East | IOSide.South | IOSide.West


def test_pond_rd_wr(run_tb):

    chip_size = 2
    interconnect = create_cgra(chip_size, chip_size, io_sides(),
                               num_tracks=3,
                               add_pd=True,
                               add_pond=True,
                               mem_ratio=(1, 2))

    netlist = {
        "e0": [("I0", "io2f_16"), ("p0", "input_width_16_num_2")],
        "e1": [("I1", "io2f_16"), ("p0", "data1")],
        "e2": [("p0", "output_width_16_num_0"), ("I2", "f2io_16")]
    }
    bus = {"e0": 16, "e1": 16, "e2": 16}

    placement, routing, _ = pnr(interconnect, (netlist, bus))
    config_data = interconnect.get_route_bitstream(routing)

    pe_x, pe_y = placement["p0"]

    petile = interconnect.tile_circuits[(pe_x, pe_y)]

    pondcore = petile.additional_cores[0]

    pond_config = {"mode": "pond",
                   "config": {"in2regfile_0": {"cycle_starting_addr": [0],
                                               "cycle_stride": [1, 1],
                                               "dimensionality": 2,
                                               "extent": [16, 1],
                                               "write_data_starting_addr": [0],
                                               "write_data_stride": [1, 1]},
                              "regfile2out_0": {"cycle_starting_addr": [16],
                                                "cycle_stride": [1, 1],
                                                "dimensionality": 2,
                                                "extent": [16, 1],
                                                "read_data_starting_addr": [0],
                                                "read_data_stride": [1, 1]}}}

    pond_config = pondcore.dut.get_bitstream(config_json=pond_config)
    for name, v in pond_config:
        idx, value = pondcore.get_config_data(name, v)
        config_data.append((interconnect.get_config_addr(idx, 1, pe_x, pe_y), value))

    config_data = compress_config_data(config_data)

    circuit = interconnect.circuit()

    tester = BasicTester(circuit, circuit.clk, circuit.reset)
    tester.zero_inputs()
    tester.reset()

    tester.poke(circuit.interface["stall"], 1)

    for addr, index in config_data:
        tester.configure(addr, index)
        tester.config_read(addr)
        tester.eval()
        tester.expect(circuit.read_config_data, index)

    tester.done_config()
    tester.poke(circuit.interface["stall"], 0)
    tester.eval()

    src_x0, src_y0 = placement["I0"]
    src_x1, src_y1 = placement["I1"]
    src_name0 = f"glb2io_16_X{src_x0:02X}_Y{src_y0:02X}"
    src_name1 = f"glb2io_16_X{src_x1:02X}_Y{src_y1:02X}"
    dst_x, dst_y = placement["I2"]
    dst_name = f"io2glb_16_X{dst_x:02X}_Y{dst_y:02X}"
    random.seed(0)

    for i in range(32):
        tester.poke(circuit.interface[src_name0], i)
        tester.poke(circuit.interface[src_name1], i + 1)
        tester.eval()
        if i >= 16:
            tester.expect(circuit.interface[dst_name], i - 16)
        tester.step(2)
        tester.eval()

    run_tb(tester)


def test_pond_pe(run_tb):

    chip_size = 2
    interconnect = create_cgra(chip_size, chip_size, io_sides(),
                               num_tracks=3,
                               add_pd=True,
                               add_pond=True,
                               mem_ratio=(1, 2))

    netlist = {
        "e0": [("I0", "io2f_16"), ("p0", "input_width_16_num_2")],
        "e1": [("I1", "io2f_16"), ("p0", "data1")],
        "e2": [("p0", "res"), ("I2", "f2io_16")],
        "e3": [("p0", "output_width_16_num_0"), ("p0", "data0")]
    }
    bus = {"e0": 16, "e1": 16, "e2": 16, "e3": 16}

    placement, routing, _ = pnr(interconnect, (netlist, bus))
    config_data = interconnect.get_route_bitstream(routing)

    pe_x, pe_y = placement["p0"]

    petile = interconnect.tile_circuits[(pe_x, pe_y)]

    pondcore = petile.additional_cores[0]

    add_bs = petile.core.get_config_bitstream(asm.umult0())
    for addr, data in add_bs:
        config_data.append((interconnect.get_config_addr(addr, 0, pe_x, pe_y), data))

    pond_config = {"mode": "pond",
                   "config": {"in2regfile_0": {"cycle_starting_addr": [0],
                                               "cycle_stride": [1, 1],
                                               "dimensionality": 2,
                                               "extent": [16, 1],
                                               "write_data_starting_addr": [0],
                                               "write_data_stride": [1, 1]},
                              "regfile2out_0": {"cycle_starting_addr": [16],
                                                "cycle_stride": [1, 1],
                                                "dimensionality": 2,
                                                "extent": [16, 1],
                                                "read_data_starting_addr": [0],
                                                "read_data_stride": [1, 1]}}}

    pond_config = pondcore.dut.get_bitstream(config_json=pond_config)
    for name, v in pond_config:
        idx, value = pondcore.get_config_data(name, v)
        config_data.append((interconnect.get_config_addr(idx, 1, pe_x, pe_y), value))

    config_data = compress_config_data(config_data)

    circuit = interconnect.circuit()

    tester = BasicTester(circuit, circuit.clk, circuit.reset)
    tester.zero_inputs()
    tester.reset()

    tester.poke(circuit.interface["stall"], 1)

    for addr, index in config_data:
        tester.configure(addr, index)
        tester.config_read(addr)
        tester.eval()
        tester.expect(circuit.read_config_data, index)

    tester.done_config()
    tester.poke(circuit.interface["stall"], 0)
    tester.eval()

    src_x0, src_y0 = placement["I0"]
    src_x1, src_y1 = placement["I1"]
    src_name0 = f"glb2io_16_X{src_x0:02X}_Y{src_y0:02X}"
    src_name1 = f"glb2io_16_X{src_x1:02X}_Y{src_y1:02X}"
    dst_x, dst_y = placement["I2"]
    dst_name = f"io2glb_16_X{dst_x:02X}_Y{dst_y:02X}"
    random.seed(0)

    for i in range(32):
        if i < 16:
            tester.poke(circuit.interface[src_name0], i)
            tester.eval()
        if i >= 16:
            num = random.randrange(0, 256)
            tester.poke(circuit.interface[src_name1], num)
            tester.eval()
            tester.expect(circuit.interface[dst_name], (i - 16) * num)
        tester.step(2)
        tester.eval()

    run_tb(tester)


def test_pond_pe_acc(run_tb):

    chip_size = 2
    interconnect = create_cgra(chip_size, chip_size, io_sides(),
                               num_tracks=3,
                               add_pd=True,
                               add_pond=True,
                               mem_ratio=(1, 2))

    netlist = {
        "e0": [("I0", "io2f_16"), ("p0", "data0")],
        "e1": [("p0", "output_width_16_num_0"), ("p0", "data1")],
        "e2": [("p0", "res"), ("p0", "input_width_16_num_2")],
        "e3": [("p0", "output_width_16_num_0"), ("I1", "f2io_16")]
    }
    bus = {"e0": 16, "e1": 16, "e2": 16, "e3": 16}

    placement, routing, _ = pnr(interconnect, (netlist, bus))
    config_data = interconnect.get_route_bitstream(routing)

    pe_x, pe_y = placement["p0"]

    petile = interconnect.tile_circuits[(pe_x, pe_y)]

    pondcore = petile.additional_cores[0]

    add_bs = petile.core.get_config_bitstream(asm.add())
    for addr, data in add_bs:
        config_data.append((interconnect.get_config_addr(addr, 0, pe_x, pe_y), data))

    pond_config = {"mode": "pond",
                   "config": {"in2regfile_0": {"cycle_starting_addr": [0],
                                               "cycle_stride": [1, 0],
                                               "dimensionality": 2,
                                               "extent": [16, 1],
                                               "write_data_starting_addr": [8],
                                               "write_data_stride": [0, 0]},
                              "regfile2out_0": {"cycle_starting_addr": [0],
                                                "cycle_stride": [1, 0],
                                                "dimensionality": 2,
                                                "extent": [16, 1],
                                                "read_data_starting_addr": [8],
                                                "read_data_stride": [0, 0]}}}

    pond_config = pondcore.dut.get_bitstream(config_json=pond_config)
    for name, v in pond_config:
        idx, value = pondcore.get_config_data(name, v)
        config_data.append((interconnect.get_config_addr(idx, 1, pe_x, pe_y), value))

    config_data = compress_config_data(config_data)

    circuit = interconnect.circuit()

    tester = BasicTester(circuit, circuit.clk, circuit.reset)
    tester.zero_inputs()
    tester.reset()

    tester.poke(circuit.interface["stall"], 1)

    for addr, index in config_data:
        tester.configure(addr, index)
        tester.config_read(addr)
        tester.eval()
        tester.expect(circuit.read_config_data, index)

    tester.done_config()
    tester.poke(circuit.interface["stall"], 0)
    tester.eval()

    src_x0, src_y0 = placement["I0"]
    src_name0 = f"glb2io_16_X{src_x0:02X}_Y{src_y0:02X}"
    dst_x, dst_y = placement["I1"]
    dst_name = f"io2glb_16_X{dst_x:02X}_Y{dst_y:02X}"
    random.seed(0)

    total = 0
    for i in range(16):
        tester.poke(circuit.interface[src_name0], i + 1)
        total = total + i
        tester.eval()
        tester.expect(circuit.interface[dst_name], total)
        tester.step(2)
        tester.eval()

    run_tb(tester)


def test_pond_config(run_tb):
    # 1x1 interconnect with only PE tile
    interconnect = create_cgra(1, 1, IOSide.None_, standalone=True,
                               mem_ratio=(0, 1),
                               add_pond=True)

    # get pond core
    pe_tile = interconnect.tile_circuits[0, 0]
    pond_core = pe_tile.additional_cores[0]
    pond_feat = pe_tile.features().index(pond_core)
    sram_feat = pond_feat + pond_core.num_sram_features

    circuit = interconnect.circuit()
    tester = BasicTester(circuit, circuit.clk, circuit.reset)
    tester.zero_inputs()
    tester.reset()

    config_data = []
    # tile enable
    reg_addr, value = pond_core.get_config_data("tile_en", 1)
    config_data.append((interconnect.get_config_addr(reg_addr, pond_feat, 0, 0), value))

    for i in range(32):
        addr = interconnect.get_config_addr(i, sram_feat, 0, 0)
        config_data.append((addr, i + 1))
    for addr, data in config_data:
        tester.configure(addr, data)

    # read back
    for addr, data in config_data:
        tester.config_read(addr)
        tester.expect(circuit.read_config_data, data)

    run_tb(tester)
