import dataclasses
import math
import os


@dataclasses.dataclass(eq=True, frozen=False)
class GlobalBufferParams:
    # architecture parameters
    num_prr: int = 16
    num_cgra_tiles: int = 32
    num_glb_tiles: int = 16
    banks_per_tile: int = 2
    bank_addr_width: int = 17
    bank_data_width: int = 64
    cgra_data_width: int = 16
    axi_data_width: int = 32
    cgra_axi_addr_width: int = 13
    cgra_axi_data_width: int = 32
    cgra_cfg_addr_width: int = 32
    cgra_cfg_data_width: int = 32

    # cell parameters
    cg_cell_name: str = "CKLNQD1BWP16P90"
    sram_macro_name: str = "TS1N16FFCLLSBLVTC2048X64M8SW"
    sram_macro_depth: int = 2048

    @property
    def num_prr_width(self):
        return math.ceil(math.log(self.num_prr, 2))

    @property
    def tile_sel_addr_width(self):
        return math.ceil(math.log(self.num_glb_tiles, 2))

    # cgra tiles per glb tile
    @property
    def cgra_per_glb(self):
        return self.num_cgra_tiles // self.num_glb_tiles  # 2

    # bank parameters
    @property
    def bank_sel_addr_width(self):
        return math.ceil(math.log(self.banks_per_tile, 2))

    @property
    def bank_strb_width(self):
        return math.ceil(self.bank_data_width / 8)

    @property
    def bank_byte_offset(self):
        return math.ceil(math.log(self.bank_data_width / 8, 2))

    # glb parameters
    @property
    def glb_addr_width(self):
        return self.bank_addr_width + self.bank_sel_addr_width + self.tile_sel_addr_width

    # cgra data parameters
    @property
    def cgra_byte_offset(self):
        return math.ceil(math.log(self.cgra_data_width / 8, 2))

    # axi parameters
    @property
    def axi_addr_width(self):
        return self.cgra_axi_addr_width - 1

    @property
    def axi_addr_reg_width(self):
        return (self.axi_addr_width
                - math.ceil(math.log(self.num_glb_tiles, 2)) - math.ceil(math.log(self.cgra_axi_data_width / 8, 2)))

    @property
    def axi_strb_width(self):
        return math.ceil(self.axi_data_width / 8)

    @property
    def axi_byte_offset(self):
        return math.ceil(math.log(self.axi_data_width / 8, 2))

    # max number of bitstream in dma header
    @property
    def max_num_cfg_width(self):
        return self.glb_addr_width - self.bank_byte_offset

    # cgra config parameters

    # dma address generator
    queue_depth: int = 1
    loop_level: int = 7

    # dma latency
    chain_latency_overhead: int = 3
    latency_width: int = math.ceil(math.log(num_glb_tiles * 2 + chain_latency_overhead, 2))
    pcfg_latency_width: int = math.ceil(math.log(num_glb_tiles * 3 + chain_latency_overhead, 2))

    # pipeline depth
    sram_macro_read_latency: int = 1  # Constant
    glb_dma2bank_delay: int = 1  # Constant
    glb_sw2bank_pipeline_depth: int = 0
    glb_bank2sw_pipeline_depth: int = 1
    glb_bank_memory_pipeline_depth: int = 0
    sram_gen_pipeline_depth: int = 0
    sram_gen_output_pipeline_depth: int = 0
    gls_pipeline_depth: int = 0
    tile2sram_wr_delay: int = (glb_dma2bank_delay + glb_sw2bank_pipeline_depth
                               + glb_bank_memory_pipeline_depth + sram_gen_pipeline_depth)
    tile2sram_rd_delay: int = (glb_dma2bank_delay + glb_sw2bank_pipeline_depth + glb_bank_memory_pipeline_depth
                               + sram_gen_pipeline_depth + glb_bank2sw_pipeline_depth + sram_gen_output_pipeline_depth
                               + sram_macro_read_latency)

    bankmux2sram_wr_delay: int = glb_sw2bank_pipeline_depth + glb_bank_memory_pipeline_depth + sram_gen_pipeline_depth
    bankmux2sram_rd_delay: int = (glb_sw2bank_pipeline_depth + glb_bank_memory_pipeline_depth + sram_gen_pipeline_depth
                                  + glb_bank2sw_pipeline_depth + sram_gen_output_pipeline_depth
                                  + sram_macro_read_latency
                                  )
    rd_clk_en_margin: int = 3
    wr_clk_en_margin: int = 3
    proc_clk_en_margin: int = 4

    is_sram_stub: int = 0

    # cycle count data width
    cycle_count_width: int = 16

    # interrupt cnt
    interrupt_cnt: int = 5


