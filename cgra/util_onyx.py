from canal.cyclone import SwitchBoxSide, SwitchBoxIO
from canal.global_signal import GlobalSignalWiring, apply_global_meso_wiring,\
    apply_global_fanout_wiring, apply_global_parallel_meso_wiring
from canal.util import IOSide, get_array_size, create_uniform_interconnect, \
    SwitchBoxType
from canal.interconnect import Interconnect
from memory_core.buffet_core import BuffetCore
from memory_core.crddrop_core import CrdDropCore
from memory_core.crdhold_core import CrdHoldCore
from memory_core.fake_pe_core import FakePECore
from memory_core.io_core_rv import IOCoreReadyValid
from memory_core.repeat_core import RepeatCore
from memory_core.repeat_signal_generator_core import RepeatSignalGeneratorCore
from memory_core.write_scanner_core import WriteScannerCore
from passes.power_domain.pd_pass import add_power_domain, add_aon_read_config_data
from lassen.sim import PE_fc as lassen_fc
from io_core.io_core_magma import IOCoreValid, IOCore
from memory_core.memory_core_magma import MemCore
from memory_core.pond_core import PondCore
from peak_core.peak_core import PeakCore
from memory_core.scanner_core import ScannerCore
from memory_core.intersect_core import IntersectCore
from typing import Tuple, Dict, List, Tuple
from passes.tile_id_pass.tile_id_pass import tile_id_physical
from memory_core.reg_core import RegCore
from passes.clk_pass.clk_pass import clk_physical
from passes.pipeline_global_pass.pipeline_global_pass import pipeline_global_signals
from passes.interconnect_port_pass import wire_core_flush_pass
from gemstone.common.util import compress_config_data
from peak_gen.peak_wrapper import wrapped_peak_class
from peak_gen.arch import read_arch
from lake.top.tech_maps import GF_Tech_Map
from memory_core.onyx_pe_core import OnyxPECore
from memory_core.core_combiner_core import CoreCombinerCore
from lake.modules.repeat import Repeat
from lake.modules.repeat_signal_generator import RepeatSignalGenerator
from lake.modules.scanner import Scanner
from lake.modules.scanner_pipe import ScannerPipe
from lake.modules.write_scanner import WriteScanner
from lake.modules.intersect import Intersect
from lake.modules.reg_cr import Reg
from lake.modules.strg_ub_vec import StrgUBVec
from lake.modules.strg_ub_thin import StrgUBThin
from lake.modules.crddrop import CrdDrop
from lake.modules.crdhold import CrdHold
from lake.modules.strg_RAM import StrgRAM
from lake.modules.stencil_valid import StencilValid
from lake.modules.buffet_like import BuffetLike
from lake.top.fiber_access import FiberAccess
from lake.modules.onyx_pe import OnyxPE
from lassen.sim import PE_fc
import magma as m
from peak import family


def get_actual_size(width: int, height: int, io_sides: IOSide):
    if io_sides & IOSide.North:
        height += 1
    if io_sides & IOSide.East:
        width += 1
    if io_sides & IOSide.South:
        height += 1
    if io_sides & IOSide.West:
        width += 1
    return width, height


