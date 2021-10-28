from kratos import Generator, always_ff, always_comb, posedge, resize, concat
from global_buffer.design.pipeline import Pipeline
from global_buffer.design.global_buffer_parameter import GlobalBufferParams
from global_buffer.design.glb_header import GlbHeader
import math


class GlbCoreLoadDma(Generator):
    def __init__(self, _params: GlobalBufferParams):
        super().__init__("glb_core_load_dma")
        self._params = _params
        self.header = GlbHeader(self._params)

        self.clk = self.clock("clk")
        self.clk_en = self.clock_en("clk_en")
        self.reset = self.reset("reset")

        self.data_g2f = self.output(
            "data_g2f", width=self._params.cgra_data_width)
        self.data_valid_g2f = self.output("data_valid_g2f", width=1)

        self.rdrq_packet = self.output(
            "rdrq_packet", self.header.rdrq_packet_t)
        self.rdrs_packet = self.input("rdrs_packet", self.header.rdrs_packet_t)

        self.cfg_ld_dma_ctrl_use_valid = self.input(
            "cfg_ld_dma_ctrl_use_valid", 1)
        self.cfg_ld_dma_ctrl_mode = self.input("cfg_ld_dma_ctrl_mode", 2)
        self.cfg_data_network_latency = self.input(
            "cfg_data_network_latency", self._params.latency_width)
        self.cfg_ld_dma_header = self.input(
            "cfg_ld_dma_header", self.header.cfg_ld_dma_header_t, size=self._params.queue_depth)

        self.ld_dma_header_clr = self.output(
            "ld_dma_header_clr", width=self._params.queue_depth)

        self.ld_dma_start_pulse = self.input("ld_dma_start_pulse", 1)
        self.ld_dma_done_pulse = self.output("ld_dma_done_pulse", 1)

        # local parameter
        self.default_latency = 8

        # local variables
        self.dma_header_r = self.var(
            "dma_header_r", self.header.cfg_ld_dma_header_t, size=self._params.queue_depth)

        self.dma_validate_r = self.var(
            "dma_validate_r", width=self._params.queue_depth)
        self.dma_validate_pulse = self.var(
            "dma_validate_pulse", width=self._params.queue_depth)
        self.dma_invalidate_pulse = self.var(
            "dma_invalidate_pulse", width=self._params.queue_depth)

        self.dma_active_r = self.var("dma_active", 1)
        self.dma_active_next = self.var("dma_active_next", 1)

        self.strm_data = self.var("strm_data", self._params.cgra_data_width)
        self.strm_data_r = self.var(
            "strm_data_r", self._params.cgra_data_width)
        self.strm_data_valid = self.var("strm_data_valid", 1)
        self.strm_data_valid_r = self.var("strm_data_valid_r", 1)
        self.strm_data_sel = self.var(
            "strm_data_sel", self._params.bank_byte_offset-self._params.cgra_byte_offset)
        self.strm_data_sel_resize = self.var(
            "strm_data_sel_resize", 6)

        self.last_strm_w = self.var("last_strm_w", 1)
        self.strm_run_r = self.var("strm_run_r", 1)
        self.strm_run_next = self.var("strm_run_next", 1)

        self.num_active_words_w = self.var(
            "num_active_words_w", self._params.max_num_words_width)
        self.num_inactive_words_w = self.var(
            "num_inactive_words_w", self._params.max_num_words_width)

        self.strm_active_r = self.var("strm_active_r", 1)
        self.strm_active_next = self.var("strm_active_next", 1)
        self.strm_active_cnt_r = self.var(
            "strm_active_cnt_r", self._params.max_num_words_width)
        self.strm_active_cnt_next = self.var(
            "strm_active_cnt_next", self._params.max_num_words_width)
        self.strm_inactive_cnt_r = self.var(
            "strm_inactive_cnt_r", self._params.max_num_words_width)
        self.strm_inactive_cnt_next = self.var(
            "strm_inactive_cnt_next", self._params.max_num_words_width)

        self.start_addr_r = self.var(
            "start_addr_r", self._params.glb_addr_width)
        self.strm_rd_en_r = self.var("strm_rd_en_r", 1)
        self.strm_rd_addr_r = self.var(
            "strm_rd_addr_r", self._params.glb_addr_width)
        self.strm_rd_addr_w = self.var(
            "strm_rd_addr_w", self._params.glb_addr_width)

        self.queue_sel_r = self.var("queue_sel_r", math.ceil(
            math.log(self._params.queue_depth, 2)))
        self.queue_sel_next = self.var("queue_sel_next", math.ceil(
            math.log(self._params.queue_depth, 2)))

        self.iter_cnt_incr = self.var(
            "iter_cnt_incr", width=1, size=self._params.loop_level)
        self.iter_cnt_next = self.var(
            "iter_cnt_next", width=self._params.max_num_words_width, size=self._params.loop_level)
        self.iter_cnt_r = self.var(
            "iter_cnt_r", width=self._params.max_num_words_width, size=self._params.loop_level)
        self.iter_range_r = self.var(
            "iter_range_r", self._params.axi_data_width, size=self._params.loop_level)
        self.iter_stride_r = self.var(
            "iter_stride_r", self._params.axi_data_width, size=self._params.loop_level)

        self.ld_dma_start_pulse_next = self.var("ld_dma_start_pulse_next", 1)
        self.ld_dma_start_pulse_r = self.var("ld_dma_start_pulse_r", 1)
        self.ld_dma_start_pulse_d2 = self.var("ld_dma_start_pulse_d2", 1)
        self.ld_dma_start_pulse_pipeline = Pipeline(width=1,
                                                    depth=2,
                                                    is_clk_en=True)

        self.add_child("ld_dma_start_pulse_pipeline",
                       self.ld_dma_start_pulse_pipeline,
                       clk=self.clk,
                       clk_en=self.clk_en,
                       reset=self.reset,
                       in_=self.ld_dma_start_pulse_r,
                       out_=self.ld_dma_start_pulse_d2)

        self.ld_dma_done_pulse_w = self.var("ld_dma_done_pulse_w", 1)

        self.bank_addr_match = self.var("bank_addr_match", 1)
        self.bank_rdrq_rd_en = self.var("bank_rdrq_rd_en", 1)
        self.bank_rdrq_rd_addr = self.var(
            "bank_rdrq_rd_addr", self._params.glb_addr_width)
        self.bank_rdrs_data_cache_r = self.var(
            "bank_rdrs_data_cache_r", self._params.bank_data_width)

        self.add_strm_data_start_pulse_pipeline()
        self.add_ld_dma_done_pulse_pipeline()
        self.add_strm_rd_en_pipeline()
        self.add_strm_rd_addr_pipeline()
        self.add_always(self.ld_dma_start_pulse_logic)
        self.add_always(self.ld_dma_start_pulse_ff)
        self.add_always(self.strm_data_ff)
        self.add_always(self.strm_data_mux)
        self.add_always(self.dma_validate_ff)
        self.add_always(self.dma_validate_pulse_gen)
        self.add_always(self.dma_invalidate_pulse_gen)
        self.add_always(self.assign_ld_dma_header_hwclr)
        self.add_always(self.dma_header_ff)
        self.add_always(self.dma_active_logic)
        self.add_always(self.dma_active_ff)
        self.add_always(self.strm_run_logic)
        self.add_always(self.strm_run_ff)
        self.add_always(self.num_active_words_mux_logic)
        self.add_always(self.cycle_active_logic)
        self.add_always(self.cycle_active_ff)
        self.add_always(self.iter_ff)
        self.add_always(self.iter_cnt_logic)
        self.add_always(self.iter_cnt_ff)
        self.add_always(self.last_strm_logic)
        self.add_always(self.ld_dma_done_pulse_logic)
        self.add_always(self.strm_addr_logic)
        self.add_always(self.strm_rdrq_packet_ff)
        self.add_always(self.bank_rdrq_packet_logic)
        self.add_always(self.bank_rdrs_data_cache_ff)
        self.add_always(self.strm_data_logic)
        self.add_always(self.queue_sel_logic)
        self.add_always(self.queue_sel_ff)

    @always_comb
    def ld_dma_start_pulse_logic(self):
        if self.cfg_ld_dma_ctrl_mode == 0:
            self.ld_dma_start_pulse_next = 0
        elif self.cfg_ld_dma_ctrl_mode == 1:
            self.ld_dma_start_pulse_next = (
                ~self.strm_run_r) & (self.ld_dma_start_pulse)
        elif (self.cfg_ld_dma_ctrl_mode == 2) | (self.cfg_ld_dma_ctrl_mode == 3):
            self.ld_dma_start_pulse_next = (((~self.dma_active_r) & (self.ld_dma_start_pulse))
                                            | ((self.dma_active_r) & (self.dma_header_r[self.queue_sel_r]['validate']) & (~self.strm_run_r)))
        else:
            self.ld_dma_start_pulse_next = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def ld_dma_start_pulse_ff(self):
        if self.reset:
            self.ld_dma_start_pulse_r = 0
        elif self.clk_en:
            if self.ld_dma_start_pulse_r:
                self.ld_dma_start_pulse_r = 0
            else:
                self.ld_dma_start_pulse_r = self.ld_dma_start_pulse_next

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def strm_data_ff(self):
        if self.reset:
            self.strm_data_r = 0
            self.strm_data_valid_r = 0
        elif self.clk_en:
            self.strm_data_r = self.strm_data
            self.strm_data_valid_r = self.strm_data_valid

    @always_comb
    def strm_data_mux(self):
        if self.cfg_ld_dma_ctrl_use_valid:
            self.data_g2f = self.strm_data_r
            self.data_valid_g2f = self.strm_data_valid_r
        else:
            self.data_g2f = self.strm_data_r
            self.data_valid_g2f = self.strm_data_start_pulse

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def dma_validate_ff(self):
        if self.reset:
            for i in range(self._params.queue_depth):
                self.dma_validate_r[i] = 0
        elif self.clk_en:
            for i in range(self._params.queue_depth):
                self.dma_validate_r[i] = self.cfg_ld_dma_header[i]['validate']

    @always_comb
    def dma_validate_pulse_gen(self):
        for i in range(self._params.queue_depth):
            self.dma_validate_pulse[i] = self.cfg_ld_dma_header[i]['validate'] & (
                ~self.dma_validate_r[i])

    @always_comb
    def dma_invalidate_pulse_gen(self):
        for i in range(self._params.queue_depth):
            self.dma_invalidate_pulse[i] = (
                self.queue_sel_r == i) & self.ld_dma_start_pulse_r

    @always_comb
    def assign_ld_dma_header_hwclr(self):
        for i in range(self._params.queue_depth):
            self.ld_dma_header_clr[i] = self.dma_invalidate_pulse[i]

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def dma_header_ff(self):
        if self.reset:
            for i in range(self._params.queue_depth):
                self.dma_header_r[i] = 0
        elif self.clk_en:
            for i in range(self._params.queue_depth):
                if self.dma_validate_pulse[i]:
                    self.dma_header_r[i] = self.cfg_ld_dma_header[i]
                elif self.dma_invalidate_pulse[i]:
                    self.dma_header_r[i]['validate'] = 0

    @always_comb
    def dma_active_logic(self):
        if self.cfg_ld_dma_ctrl_mode == 0:
            self.dma_active_next = 0
        elif ((self.cfg_ld_dma_ctrl_mode == 1) | (self.cfg_ld_dma_ctrl_mode == 2) | (self.cfg_ld_dma_ctrl_mode == 3)):
            self.dma_active_next = self.ld_dma_start_pulse
        else:
            self.dma_active_next = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def dma_active_ff(self):
        if self.reset:
            self.dma_active_r = 0
        elif self.clk_en:
            self.dma_active_r = self.dma_active_next

    @always_comb
    def strm_run_logic(self):
        if self.ld_dma_start_pulse_r:
            self.strm_run_next = 1
        elif self.ld_dma_done_pulse_w:
            self.strm_run_next = 0
        else:
            self.strm_run_next = self.strm_run_r

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def strm_run_ff(self):
        if self.reset:
            self.strm_run_r = 0
        elif self.clk_en:
            self.strm_run_r = self.strm_run_next

    @always_comb
    def num_active_words_mux_logic(self):
        self.num_active_words_w = self.dma_header_r[self.queue_sel_r]['num_active_words']
        self.num_inactive_words_w = self.dma_header_r[self.queue_sel_r]['num_inactive_words']

    @always_comb
    def cycle_active_logic(self):
        self.strm_active_next = 0
        self.strm_active_cnt_next = 0
        self.strm_inactive_cnt_next = 0
        if (self.strm_run_r | self.ld_dma_start_pulse_r):
            if self.ld_dma_start_pulse_r:
                self.strm_active_cnt_next = self.num_active_words_w
                self.strm_inactive_cnt_next = self.num_inactive_words_w
                self.strm_active_next = 1
            elif self.num_inactive_words_w == 0:
                if self.last_strm_w:
                    self.strm_active_next = 0
                else:
                    self.strm_active_next = 1
            else:
                if self.strm_active_r:
                    if self.strm_active_cnt_r > 0:
                        self.strm_active_cnt_next = self.strm_active_cnt_r - 1
                    else:
                        self.strm_active_cnt_next = 0
                    self.strm_active_next = ~(self.strm_active_cnt_next == 0)
                    if self.strm_active_next == 0:
                        self.strm_inactive_cnt_next = self.num_inactive_words_w
                    else:
                        self.strm_inactive_cnt_next = self.strm_inactive_cnt_r
                else:
                    if self.strm_inactive_cnt_r > 0:
                        self.strm_inactive_cnt_next = self.strm_inactive_cnt_r - 1
                    else:
                        self.strm_active_cnt_next = 0
                    self.strm_active_next = self.strm_inactive_cnt_next == 0
                    if self.strm_active_next == 1:
                        self.strm_active_cnt_next = self.num_active_words_w
                    else:
                        self.strm_active_cnt_next = self.strm_active_cnt_r

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def cycle_active_ff(self):
        if self.reset:
            self.strm_active_r = 0
            self.strm_active_cnt_r = 0
            self.strm_inactive_cnt_r = 0
        elif self.clk_en:
            self.strm_active_r = self.strm_active_next
            self.strm_active_cnt_r = self.strm_active_cnt_next
            self.strm_inactive_cnt_r = self.strm_inactive_cnt_next

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def iter_ff(self):
        if self.reset:
            self.start_addr_r = 0
            for i in range(self._params.loop_level):
                self.iter_range_r[i] = 0
                self.iter_stride_r[i] = 0
        elif self.clk_en:
            if self.ld_dma_start_pulse_r:
                self.start_addr_r = self.dma_header_r[self.queue_sel_r]['start_addr']
                for i in range(self._params.loop_level):
                    self.iter_range_r[i] = self.dma_header_r[
                        self.queue_sel_r][f"range_{i}"]
                    self.iter_stride_r[i] = self.dma_header_r[
                        self.queue_sel_r][f"stride_{i}"]

    @always_comb
    def iter_cnt_logic(self):
        for i in range(self._params.loop_level):
            self.iter_cnt_incr[i] = 0
            self.iter_cnt_next[i] = 0
        if self.strm_run_r:
            for i in range(self._params.loop_level):
                if i == 0:
                    self.iter_cnt_incr[i] = self.strm_active_r
                else:
                    self.iter_cnt_incr[i] = self.iter_cnt_incr[i -
                                                               1] & (self.iter_cnt_next[i-1] == 0)

                if self.iter_cnt_incr[i]:
                    if self.iter_cnt_r[i] == (self.iter_range_r[i] - 1):
                        self.iter_cnt_next[i] = 0
                    else:
                        self.iter_cnt_next[i] = self.iter_cnt_r[i] + 1
                else:
                    self.iter_cnt_next[i] = self.iter_cnt_r[i]

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def iter_cnt_ff(self):
        if self.reset:
            for i in range(self._params.loop_level):
                self.iter_cnt_r[i] = 0
        elif self.clk_en:
            for i in range(self._params.loop_level):
                self.iter_cnt_r[i] = self.iter_cnt_next[i]

    @always_comb
    def last_strm_logic(self):
        self.last_strm_w = 1
        for i in range(self._params.loop_level):
            self.last_strm_w = self.last_strm_w & ((self.iter_range_r[i] == 0) | (
                self.iter_cnt_r[i] == (self.iter_range_r[i] - 1)))

    @always_comb
    def ld_dma_done_pulse_logic(self):
        self.ld_dma_done_pulse_w = self.last_strm_w & self.strm_run_r

    @always_comb
    def strm_addr_logic(self):
        self.strm_rd_addr_w = self.start_addr_r
        for i in range(self._params.loop_level):
            self.strm_rd_addr_w = resize(self.strm_rd_addr_w + self.iter_cnt_r[i] * self.iter_stride_r[i] * (
                self._params.cgra_byte_offset + 1), self._params.glb_addr_width)

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def strm_rdrq_packet_ff(self):
        if self.reset:
            self.strm_rd_en_r = 0
            self.strm_rd_addr_r = 0
        elif self.clk_en:
            if self.strm_active_r:
                self.strm_rd_en_r = 1
                self.strm_rd_addr_r = self.strm_rd_addr_w
            else:
                self.strm_rd_en_r = 0

    @always_comb
    def bank_rdrq_packet_logic(self):
        self.bank_addr_match = (self.strm_rd_addr_r[self._params.glb_addr_width-1, self._params.bank_byte_offset]
                                == self.strm_rd_addr_d_arr[0][self._params.glb_addr_width-1, self._params.bank_byte_offset])
        self.bank_rdrq_rd_en = self.strm_rd_en_r & (
            self.ld_dma_start_pulse_d2 | (~self.bank_addr_match))
        self.bank_rdrq_rd_addr = self.strm_rd_addr_r

        self.rdrq_packet['rd_en'] = self.bank_rdrq_rd_en
        self.rdrq_packet['rd_addr'] = self.bank_rdrq_rd_addr

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def bank_rdrs_data_cache_ff(self):
        if self.reset:
            self.bank_rdrs_data_cache_r = 0
        elif self.clk_en:
            if self.rdrs_packet['rd_data_valid']:
                self.bank_rdrs_data_cache_r = self.rdrs_packet['rd_data']

    @always_comb
    def strm_data_logic(self):
        self.strm_data_valid = self.strm_rd_en_d_arr[self.cfg_data_network_latency +
                                                     self.default_latency]
        self.strm_data_sel = self.strm_rd_addr_d_arr[self.cfg_data_network_latency +
                                                     self.default_latency][self._params.bank_byte_offset-1, self._params.cgra_byte_offset]

        self.strm_data = concat(*[self.bank_rdrs_data_cache_r[resize(self.strm_data_sel, math.ceil(math.log(
            self._params.bank_data_width, 2))) * self._params.cgra_data_width + i] for i in reversed(range(self._params.cgra_data_width))])

    @always_comb
    def queue_sel_logic(self):
        if self.cfg_ld_dma_ctrl_mode == 3:
            if self.ld_dma_done_pulse_w:
                self.queue_sel_next = self.queue_sel_r + 1
            else:
                self.queue_sel_next = self.queue_sel_r
        else:
            self.queue_sel_next = 0

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def queue_sel_ff(self):
        if self.reset:
            self.queue_sel_r = 0
        elif self.clk_en:
            self.queue_sel_r = self.queue_sel_next

    def add_strm_rd_en_pipeline(self):
        # TODO: This maximum latency is different from start_pulse maximum latency
        maximum_latency = 2 * self._params.num_glb_tiles + self.default_latency
        self.strm_rd_en_d_arr = self.var("strm_rd_en_d_arr", maximum_latency)
        self.strm_rd_en_pipeline = Pipeline(width=1,
                                            depth=maximum_latency,
                                            is_clk_en=True,
                                            flatten_output=True)
        self.add_child("strm_rd_en_pipeline",
                       self.strm_rd_en_pipeline,
                       clk=self.clk,
                       clk_en=self.clk_en,
                       reset=self.reset,
                       in_=self.strm_rd_en_r,
                       out_=self.strm_rd_en_d_arr)

    def add_strm_rd_addr_pipeline(self):
        # TODO: This maximum latency is different from start_pulse maximum latency
        maximum_latency = 2 * self._params.num_glb_tiles + self.default_latency
        self.strm_rd_addr_d_arr = self.var(
            "strm_rd_addr_d_arr", width=self._params.glb_addr_width, size=maximum_latency)
        self.strm_rd_addr_pipeline = Pipeline(width=self._params.glb_addr_width,
                                              depth=maximum_latency,
                                              is_clk_en=True,
                                              flatten_output=True)
        self.add_child("strm_rd_addr_pipeline",
                       self.strm_rd_addr_pipeline,
                       clk=self.clk,
                       clk_en=self.clk_en,
                       reset=self.reset,
                       in_=self.strm_rd_addr_r,
                       out_=self.strm_rd_addr_d_arr)

    def add_strm_data_start_pulse_pipeline(self):
        # TODO: Latency calculation should be automatic.
        # self.default_latency set to 8 is error-prone.
        maximum_latency = 2 * self._params.num_glb_tiles + self.default_latency + 2
        self.strm_data_start_pulse_d_arr = self.var(
            "strm_data_start_pulse_d_arr", maximum_latency)
        self.strm_data_start_pulse_pipeline = Pipeline(width=1,
                                                       depth=maximum_latency,
                                                       is_clk_en=True,
                                                       flatten_output=True)
        self.add_child("strm_dma_start_pulse_pipeline",
                       self.strm_data_start_pulse_pipeline,
                       clk=self.clk,
                       clk_en=self.clk_en,
                       reset=self.reset,
                       in_=self.ld_dma_start_pulse_r,
                       out_=self.strm_data_start_pulse_d_arr)
        self.strm_data_start_pulse = self.var("strm_data_start_pulse", 1)
        self.wire(self.strm_data_start_pulse,
                  self.strm_data_start_pulse_d_arr[self.cfg_data_network_latency + self.default_latency + 2])

    def add_ld_dma_done_pulse_pipeline(self):
        # TODO: This maximum latency is different from other maximum latency
        maximum_latency = 2 * self._params.num_glb_tiles + self.default_latency + 3
        self.ld_dma_done_pulse_d_arr = self.var(
            "ld_dma_done_pulse_d_arr", maximum_latency)
        self.ld_dma_done_pulse_pipeline = Pipeline(width=1,
                                                   depth=maximum_latency,
                                                   is_clk_en=True,
                                                   flatten_output=True)
        self.add_child("ld_dma_done_pulse_pipeline",
                       self.ld_dma_done_pulse_pipeline,
                       clk=self.clk,
                       clk_en=self.clk_en,
                       reset=self.reset,
                       in_=self.ld_dma_done_pulse_w,
                       out_=self.ld_dma_done_pulse_d_arr)
        self.wire(self.ld_dma_done_pulse,
                  self.ld_dma_done_pulse_d_arr[self.cfg_data_network_latency + self.default_latency + 3])