def gen_global_buffer_params(**kwargs):
    # User-defined parameters
    num_prr = kwargs.pop('num_prr', 16)
    num_glb_tiles = kwargs.pop('num_glb_tiles', 16)
    num_cgra_cols = kwargs.pop('num_cgra_cols', 32)
    glb_tile_mem_size = kwargs.pop('glb_tile_mem_size', 256)
    bank_data_width = kwargs.pop('bank_data_width', 64)
    banks_per_tile = kwargs.pop('banks_per_tile', 2)
    cgra_axi_addr_width = kwargs.pop('cgra_axi_addr_width', 13)
    axi_data_width = kwargs.pop('axi_data_width', 32)
    cfg_addr_width = kwargs.pop('cfg_addr_width', 32)
    cfg_data_width = kwargs.pop('cfg_data_width', 32)
    is_sram_stub = kwargs.pop('is_sram_stub', 0)

    # Check if there is unused kwargs
    if kwargs:
        raise Exception(f"{kwargs.keys()} are not supported parameters")

    # the number of glb tiles is half the number of cgra columns
    assert 2 * num_glb_tiles == num_cgra_cols

    def _power_of_two(n):
        if n == 1:
            return True
        elif n % 2 != 0 or n == 0:
            return False
        return _power_of_two(n / 2)

    assert _power_of_two(glb_tile_mem_size) is True

    # Unit is KB, so we add 10
    bank_addr_width = (math.ceil(math.log(glb_tile_mem_size, 2))
                       - math.ceil(math.log(banks_per_tile, 2)) + 10)

    params = GlobalBufferParams(num_prr=num_prr,
                                num_glb_tiles=num_glb_tiles,
                                num_cgra_tiles=num_cgra_cols,
                                banks_per_tile=banks_per_tile,
                                bank_data_width=bank_data_width,
                                bank_addr_width=bank_addr_width,
                                cgra_axi_addr_width=cgra_axi_addr_width,
                                axi_data_width=axi_data_width,
                                cgra_cfg_addr_width=cfg_addr_width,
                                cgra_cfg_data_width=cfg_data_width,
                                is_sram_stub=is_sram_stub,
                                )
    return params


def gen_header_files(params, svh_filename, h_filename, header_name):
    mod_params = dataclasses.asdict(params)
    folder = svh_filename.rsplit('/', 1)[0]
    # parameter pass to systemverilog package
    if not os.path.exists(folder):
        os.makedirs(folder)

    with open(svh_filename, "w") as f:
        f.write(f"`ifndef {header_name.upper()}_PARAM\n")
        f.write(f"`define {header_name.upper()}_PARAM\n")
        f.write(f"package {header_name}_param;\n")
        for k, v in mod_params.items():
            if type(v) == str:
                continue
            v = int(v)
            f.write(f"localparam int {k.upper()} = {v};\n")
        f.write(f"endpackage\n")
        f.write(f"`endif\n")

    with open(h_filename, "w") as f:
        f.write(f"#pragma once\n")
        for k, v in mod_params.items():
            if type(v) == str:
                continue
            v = int(v)
            f.write(f"#define {k.upper()} {v}\n")