def create_cgra(width: int, height: int, io_sides: IOSide,
                add_reg: bool = True,
                mem_ratio: Tuple[int, int] = (1, 4),
                reg_addr_width: int = 8,
                config_data_width: int = 32,
                tile_id_width: int = 16,
                num_tracks: int = 5,
                add_pd: bool = True,
                use_sim_sram: bool = True,
                hi_lo_tile_id: bool = True,
                pass_through_clk: bool = True,
                tile_layout_option: int = 0,  # 0: column-based, 1: row-based
                global_signal_wiring: GlobalSignalWiring =
                GlobalSignalWiring.Meso,
                pipeline_config_interval: int = 8,
                standalone: bool = False,
                amber_pond: bool = False,
                add_pond: bool = False,
                pond_area_opt: bool = True,
                pond_area_opt_share: bool = False,
                pond_area_opt_dual_config: bool = True,
                harden_flush: bool = True,
                use_io_valid: bool = True,
                switchbox_type: SwitchBoxType = SwitchBoxType.Imran,
                pipeline_regs_density: list = None,
                port_conn_option: list = None,
                port_conn_override: Dict[str,
                                         List[Tuple[SwitchBoxSide,
                                                    SwitchBoxIO]]] = None,
                altcore=None,
                pe_fc=lassen_fc,
                ready_valid: bool = True,
                scgra: bool = True,
                scgra_combined: bool = True,
                mem_width: int = 64,
                mem_depth: int = 512,
                mem_input_ports: int = 2,
                mem_output_ports: int = 2,
                macro_width: int = 32,
                dac_exp: bool = False,
                dual_port: bool = False,
                rf: bool = False,
                perf_debug: bool = False):
    # currently only add 16bit io cores
    # bit_widths = [1, 16, 17]
    bit_widths = [1, 17]
    track_length = 1

    fifo_depth = 2

    if scgra is True:
        pe_prefix = "PEGEN_"
        clk_enable = True
        physical_sram = not use_sim_sram

        pe_child = PE_fc(family.MagmaFamily())
        m.compile(f"garnet_PE",
                  pe_child,
                  output="coreir-verilog",
                  coreir_libs={"float_CW"},
                  verilog_prefix=pe_prefix)
        m.clear_cachedFunctions()
        m.frontend.coreir_.ResetCoreIR()
        m.generator.reset_generator_cache()
        m.logging.flush_all()  # flush all staged logs

        pipeline_scanner = True
        use_fiber_access = True

        if not scgra_combined:

            altcore = [(ScannerCore, {'fifo_depth': fifo_depth,
                                      'add_clk_enable': clk_enable,
                                      'pipelined': pipeline_scanner}),
                       (BuffetCore, {'local_mems': True,
                                     'physical_mem': physical_sram,
                                     'fifo_depth': fifo_depth,
                                     'tech_map': GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port)}),
                       (OnyxPECore, {'fifo_depth': fifo_depth, 'ext_pe_prefix': pe_prefix}),
                       (WriteScannerCore, {'fifo_depth': fifo_depth}),
                       (RepeatCore, {'fifo_depth': fifo_depth}),
                       (IntersectCore, {'fifo_depth': fifo_depth}),
                       (CrdDropCore, {'fifo_depth': fifo_depth}),
                       (CrdHoldCore, {'fifo_depth': fifo_depth}),
                       (RepeatSignalGeneratorCore, {'passthru': False,
                                                    'fifo_depth': fifo_depth}),
                       (RegCore, {'fifo_depth': fifo_depth})]

        else:

            controllers = []

            if pipeline_scanner:
                scan = ScannerPipe(data_width=16,
                                   fifo_depth=fifo_depth,
                                   add_clk_enable=True,
                                   defer_fifos=True,
                                   add_flush=False,
                                   perf_debug=perf_debug)
            else:
                scan = Scanner(data_width=16,
                               fifo_depth=fifo_depth,
                               defer_fifos=True,
                               add_flush=False)

            wscan = WriteScanner(data_width=16,
                                 fifo_depth=fifo_depth,
                                 defer_fifos=True,
                                 add_flush=False,
                                 perf_debug=perf_debug)
            if dac_exp:
                if dual_port:
                    read_delay = 1
                    if rf:
                        read_delay = 0
                    strg_ub = StrgUBThin(
                        config_mode_str="UB",
                        data_width=16,  # CGRA Params
                        mem_width=mem_width,
                        mem_depth=mem_depth,
                        input_addr_iterator_support=6,
                        input_sched_iterator_support=6,
                        output_addr_iterator_support=6,
                        output_sched_iterator_support=6,
                        interconnect_input_ports=mem_input_ports,  # Connection to int
                        interconnect_output_ports=mem_output_ports,
                        config_width=16,
                        read_delay=read_delay,  # Cycle delay in read (SRAM vs Register File)
                        rw_same_cycle=dual_port,
                        gen_addr=True,
                        comply_with_17=True,
                        area_opt=False,
                        area_opt_share=False,
                        area_opt_dual_config=False,
                        chaining=True,
                        name_suffix="_DAC",
                        reduced_id_config_width=16,
                        delay_width=4,
                        iterator_support2=2  # assumes that this port has smaller iter_support
                    )
                else:
                    strg_ub = StrgUBVec(data_width=16,
                                        mem_width=mem_width,
                                        mem_depth=mem_depth,
                                        interconnect_input_ports=mem_input_ports,
                                        interconnect_output_ports=mem_output_ports)

            else:
                strg_ub = StrgUBVec(data_width=16,
                                    mem_width=mem_width,
                                    mem_depth=mem_depth)
            fiber_access = FiberAccess(data_width=16,
                                       local_memory=False,
                                       tech_map=GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port),
                                       defer_fifos=True,
                                       add_flush=False,
                                       use_pipelined_scanner=pipeline_scanner,
                                       fifo_depth=fifo_depth,
                                       buffet_optimize_wide=True,
                                       perf_debug=perf_debug)
            buffet = BuffetLike(data_width=16,
                                mem_depth=mem_depth, local_memory=False,
                                tech_map=GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port),
                                defer_fifos=True,
                                optimize_wide=True,
                                add_flush=False,
                                fifo_depth=fifo_depth)
            strg_ram = StrgRAM(data_width=16,
                               banks=1,
                               memory_width=mem_width,
                               memory_depth=mem_depth,
                               rw_same_cycle=False,
                               read_delay=1,
                               addr_width=16,
                               prioritize_write=True,
                               comply_with_17=True)

            stencil_valid = StencilValid()

            if dac_exp:
                controllers.append(strg_ub)
                controllers.append(strg_ram)
                controllers.append(stencil_valid)
            else:
                if use_fiber_access:
                    controllers.append(fiber_access)
                else:
                    controllers.append(scan)
                    controllers.append(wscan)
                    controllers.append(buffet)

                controllers.append(strg_ub)
                controllers.append(strg_ram)
                controllers.append(stencil_valid)

            isect = Intersect(data_width=16,
                              use_merger=False,
                              fifo_depth=fifo_depth,
                              defer_fifos=True,
                              add_flush=False,
                              perf_debug=perf_debug)
            crd_drop = CrdDrop(data_width=16,
                               fifo_depth=fifo_depth,
                               lift_config=True,
                               defer_fifos=True,
                               add_flush=False,
                               perf_debug=perf_debug)
            crd_hold = CrdHold(data_width=16,
                               fifo_depth=fifo_depth,
                               lift_config=True,
                               defer_fifos=True,
                               add_flush=False,
                               perf_debug=perf_debug)
            onyxpe = OnyxPE(data_width=16,
                            fifo_depth=fifo_depth,
                            defer_fifos=True,
                            ext_pe_prefix=pe_prefix,
                            pe_ro=True,
                            do_config_lift=False,
                            add_flush=False,
                            perf_debug=perf_debug)
            repeat = Repeat(data_width=16,
                            fifo_depth=fifo_depth,
                            defer_fifos=True,
                            add_flush=False,
                            perf_debug=perf_debug)
            rsg = RepeatSignalGenerator(data_width=16,
                                        passthru=False,
                                        fifo_depth=fifo_depth,
                                        defer_fifos=True,
                                        add_flush=False,
                                        perf_debug=perf_debug)
            regcr = Reg(data_width=16,
                        fifo_depth=fifo_depth,
                        defer_fifos=True,
                        add_flush=False,
                        perf_debug=perf_debug)

            controllers_2 = []

            controllers_2.append(isect)
            controllers_2.append(crd_drop)
            controllers_2.append(crd_hold)
            controllers_2.append(onyxpe)
            controllers_2.append(repeat)
            controllers_2.append(rsg)
            controllers_2.append(regcr)

            altcore = [(CoreCombinerCore, {'controllers_list': controllers_2,
                                           'use_sim_sram': not physical_sram,
                                           'tech_map': GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port),
                                           'pnr_tag': "p",
                                           'name': "PE",
                                           'mem_width': mem_width,
                                           'mem_depth': mem_depth,
                                           'input_prefix': "PE_",
                                           'fifo_depth': fifo_depth,
                                           'dual_port': dual_port,
                                           'rf': rf}),
                       (CoreCombinerCore, {'controllers_list': controllers_2,
                                           'use_sim_sram': not physical_sram,
                                           'tech_map': GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port),
                                           'pnr_tag': "p",
                                           'mem_width': mem_width,
                                           'mem_depth': mem_depth,
                                           'name': "PE",
                                           'input_prefix': "PE_",
                                           'fifo_depth': fifo_depth,
                                           'dual_port': dual_port,
                                           'rf': rf}),
                       (CoreCombinerCore, {'controllers_list': controllers_2,
                                           'use_sim_sram': not physical_sram,
                                           'tech_map': GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port),
                                           'pnr_tag': "p",
                                           'mem_width': mem_width,
                                           'mem_depth': mem_depth,
                                           'name': "PE",
                                           'input_prefix': "PE_",
                                           'fifo_depth': fifo_depth,
                                           'dual_port': dual_port,
                                           'rf': rf}),
                       (CoreCombinerCore, {'controllers_list': controllers,
                                           'use_sim_sram': not physical_sram,
                                           'tech_map': GF_Tech_Map(depth=mem_depth, width=macro_width, dual_port=dual_port),
                                           'pnr_tag': "m",
                                           'mem_width': mem_width,
                                           'mem_depth': mem_depth,
                                           'name': "MemCore",
                                           'input_prefix': "MEM_",
                                           'fifo_depth': fifo_depth,
                                           'dual_port': dual_port,
                                           'rf': rf})]

        real_pe = True

    # compute the actual size
    width, height = get_actual_size(width, height, io_sides)
    # these values are inclusive
    x_min, x_max, y_min, y_max = get_array_size(width, height, io_sides)
    # compute ratio
    tile_max = mem_ratio[-1]
    mem_tile_ratio = tile_max - mem_ratio[0]

    # creates all the cores here
    # we don't want duplicated cores when snapping into different interconnect
    # graphs
    cores = {}
    additional_core = {}
    altcore_ind = 0
    altcorelen = len(altcore) if altcore is not None else 0
    altcore_used = False

    intercore_mapping = None

    for x in range(width):
        # Only update the altcore if it had been used actually.
        if altcore_used:
            if altcore_ind == (altcorelen - 1):
                altcore_ind = 0
            else:
                altcore_ind += 1
            altcore_used = False
        for y in range(height):
            # empty corner
            if x in range(x_min) and y in range(y_min):
                core = None
            elif x in range(x_min) and y in range(y_max + 1, height):
                core = None
            elif x in range(x_max + 1, width) and y in range(y_min):
                core = None
            elif x in range(x_max + 1, width) and y in range(y_max + 1, height):
                core = None
            elif x in range(x_min) \
                    or x in range(x_max + 1, width) \
                    or y in range(y_min) \
                    or y in range(y_max + 1, height):
                if ready_valid:
                    core = IOCoreReadyValid(allow_bypass=False)
                elif use_io_valid:
                    core = IOCoreValid(config_addr_width=reg_addr_width,
                                       config_data_width=config_data_width)
                else:
                    core = IOCore()
            else:
                # now override this...to just use the altcore list to not waste space
                if altcore is not None:
                    altcore_used = True
                    if altcore[altcore_ind] == PeakCore:
                        core = PeakCore(pe_fc, ready_valid=ready_valid)
                    else:
                        core_type, core_kwargs = altcore[altcore_ind]
                        core = core_type(**core_kwargs)
                        if add_pond and core_type == CoreCombinerCore and "alu" in core.get_modes_supported():
                            intercore_mapping = core.get_port_remap()['alu']
                            additional_core[(x, y)] = PondCore(gate_flush=not harden_flush, ready_valid=ready_valid)
                        # Try adding pond?
                        elif add_pond and altcore[altcore_ind][0] == OnyxPECore:
                            additional_core[(x, y)] = PondCore(gate_flush=not harden_flush, ready_valid=ready_valid)
                else:
                    if tile_layout_option == 0:
                        use_mem_core = (x - x_min) % tile_max >= mem_tile_ratio
                    elif tile_layout_option == 1:
                        use_mem_core = (y - y_min) % tile_max >= mem_tile_ratio

                    if use_mem_core:
                        core = MemCore(use_sim_sram=use_sim_sram, gate_flush=not harden_flush, ready_valid=ready_valid)
                    else:
                        core = PeakCore(pe_fc, ready_valid=ready_valid)
                        if add_pond:
                            additional_core[(x, y)] = PondCore(gate_flush=not harden_flush, ready_valid=ready_valid)

            cores[(x, y)] = core

    def create_core(xx: int, yy: int):
        return cores[(xx, yy)]

    def create_additional_core(xx: int, yy: int):
        return additional_core.get((xx, yy), None)

    # pond may have inter-core connection
    if add_pond:
        # remap
        if intercore_mapping is not None:
            inter_core_connection_1 = {"PondTop_output_width_1_num_0": [intercore_mapping["bit0"]]}
            inter_core_connection_16 = {"PondTop_output_width_17_num_0": [intercore_mapping["data0"], intercore_mapping["data1"],
                                        intercore_mapping["data2"]],
                                        intercore_mapping["res"]: ["PondTop_input_width_17_num_0", "PondTop_input_width_17_num_1"]}
        else:
            inter_core_connection_1 = {"PondTop_output_width_1_num_0": ["bit0"]}
            inter_core_connection_16 = {"PondTop_output_width_17_num_0": ["data0", "data1", "data2"],
                                        "res": ["PondTop_input_width_17_num_0", "PondTop_input_width_17_num_1"]}
    else:
        inter_core_connection_1 = {}
        inter_core_connection_16 = {}

    # Specify input and output port connections.
    inputs = set()
    outputs = set()
    for core in cores.values():
        # Skip IO cores.
        if core is None or isinstance(core, IOCoreValid) or isinstance(core, IOCoreReadyValid):
            continue
        inputs |= {i.qualified_name() for i in core.inputs()}
        outputs |= {o.qualified_name() for o in core.outputs()}

    # inputs.remove("glb2io_1")
    # inputs.remove("glb2io_16")
    # inputs.remove("glb2io_17")
    # inputs.remove("glb2io_17_valid")
    # inputs.remove("io2glb_17_ready")
    # outputs.remove("io2glb_1")
    # outputs.remove("io2glb_16")
    # outputs.remove("io2glb_17")
    # outputs.remove("glb2io_17_ready")
    # outputs.remove("io2glb_17_valid")

    if add_pond:
        for core in additional_core.values():
            if isinstance(core, list):
                for actual_core in core:
                    inputs |= {i.qualified_name() for i in actual_core.inputs()}
                    outputs |= {o.qualified_name() for o in actual_core.outputs()}
            else:
                inputs |= {i.qualified_name() for i in core.inputs()}
                outputs |= {o.qualified_name() for o in core.outputs()}

            # Some Pond outputs will be connected to the SBs
            outputs.remove("PondTop_output_width_17_num_0")

    # This is slightly different from the original CGRA. Here we connect
    # input to every SB_IN and output to every SB_OUT.
    if port_conn_option is None:
        port_conns = {}
        in_conn = [(side, SwitchBoxIO.SB_IN) for side in SwitchBoxSide]
        out_conn = [(side, SwitchBoxIO.SB_OUT) for side in SwitchBoxSide]
        port_conns.update({input_: in_conn for input_ in inputs})
        port_conns.update({output: out_conn for output in outputs})
    else:
        port_conns = {}
        sb_side_dict = {
            1: [SwitchBoxSide.NORTH],
            2: [SwitchBoxSide.NORTH, SwitchBoxSide.SOUTH],
            3: [SwitchBoxSide.NORTH, SwitchBoxSide.SOUTH, SwitchBoxSide.EAST],
            4: SwitchBoxSide
        }
        [in_option, out_option] = port_conn_option
        in_conn = [(side, SwitchBoxIO.SB_IN) for side in sb_side_dict.get(in_option)]
        out_conn = [(side, SwitchBoxIO.SB_OUT) for side in sb_side_dict.get(out_option)]
        port_conns.update({input_: in_conn for input_ in inputs})
        port_conns.update({output: out_conn for output in outputs})

    if port_conn_override is not None:
        port_conns.update(port_conn_override)

    pipeline_regs = []
    if pipeline_regs_density is None:
        for track in range(num_tracks):
            for side in SwitchBoxSide:
                pipeline_regs.append((track, side))
    else:
        [regs_north, regs_south, regs_east, regs_west] = pipeline_regs_density
        for track in range(regs_north):
            pipeline_regs.append((track, SwitchBoxSide.NORTH))
        for track in range(regs_south):
            pipeline_regs.append((track, SwitchBoxSide.SOUTH))
        for track in range(regs_east):
            pipeline_regs.append((track, SwitchBoxSide.EAST))
        for track in range(regs_west):
            pipeline_regs.append((track, SwitchBoxSide.WEST))
    # if reg mode is off, reset to empty
    if not add_reg:
        pipeline_regs = []
    ics = {}

    track_list = list(range(num_tracks))
    io_in = {"f2io_1": [0], "f2io_17": [0]}
    io_out = {"io2f_1": track_list, "io2f_17": track_list}

    for bit_width in bit_widths:
        if io_sides & IOSide.None_:
            io_conn = None
        else:
            io_conn = {"in": io_in, "out": io_out}
        if bit_width == 1:
            inter_core_connection = inter_core_connection_1
        else:
            inter_core_connection = inter_core_connection_16
        ic = create_uniform_interconnect(width, height, bit_width,
                                         create_core,
                                         port_conns,
                                         {track_length: num_tracks},
                                         switchbox_type,
                                         pipeline_regs,
                                         io_sides=io_sides,
                                         io_conn=io_conn,
                                         additional_core_fn=create_additional_core,
                                         inter_core_connection=inter_core_connection)
        ics[bit_width] = ic

    interconnect = Interconnect(ics, reg_addr_width, config_data_width,
                                tile_id_width,
                                lift_ports=standalone,
                                stall_signal_width=1,
                                ready_valid=ready_valid)
    if hi_lo_tile_id:
        tile_id_physical(interconnect)
    if add_pd:
        add_power_domain(interconnect)

    # add hardened flush signal
    if harden_flush:
        wire_core_flush_pass(interconnect)

    interconnect.finalize()

    if global_signal_wiring == GlobalSignalWiring.Meso:
        apply_global_meso_wiring(interconnect)
    elif global_signal_wiring == GlobalSignalWiring.Fanout:
        apply_global_fanout_wiring(interconnect)
    elif global_signal_wiring == GlobalSignalWiring.ParallelMeso:
        apply_global_meso_wiring(interconnect)
    if add_pd:
        add_aon_read_config_data(interconnect)

    if pass_through_clk:
        clk_physical(interconnect, tile_layout_option)

    pipeline_global_signals(interconnect, pipeline_config_interval)

    return interconnect