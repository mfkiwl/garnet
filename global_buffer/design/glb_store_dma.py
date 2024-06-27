from kratos import Generator, always_ff, always_comb, posedge, const, resize, ext, clog2, clock_en
from global_buffer.design.glb_loop_iter import GlbLoopIter
from global_buffer.design.glb_sched_gen import GlbSchedGen
from global_buffer.design.glb_addr_gen import GlbAddrGen
from global_buffer.design.pipeline import Pipeline
from global_buffer.design.global_buffer_parameter import GlobalBufferParams
from global_buffer.design.glb_header import GlbHeader
from global_buffer.design.glb_clk_en_gen import GlbClkEnGen
from global_buffer.design.fifo import FIFO


class GlbStoreDma(Generator):
    def __init__(self, _params: GlobalBufferParams):
        super().__init__("glb_store_dma")
        self._params = _params
        self.header = GlbHeader(self._params)
        assert self._params.bank_data_width == self._params.cgra_data_width * 4

        self.clk = self.clock("clk")
        self.reset = self.reset("reset")
        self.clk_en_dma2bank = self.output("clk_en_dma2bank", 1)

        self.data_f2g = self.input("data_f2g", width=self._params.cgra_data_width,
                                   size=self._params.cgra_per_glb, packed=True)
        self.data_f2g_vld = self.input("data_f2g_vld", 1, size=self._params.cgra_per_glb, packed=True)
        self.data_f2g_rdy = self.output("data_f2g_rdy", 1, size=self._params.cgra_per_glb, packed=True)

        self.ctrl_f2g = self.input("ctrl_f2g", 1, size=self._params.cgra_per_glb, packed=True)

        self.wr_packet_dma2bank = self.output("wr_packet_dma2bank", self.header.wr_packet_t)
        self.wr_packet_dma2ring = self.output("wr_packet_dma2ring", self.header.wr_packet_t)

        self.cfg_tile_connected_prev = self.input("cfg_tile_connected_prev", 1)
        self.cfg_tile_connected_next = self.input("cfg_tile_connected_next", 1)
        self.cfg_st_dma_num_repeat = self.input("cfg_st_dma_num_repeat", clog2(self._params.queue_depth) + 1)
        self.cfg_st_dma_ctrl_mode = self.input("cfg_st_dma_ctrl_mode", 2)
        self.cfg_st_dma_ctrl_valid_mode = self.input("cfg_st_dma_ctrl_valid_mode", 2)
        self.cfg_data_network_latency = self.input("cfg_data_network_latency", self._params.latency_width)
        self.cfg_st_dma_header = self.input("cfg_st_dma_header", self.header.cfg_store_dma_header_t,
                                            size=self._params.queue_depth, explicit_array=True)
        self.cfg_data_network_f2g_mux = self.input("cfg_data_network_f2g_mux", self._params.cgra_per_glb)
        self.cfg_st_dma_num_blocks = self.input("cfg_st_dma_num_blocks", self._params.axi_data_width)
        self.cfg_st_dma_rv_seg_mode = self.input("cfg_st_dma_rv_seg_mode", 1)

        self.st_dma_start_pulse = self.input("st_dma_start_pulse", 1)
        self.st_dma_done_interrupt = self.output("st_dma_done_interrupt", 1)

        # localparam
        self.cgra_strb_width = self._params.cgra_data_width // 8
        self.cgra_strb_value = 2 ** (self._params.cgra_data_width // 8) - 1

        # local variables
        self.wr_packet_dma2bank_w = self.var("wr_packet_dma2bank_w", self.header.wr_packet_t)
        self.wr_packet_dma2ring_w = self.var("wr_packet_dma2ring_w", self.header.wr_packet_t)
        self.data_f2g_r = self.var("data_f2g_r", width=self._params.cgra_data_width,
                                   size=self._params.cgra_per_glb, packed=True)
        self.data_f2g_vld_r = self.var("data_f2g_vld_r", 1, size=self._params.cgra_per_glb, packed=True)
        self.ctrl_f2g_r = self.var("ctrl_f2g_r", 1, size=self._params.cgra_per_glb, packed=True)
        self.strm_data = self.var("strm_data", width=self._params.cgra_data_width)
        self.strm_data_valid = self.var("strm_data_valid", width=1)
        self.st_dma_done_pulse = self.var("st_dma_done_pulse", 1)
        self.st_dma_done_pulse_last = self.var("st_dma_done_pulse_last", 1)
        self.strm_wr_data_w = self.var("strm_wr_data_w", width=self._params.cgra_data_width)
        self.strm_wr_addr_w = self.var("strm_wr_addr_w", width=self._params.glb_addr_width)
        self.last_strm_wr_addr_r = self.var("last_strm_wr_addr_r", width=self._params.glb_addr_width)
        self.strm_wr_en_w = self.var("strm_wr_en_w", width=1)
        self.strm_data_sel = self.var("strm_data_sel", self._params.bank_byte_offset - self._params.cgra_byte_offset)

        self.bank_addr_match = self.var("bank_addr_match", 1)
        self.bank_wr_en = self.var("bank_wr_en", 1)
        self.bank_wr_addr = self.var("bank_wr_addr", width=self._params.glb_addr_width)
        self.bank_wr_data_cache_r = self.var("bank_wr_data_cache_r", self._params.bank_data_width)
        self.bank_wr_data_cache_w = self.var("bank_wr_data_cache_w", self._params.bank_data_width)
        self.bank_wr_strb_cache_r = self.var("bank_wr_strb_cache_r", self._params.bank_strb_width)
        self.bank_wr_strb_cache_w = self.var("bank_wr_strb_cache_w", self._params.bank_strb_width)

        self.done_pulse_w = self.var("done_pulse_w", 1)
        self.st_dma_start_pulse_next = self.var("st_dma_start_pulse_next", 1)
        self.st_dma_start_pulse_r = self.var("st_dma_start_pulse_r", 1)
        self.is_first = self.var("is_first", 1)
        self.is_last = self.var("is_last", 1)
        self.strm_run = self.var("strm_run", 1)
        self.loop_done = self.var("loop_done", 1)
        self.loop_done_muxed = self.var("loop_done_muxed", 1)
        self.cycle_valid = self.var("cycle_valid", 1)
        self.cycle_count = self.var("cycle_count", self._params.cycle_count_width)
        self.cycle_current_addr = self.var("cycle_current_addr", self._params.cycle_count_width)
        self.data_base_addr = self.var("data_base_addr", self._params.glb_addr_width + 1)
        self.data_current_addr = self.var("data_current_addr", self._params.glb_addr_width + 1)
        self.data_current_addr_pre = self.var("data_current_addr_pre", self._params.glb_addr_width + 1)
        self.loop_mux_sel = self.var("loop_mux_sel", clog2(self._params.store_dma_loop_level))
        self.repeat_cnt = self.var("repeat_cnt", clog2(self._params.queue_depth) + 1)

        # ready_valid controller
        self.block_done = self.var("block_done", 1)
        self.seg_done = self.var("seg_done", 1)
        self.is_last_block = self.var("is_last_block", 1)
        self.data_ready_g2f_w = self.var("data_ready_g2f_w", 1)
        self.cycle_counter_en = self.var("cycle_counter_en", 1)
        self.rv_mode_on = self.var("rv_mode_on", 1)
        self.fifo_almost_full_diff = self.var("fifo_almost_full_diff", clog2(self._params.store_dma_fifo_depth))
        self.iter_step_valid = self.var("iter_step_valid", 1)
        self.fifo_pop_ready = self.var("fifo_pop_ready", 1)
        self.data_cgra2fifo = self.var("data_cgra2fifo", self._params.cgra_data_width)
        self.data_fifo2dma = self.var("data_fifo2dma", self._params.cgra_data_width)
        self.fifo_push = self.var("fifo_push", 1)
        self.fifo_pop = self.var("fifo_pop", 1)
        self.fifo_empty = self.var("fifo_empty", 1)
        self.fifo_almost_full = self.var("fifo_almost_full", 1)
        self.fifo_full = self.var("fifo_full", 1)
        self.fifo2cgra_ready = self.var("fifo2cgra_ready", 1)
        self.rv_is_metadata = self.var("rv_is_metadata", 1)
        self.rv_is_addrdata = self.var("rv_is_addrdata", 1)
        self.rv_base_addr = self.var("rv_num_base_addr", self._params.glb_addr_width)
        self.rv_num_data_cnt = self.var("rv_num_data_cnt", self._params.cgra_data_width)
        self.rv_num_seg_cnt = self.var("rv_num_seg_cnt", 2)  # we would have a max of 2 seg
        self.rv_num_seg_cnt_total = self.var("rv_num_seg_cnt_total", 2)
        self.rv_num_blocks_cnt = self.var("rv_num_blocks_cnt", self._params.axi_data_width)

        if self._params.queue_depth != 1:
            self.queue_sel_r = self.var("queue_sel_r", max(1, clog2(self.repeat_cnt.width)))

        # Current dma header
        self.current_dma_header = self.var("current_dma_header", self.header.cfg_store_dma_header_t)
        if self._params.queue_depth == 1:
            self.wire(self.cfg_st_dma_header, self.current_dma_header)
        else:
            self.wire(self.cfg_st_dma_header[self.queue_sel_r], self.current_dma_header)

        if self._params.queue_depth != 1:
            self.add_always(self.queue_sel_ff)

        self.add_always(self.repeat_cnt_ff)
        self.add_always(self.is_first_ff)
        self.add_always(self.is_last_ff)
        self.add_always(self.strm_run_ff)
        self.add_always(self.st_dma_start_pulse_logic)
        self.add_always(self.st_dma_start_pulse_ff)
        self.add_always(self.cycle_counter)
        self.add_always(self.data_f2g_ff)
        self.add_always(self.data_f2g_logic)
        self.add_always(self.cycle_valid_comb)
        self.add_always(self.strm_wr_packet_comb)
        self.add_always(self.last_strm_wr_addr_ff)
        self.add_always(self.strm_data_sel_comb)
        self.add_always(self.bank_wr_packet_cache_comb)
        self.add_always(self.bank_wr_packet_cache_ff)
        self.add_always(self.bank_wr_packet_logic)
        self.add_always(self.wr_packet_ff)
        self.add_always(self.wr_packet_logic)
        self.add_dma2bank_clk_en()
        self.add_always(self.strm_done_pulse_logic)
        self.add_done_pulse_pipeline()
        self.add_done_pulse_last_pipeline()
        self.add_always(self.interrupt_ff)
        self.add_always(self.block_done_logic)
        self.add_always(self.seg_done_logic)
        self.add_always(self.loop_done_muxed_logic)
        self.add_always(self.rv_num_blocks_cnt_ff)
        self.add_always(self.rv_is_last_block_comb)
        self.add_always(self.rv_metadata_ff)
        self.add_always(self.rv_num_data_cnt_ff)
        self.add_always(self.data_ready_g2f_comb)
        self.add_always(self.rv_addrdata_ff)
        self.add_always(self.rv_base_addr_ff)
        self.add_always(self.data_addr_gen_start_addr_comb)
        self.add_always(self.rv_num_seg_cnt_ff)
        self.add_always(self.rv_num_seg_cnt_total_comb)

        # ready/valid control
        self.wire(self.rv_mode_on, (self.cfg_st_dma_ctrl_valid_mode == self._params.st_dma_valid_mode_ready_valid))

        # FIFO for ready/valid
        self.data_g2f_fifo = FIFO(self._params.cgra_data_width, self._params.store_dma_fifo_depth)
        self.add_child("data_f2g_fifo",
                       self.data_g2f_fifo,
                       clk=self.clk,
                       clk_en=clock_en(self.rv_mode_on),
                       reset=self.reset,
                       flush=self.st_dma_start_pulse_r,
                       data_in=self.data_cgra2fifo,
                       data_out=self.data_fifo2dma,
                       push=self.fifo_push,
                       pop=self.fifo_pop,
                       full=self.fifo_full,
                       empty=self.fifo_empty,
                       almost_full=self.fifo_almost_full,
                       almost_full_diff=const(2, clog2(self._params.store_dma_fifo_depth)),
                       almost_empty_diff=const(2, clog2(self._params.store_dma_fifo_depth)))

        self.wire(self.data_cgra2fifo, self.strm_data)
        self.wire(self.fifo_pop_ready, ~self.fifo_empty)
        self.wire(self.fifo_pop, ~self.fifo_empty & self.strm_run)
        self.wire(self.fifo_push, ~self.fifo_full & self.strm_data_valid)
        self.wire(self.fifo2cgra_ready, ~self.fifo_almost_full)

        # Loop iteration shared for cycle and data
        self.loop_iter = GlbLoopIter(self._params, loop_level=self._params.store_dma_loop_level)
        self.add_child("loop_iter",
                       self.loop_iter,
                       clk=self.clk,
                       clk_en=const(1, 1),
                       reset=self.reset,
                       step=self.iter_step_valid,
                       mux_sel_out=self.loop_mux_sel,
                       restart=self.loop_done)
        self.wire(self.loop_iter.dim, self.current_dma_header["dim"])
        for i in range(self._params.store_dma_loop_level):
            self.wire(self.loop_iter.ranges[i], self.current_dma_header[f"range_{i}"])

        # Cycle stride
        self.wire(self.cycle_counter_en, self.cfg_st_dma_ctrl_valid_mode == self._params.st_dma_valid_mode_static)
        self.cycle_stride_sched_gen = GlbSchedGen(self._params)
        self.add_child("cycle_stride_sched_gen",
                       self.cycle_stride_sched_gen,
                       clk=self.clk,
                       clk_en=clock_en(self.cycle_counter_en),
                       reset=self.reset,
                       restart=self.st_dma_start_pulse_r,
                       cycle_count=self.cycle_count,
                       current_addr=self.cycle_current_addr,
                       finished=self.loop_done_muxed,
                       valid_output=self.cycle_valid)

        self.cycle_stride_addr_gen = GlbAddrGen(self._params, loop_level=self._params.store_dma_loop_level)
        self.cycle_stride_addr_gen.p_addr_width.value = self._params.cycle_count_width
        self.cycle_stride_addr_gen.p_loop_level.value = self._params.store_dma_loop_level
        self.add_child("cycle_stride_addr_gen",
                       self.cycle_stride_addr_gen,
                       clk=self.clk,
                       clk_en=clock_en(self.cycle_counter_en),
                       reset=self.reset,
                       restart=self.st_dma_start_pulse_r,
                       step=self.iter_step_valid,
                       mux_sel=self.loop_mux_sel)
        self.wire(self.cycle_stride_addr_gen.addr_out, self.cycle_current_addr)
        self.wire(self.cycle_stride_addr_gen.start_addr, self.current_dma_header["cycle_start_addr"])
        for i in range(self._params.store_dma_loop_level):
            self.wire(self.cycle_stride_addr_gen.strides[i],
                      self.current_dma_header[f"cycle_stride_{i}"])

        # Data stride
        self.data_stride_addr_gen = GlbAddrGen(self._params, loop_level=self._params.store_dma_loop_level)
        self.data_stride_addr_gen.p_addr_width.value = self._params.glb_addr_width + 1
        self.data_stride_addr_gen.p_loop_level.value = self._params.store_dma_loop_level
        self.add_child("data_stride_addr_gen",
                       self.data_stride_addr_gen,
                       clk=self.clk,
                       clk_en=const(1, 1),
                       reset=self.reset,
                       restart=self.st_dma_start_pulse_r | self.rv_is_addrdata,
                    #    start_addr=self.data_base_addr,
                       step=self.iter_step_valid,
                       mux_sel=self.loop_mux_sel,
                       addr_out=self.data_current_addr)
        # In RV mode, the start address is given by the header of each block
        # self.wire(self.data_stride_addr_gen.start_addr, ext(self.current_dma_header["start_addr"],
        #                                                     self._params.glb_addr_width + 1))
        self.wire(self.data_stride_addr_gen.start_addr, self.data_base_addr)
        for i in range(self._params.store_dma_loop_level):
            self.wire(self.data_stride_addr_gen.strides[i], self.current_dma_header[f"stride_{i}"])

    @always_comb
    def block_done_logic(self):
        if self.rv_mode_on:
            self.block_done = self.strm_run & ~self.rv_is_metadata & ~self.rv_is_addrdata & self.seg_done &\
            (((self.rv_num_seg_cnt == 1) & self.fifo_pop_ready) | (self.rv_num_seg_cnt == 0))
        else:
            self.block_done = 0

    @always_comb
    def seg_done_logic(self):
        if self.rv_mode_on:
            self.seg_done = self.strm_run & ~self.rv_is_metadata & ~self.rv_is_addrdata & (
                ((self.rv_num_data_cnt == 1) & self.fifo_pop_ready) | (self.rv_num_data_cnt == 0))
        else:
            self.seg_done = 0

    @always_comb
    def loop_done_muxed_logic(self):
        if self.rv_mode_on:
            self.loop_done_muxed = self.block_done & self.is_last_block
        else:
            self.loop_done_muxed = self.loop_done

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rv_num_blocks_cnt_ff(self):
        if self.reset:
            self.rv_num_blocks_cnt = 0
        elif self.rv_mode_on:
            if self.st_dma_start_pulse_r:
                self.rv_num_blocks_cnt = self.cfg_st_dma_num_blocks
            elif self.block_done & (self.rv_num_blocks_cnt > 0):
                self.rv_num_blocks_cnt = self.rv_num_blocks_cnt - 1

    @always_comb
    def rv_is_last_block_comb(self):
        self.is_last_block = self.rv_num_blocks_cnt == 1

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rv_metadata_ff(self):
        if self.reset:
            self.rv_is_metadata = 0
        elif self.rv_mode_on:
            if (self.rv_is_addrdata & self.fifo_pop_ready) |\
                ((self.rv_num_seg_cnt != 1) & (self.rv_num_data_cnt == 1) & self.fifo_pop_ready):
                self.rv_is_metadata = 1
            elif self.rv_is_metadata & self.fifo_pop_ready:
                self.rv_is_metadata = 0
        # if self.reset:
        #     self.rv_is_metadata = 0
        # elif self.rv_mode_on:
        #     if self.st_dma_start_pulse_r:
        #         self.rv_is_metadata = 1
        #     elif (self.rv_mode_on & self.block_done & ~self.is_last_block):
        #         self.rv_is_metadata = 1
        #     elif self.rv_is_metadata & self.fifo_pop_ready:
        #         self.rv_is_metadata = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rv_num_data_cnt_ff(self):
        if self.reset:
            self.rv_num_data_cnt = 0
        else:
            if self.st_dma_start_pulse_r:
                self.rv_num_data_cnt = 0
            elif self.strm_run & self.rv_is_metadata & self.fifo_pop_ready:
                self.rv_num_data_cnt = self.data_fifo2dma
            elif (self.rv_num_data_cnt > 0) & self.fifo_pop_ready:
                self.rv_num_data_cnt = self.rv_num_data_cnt - 1

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def repeat_cnt_ff(self):
        if self.reset:
            self.repeat_cnt = 0
        else:
            if self.cfg_st_dma_ctrl_mode == 2:
                if self.st_dma_done_pulse:
                    if (self.repeat_cnt + 1) < self.cfg_st_dma_num_repeat:
                        self.repeat_cnt += 1
            elif self.cfg_st_dma_ctrl_mode == 3:
                if self.st_dma_done_pulse:
                    if (((self.repeat_cnt + 1) < self.cfg_st_dma_num_repeat)
                            & ((self.repeat_cnt + 1) < self._params.queue_depth)):
                        self.repeat_cnt += 1

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def queue_sel_ff(self):
        if self.reset:
            self.queue_sel_r = 0
        else:
            if self.cfg_st_dma_ctrl_mode == 3:
                if self.st_dma_done_pulse:
                    if (self.repeat_cnt + 1) < self.cfg_st_dma_num_repeat:
                        self.queue_sel_r = self.queue_sel_r + 1
            else:
                self.queue_sel_r = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def is_first_ff(self):
        if self.reset:
            self.is_first = 0
        else:
            if self.st_dma_start_pulse_r:
                self.is_first = 1
            elif self.strm_wr_en_w:
                self.is_first = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def is_last_ff(self):
        if self.reset:
            self.is_last = 0
        else:
            if self.loop_done_muxed:
                self.is_last = 1
            elif self.bank_wr_en:
                self.is_last = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def strm_run_ff(self):
        if self.reset:
            self.strm_run = 0
        else:
            if self.st_dma_start_pulse_r:
                self.strm_run = 1
            elif self.loop_done_muxed:
                self.strm_run = 0

    @always_comb
    def st_dma_start_pulse_logic(self):
        if self.cfg_st_dma_ctrl_mode == 0:
            self.st_dma_start_pulse_next = 0
        elif self.cfg_st_dma_ctrl_mode == 1:
            self.st_dma_start_pulse_next = (~self.strm_run) & self.st_dma_start_pulse
        elif (self.cfg_st_dma_ctrl_mode == 2) | (self.cfg_st_dma_ctrl_mode == 3):
            self.st_dma_start_pulse_next = (((~self.strm_run) & self.st_dma_start_pulse)
                                            | ((self.st_dma_done_pulse)
                                               & ((self.repeat_cnt + 1) < self.cfg_st_dma_num_repeat)))
        else:
            self.st_dma_start_pulse_next = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def st_dma_start_pulse_ff(self):
        if self.reset:
            self.st_dma_start_pulse_r = 0
        else:
            if self.st_dma_start_pulse_r:
                self.st_dma_start_pulse_r = 0
            else:
                self.st_dma_start_pulse_r = self.st_dma_start_pulse_next

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def cycle_counter(self):
        if self.reset:
            self.cycle_count = 0
        else:
            if self.st_dma_start_pulse_r:
                self.cycle_count = 0
            elif self.loop_done_muxed:
                self.cycle_count = 0
            elif self.cycle_counter_en & self.strm_run:
                self.cycle_count = self.cycle_count + 1

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def data_f2g_ff(self):
        if self.reset:
            self.data_f2g_r = 0
            self.data_f2g_vld_r = 0
            self.ctrl_f2g_r = 0
        else:
            for i in range(self._params.cgra_per_glb):
                self.data_f2g_r[i] = self.data_f2g[i]
                self.data_f2g_vld_r[i] = self.data_f2g_vld[i]
                self.ctrl_f2g_r[i] = self.ctrl_f2g[i]

    @always_comb
    def data_ready_g2f_comb(self):
        if self.rv_mode_on:
            self.data_ready_g2f_w = self.fifo2cgra_ready
        else:
            self.data_ready_g2f_w = 0

    @always_comb
    def data_f2g_logic(self):
        self.strm_data = 0
        self.strm_data_valid = 0
        for i in range(self._params.cgra_per_glb):
            if self.cfg_data_network_f2g_mux[i] == 1:
                self.strm_data = self.data_f2g_r[i]
                self.data_f2g_rdy[i] = self.data_ready_g2f_w
                if self.rv_mode_on:
                    self.strm_data_valid = self.data_f2g_vld_r[i]
                else:
                    self.strm_data_valid = self.ctrl_f2g_r[i]
            else:
                self.strm_data = self.strm_data
                self.strm_data_valid = self.strm_data_valid
                self.data_f2g_rdy[i] = 0

    @always_comb
    def cycle_valid_comb(self):
        if self.cycle_counter_en:
            self.iter_step_valid = self.cycle_valid
        elif self.rv_mode_on:
            self.iter_step_valid = self.strm_run & self.fifo_pop_ready & ~self.rv_is_addrdata
        else:
            self.iter_step_valid = self.strm_data_valid

    @always_comb
    def strm_wr_packet_comb(self):
        self.strm_wr_en_w = self.iter_step_valid
        if self.rv_mode_on:
            self.strm_wr_addr_w = resize(self.data_current_addr, self._params.glb_addr_width)
            self.strm_wr_data_w = self.data_fifo2dma
        else:
            self.strm_wr_addr_w = resize(self.data_current_addr, self._params.glb_addr_width)
            self.strm_wr_data_w = self.strm_data

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def last_strm_wr_addr_ff(self):
        if self.reset:
            self.last_strm_wr_addr_r = 0
        else:
            if self.strm_wr_en_w:
                self.last_strm_wr_addr_r = self.strm_wr_addr_w

    @always_comb
    def strm_data_sel_comb(self):
        self.strm_data_sel = self.strm_wr_addr_w[self._params.bank_byte_offset - 1, self._params.cgra_byte_offset]

    @always_comb
    def bank_wr_packet_cache_comb(self):
        self.bank_wr_strb_cache_w = self.bank_wr_strb_cache_r
        self.bank_wr_data_cache_w = self.bank_wr_data_cache_r
        # First, if cached data is written to memory, clear it.
        if self.bank_wr_en:
            self.bank_wr_strb_cache_w = 0
            self.bank_wr_data_cache_w = 0
        # Next, save data to cache
        if self.strm_wr_en_w:
            if self.strm_data_sel == 0:
                self.bank_wr_strb_cache_w[self.cgra_strb_width - 1,
                                          0] = const(self.cgra_strb_value, self.cgra_strb_width)
                self.bank_wr_data_cache_w[self._params.cgra_data_width - 1, 0] = self.strm_wr_data_w
            elif self.strm_data_sel == 1:
                self.bank_wr_strb_cache_w[self.cgra_strb_width * 2 - 1,
                                          self.cgra_strb_width] = const(self.cgra_strb_value,
                                                                        self.cgra_strb_width)
                self.bank_wr_data_cache_w[self._params.cgra_data_width * 2 - 1,
                                          self._params.cgra_data_width] = self.strm_wr_data_w
            elif self.strm_data_sel == 2:
                self.bank_wr_strb_cache_w[self.cgra_strb_width * 3 - 1,
                                          self.cgra_strb_width * 2] = const(self.cgra_strb_value,
                                                                            self.cgra_strb_width)
                self.bank_wr_data_cache_w[self._params.cgra_data_width * 3 - 1,
                                          self._params.cgra_data_width * 2] = self.strm_wr_data_w
            elif self.strm_data_sel == 3:
                self.bank_wr_strb_cache_w[self.cgra_strb_width * 4 - 1,
                                          self.cgra_strb_width * 3] = const(self.cgra_strb_value,
                                                                            self.cgra_strb_width)
                self.bank_wr_data_cache_w[self._params.cgra_data_width * 4 - 1,
                                          self._params.cgra_data_width * 3] = self.strm_wr_data_w
            else:
                self.bank_wr_strb_cache_w = self.bank_wr_strb_cache_r
                self.bank_wr_data_cache_w = self.bank_wr_data_cache_r

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def bank_wr_packet_cache_ff(self):
        if self.reset:
            self.bank_wr_strb_cache_r = 0
            self.bank_wr_data_cache_r = 0
        else:
            self.bank_wr_strb_cache_r = self.bank_wr_strb_cache_w
            self.bank_wr_data_cache_r = self.bank_wr_data_cache_w

    @always_comb
    def bank_wr_packet_logic(self):
        self.bank_addr_match = (self.strm_wr_addr_w[self._params.glb_addr_width - 1, self._params.bank_byte_offset]
                                == self.last_strm_wr_addr_r[self._params.glb_addr_width - 1,
                                                            self._params.bank_byte_offset])
        self.bank_wr_en = ((self.strm_wr_en_w & (~self.bank_addr_match) & (~self.is_first)) | self.is_last)
        self.bank_wr_addr = self.last_strm_wr_addr_r

    @always_comb
    def wr_packet_logic(self):
        if self.cfg_tile_connected_next | self.cfg_tile_connected_prev:
            self.wr_packet_dma2bank_w = 0
            self.wr_packet_dma2ring_w['wr_en'] = self.bank_wr_en
            self.wr_packet_dma2ring_w['wr_strb'] = self.bank_wr_strb_cache_r
            self.wr_packet_dma2ring_w['wr_data'] = self.bank_wr_data_cache_r
            self.wr_packet_dma2ring_w['wr_addr'] = self.bank_wr_addr
        else:
            self.wr_packet_dma2bank_w['wr_en'] = self.bank_wr_en
            self.wr_packet_dma2bank_w['wr_strb'] = self.bank_wr_strb_cache_r
            self.wr_packet_dma2bank_w['wr_data'] = self.bank_wr_data_cache_r
            self.wr_packet_dma2bank_w['wr_addr'] = self.bank_wr_addr
            self.wr_packet_dma2ring_w = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def wr_packet_ff(self):
        if self.reset:
            self.wr_packet_dma2bank = 0
            self.wr_packet_dma2ring = 0
        else:
            self.wr_packet_dma2bank = self.wr_packet_dma2bank_w
            self.wr_packet_dma2ring = self.wr_packet_dma2ring_w

    def add_dma2bank_clk_en(self):
        self.clk_en_gen = GlbClkEnGen(cnt=self._params.tile2sram_wr_delay + self._params.wr_clk_en_margin)
        self.clk_en_gen.p_cnt.value = self._params.tile2sram_wr_delay + self._params.wr_clk_en_margin
        self.dma2bank_clk_en = self.var("dma2bank_clk_en", 1)
        self.add_child("dma2bank_clk_en_gen",
                       self.clk_en_gen,
                       clk=self.clk,
                       reset=self.reset,
                       enable=self.wr_packet_dma2bank_w['wr_en'],
                       clk_en=self.dma2bank_clk_en
                       )
        self.wire(self.clk_en_dma2bank, self.dma2bank_clk_en)

    @always_comb
    def strm_done_pulse_logic(self):
        self.done_pulse_w = self.loop_done_muxed & self.strm_run

    def add_done_pulse_pipeline(self):
        maximum_latency = (2 * self._params.max_num_chain + self._params.tile2sram_wr_delay
                           + self._params.chain_latency_overhead)
        latency_width = clog2(maximum_latency)
        self.done_pulse_d_arr = self.var(
            "done_pulse_d_arr", 1, size=maximum_latency, explicit_array=True)
        self.done_pulse_pipeline = Pipeline(width=1,
                                            depth=maximum_latency,
                                            flatten_output=True)
        self.add_child("done_pulse_pipeline",
                       self.done_pulse_pipeline,
                       clk=self.clk,
                       clk_en=const(1, 1),
                       reset=self.reset,
                       in_=self.done_pulse_w,
                       out_=self.done_pulse_d_arr)

        self.wire(self.st_dma_done_pulse,
                  self.done_pulse_d_arr[(resize(self.cfg_data_network_latency, latency_width)
                                         + self._params.tile2sram_wr_delay)])

    def add_done_pulse_last_pipeline(self):
        self.interrupt_last_pipeline = Pipeline(width=1, depth=self._params.interrupt_cnt)
        self.add_child("st_dma_interrupt_pipeline",
                       self.interrupt_last_pipeline,
                       clk=self.clk,
                       clk_en=const(1, 1),
                       reset=self.reset,
                       in_=self.st_dma_done_pulse,
                       out_=self.st_dma_done_pulse_last)

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def interrupt_ff(self):
        if self.reset:
            self.st_dma_done_interrupt = 0
        else:
            if self.st_dma_done_pulse:
                self.st_dma_done_interrupt = 1
            elif self.st_dma_done_pulse_last:
                self.st_dma_done_interrupt = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rv_addrdata_ff(self):
        if self.reset:
            self.rv_is_addrdata = 0
        elif self.rv_mode_on:
            if self.st_dma_start_pulse_r:
                self.rv_is_addrdata = 1
            elif (self.rv_mode_on & self.block_done & ~self.is_last_block):
                self.rv_is_addrdata = 1
            elif self.rv_is_addrdata & self.fifo_pop_ready:
                self.rv_is_addrdata = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rv_base_addr_ff(self):
        if self.reset:
            self.rv_base_addr = 0
        elif self.rv_is_addrdata:
            self.rv_base_addr = self.current_dma_header["start_addr"] + self.data_fifo2dma

    @always_comb
    def data_addr_gen_start_addr_comb(self):
        if self.rv_mode_on:
            self.data_base_addr = ext(self.rv_base_addr, self._params.glb_addr_width + 1)
        else:
            self.data_base_addr = ext(self.current_dma_header["start_addr"],
                                                       self._params.glb_addr_width + 1)

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rv_num_seg_cnt_ff(self):
        if self.reset:
            self.rv_num_seg_cnt = 0
        else:
            if self.st_dma_start_pulse_r:
                self.rv_num_seg_cnt = 0
            elif self.strm_run & self.rv_is_addrdata & self.fifo_pop_ready:
                self.rv_num_seg_cnt = self.rv_num_seg_cnt_total
            elif ((self.rv_num_data_cnt == 1) | (self.rv_is_metadata & (self.data_fifo2dma == 0))) & self.fifo_pop_ready:
                self.rv_num_seg_cnt = self.rv_num_seg_cnt - 1

    @always_comb
    def rv_num_seg_cnt_total_comb(self):
        if self.cfg_st_dma_rv_seg_mode:
            self.rv_num_seg_cnt_total = 2
        else:
            self.rv_num_seg_cnt_total = 1