from kratos import *


class FIFO(Generator):
    def __init__(self, data_width, depth, almost_full_diff=2, almost_empty_diff=2):

        super().__init__(f"reg_fifo_d_{depth}_w_{data_width}", debug=True)

        self.data_width = self.parameter("data_width", 16)
        self.data_width.value = data_width
        self.depth = depth
        self.almost_full_diff = almost_full_diff
        self.almost_empty_diff = almost_empty_diff

        assert not (depth & (depth - 1)), "FIFO depth needs to be a power of 2"

        # CLK and RST
        self.clk = self.clock("clk")
        self.reset = self.reset("reset")
        self.clk_en = self.input("clk_en", 1)

        # INPUTS
        self._data_in = self.input("data_in", self.data_width)
        self._data_out = self.output("data_out", self.data_width)

        self._push = self.input("push", 1)
        self._pop = self.input("pop", 1)
        ptr_width = max(1, clog2(self.depth))

        self._rd_ptr = self.var("rd_ptr", ptr_width)
        self._wr_ptr = self.var("wr_ptr", ptr_width)
        self._read = self.var("read", 1)
        self._write = self.var("write", 1)
        self._reg_array = self.var("reg_array", self.data_width, size=self.depth, packed=True, explicit_array=True)

        self._empty = self.output("empty", 1)
        self._full = self.output("full", 1)
        self._almost_full = self.output("almost_full", 1)
        self._almost_empty = self.output("almost_empty", 1)

        self._num_items = self.var("num_items", clog2(self.depth) + 1)
        self.wire(self._full, self._num_items == self.depth)
        self.wire(self._almost_full, self._num_items >= (self.depth - self.almost_full_diff))
        self.wire(self._almost_empty, self._num_items <= self.almost_empty_diff)
        self.wire(self._empty, self._num_items == 0)
        self.wire(self._read, self._pop & ~self._empty)

        self.wire(self._write, self._push & ~self._full)
        self.add_code(self.set_num_items)
        self.add_code(self.reg_array_ff)
        self.add_code(self.wr_ptr_ff)
        self.add_code(self.rd_ptr_ff)
        self.add_code(self.data_out_ff)

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def rd_ptr_ff(self):
        if self.reset:
            self._rd_ptr = 0
        elif self._read:
            self._rd_ptr = self._rd_ptr + 1

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def wr_ptr_ff(self):
        if self.reset:
            self._wr_ptr = 0
        elif self._write:
            if self._wr_ptr == (self.depth - 1):
                self._wr_ptr = 0
            else:
                self._wr_ptr = self._wr_ptr + 1

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def reg_array_ff(self):
        if self.reset:
            self._reg_array = 0
        elif self._write:
            self._reg_array[self._wr_ptr] = self._data_in

    @always_comb
    def data_out_ff(self):
        self._data_out = self._reg_array[self._rd_ptr]

    @always_ff((posedge, "clk"), (posedge, "reset"))
    def set_num_items(self):
        if self.reset:
            self._num_items = 0
        elif self._write & ~self._read:
            self._num_items = self._num_items + 1
        elif ~self._write & self._read:
            self._num_items = self._num_items - 1
        else:
            self._num_items = self._num_items
