from kratos import Interface


class GlbConfigInterface(Interface):
    def __init__(self, addr_width: int, data_width: int):
        Interface.__init__(self, f"glb_cfg_ifc_A_{addr_width}_D_{data_width}")

        # Local variables
        self.wr_en = self.var("wr_en", 1)
        self.wr_addr = self.var("wr_addr", addr_width)
        self.wr_data = self.var("wr_data", data_width)
        self.rd_en = self.var("rd_en", 1)
        self.rd_addr = self.var("rd_addr", addr_width)
        self.rd_data = self.var("rd_data", data_width)
        self.rd_data_valid = self.var("rd_data_valid", 1)

        m_to_s = [self.wr_en, self.wr_addr,
                  self.wr_data, self.rd_en, self.rd_addr]
        s_to_m = [self.rd_data, self.rd_data_valid]

        self.master = self.modport("master")
        self.slave = self.modport("slave")

        for port in m_to_s:
            self.master.set_output(port)
            self.slave.set_input(port)
        for port in s_to_m:
            self.master.set_input(port)
            self.slave.set_output(port)