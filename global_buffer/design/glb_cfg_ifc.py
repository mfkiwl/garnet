from kratos import Interface


class GlbConfigInterface(Interface):
    def __init__(self, params):
        Interface.__init__(self, "glb_cfg_ifc")
        self.params = params

        addr_width = params.axi_addr_width
        data_width = params.axi_data_width

        # Local variables
        wr_en = self.var("wr_en", 1)
        wr_clk_en = self.var("wr_clk_en", 1)
        wr_addr = self.var("wr_addr", addr_width)
        wr_data = self.var("wr_data", data_width)
        rd_en = self.var("rd_en", 1)
        rd_clk_en = self.var("rd_clk_en", 1)
        rd_addr = self.var("rd_addr", addr_width)
        rd_data = self.var("rd_data", data_width)
        rd_data_valid = self.var("rd_data_valid", 1)

        m_to_s = [wr_en, wr_clk_en, wr_addr, wr_data, rd_en, rd_clk_en, rd_addr]
        s_to_m = [rd_data, rd_data_valid]

        self.master = self.modport("master")
        self.slave = self.modport("slave")

        for port in m_to_s:
            self.master.set_output(port)
            self.slave.set_input(port)
        for port in s_to_m:
            self.master.set_input(port)
            self.slave.set_output(port)
