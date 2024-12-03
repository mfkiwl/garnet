//
//--------------------------------------------------------------------------------
//          THIS FILE WAS AUTOMATICALLY GENERATED BY THE GENESIS2 ENGINE        
//  FOR MORE INFORMATION: OFER SHACHAM (CHIP GENESIS INC / STANFORD VLSI GROUP)
//    !! THIS VERSION OF GENESIS2 IS NOT FOR ANY COMMERCIAL USE !!
//     FOR COMMERCIAL LICENSE CONTACT SHACHAM@ALUMNI.STANFORD.EDU
//--------------------------------------------------------------------------------
//
//  
//	-----------------------------------------------
//	|            Genesis Release Info             |
//	|  $Change: 11904 $ --- $Date: 2013/08/03 $   |
//	-----------------------------------------------
//	
//
//  Source file: /aha/garnet/global_controller/rtl/genesis/global_controller.svp
//  Source template: global_controller
//
// --------------- Begin Pre-Generation Parameters Status Report ---------------
//
//	From 'generate' statement (priority=5):
//
//		---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----
//
//	From Command Line input (priority=4):
// Parameter num_glb_tiles 	= 4
// Parameter cfg_addr_width 	= 32
// Parameter axi_addr_width 	= 13
// Parameter cfg_op_width 	= 5
// Parameter cgra_width 	= 8
// Parameter cfg_data_width 	= 32
// Parameter glb_tile_mem_size 	= 128
// Parameter axi_data_width 	= 32
// Parameter block_axi_addr_width 	= 12
//
//		---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----
//
//	From XML input (priority=3):
//
//		---- ---- ---- ---- ---- ---- ---- ---- ---- ---- ----
//
//	From Config File input (priority=2):
//
// ---------------- End Pre-Generation Pramameters Status Report ----------------

/*=============================================================================
** Module: global_controller.svp
** Description:
**              Global Controller
** Author: Taeyoung Kong, Alex Carsello
** Change history: 05/02/2019 - AXI4-Lite controller is added
**===========================================================================*/

//============================================================================//
// Genesis parameter declaration
//============================================================================//
// cfg_data_width (_GENESIS2_CMD_LINE_PRIORITY_) = 32
//
// cfg_addr_width (_GENESIS2_CMD_LINE_PRIORITY_) = 32
//
// cfg_op_width (_GENESIS2_CMD_LINE_PRIORITY_) = 5
//
// axi_addr_width (_GENESIS2_CMD_LINE_PRIORITY_) = 13
//
// axi_data_width (_GENESIS2_CMD_LINE_PRIORITY_) = 32
//
// block_axi_addr_width (_GENESIS2_CMD_LINE_PRIORITY_) = 12
//
// num_glb_tiles (_GENESIS2_CMD_LINE_PRIORITY_) = 4
//
// cgra_width (_GENESIS2_CMD_LINE_PRIORITY_) = 8
//
// glb_tile_mem_size (_GENESIS2_CMD_LINE_PRIORITY_) = 128
//

//============================================================================//
// Genesis object generation
//============================================================================//

module global_controller (
    input  logic                                clk_in,
    input  logic                                reset_in,

    // cgra control signals
    output logic                                clk_out,
    output logic                                reset_out,
    output logic [7:0]            cgra_stall, 
    output logic [3:0]         glb_clk_en_master, 
    output logic [3:0]         glb_clk_en_bank_master, 
    output logic [3:0]         glb_pcfg_broadcast_stall, 
    output logic [$clog2(4)*2-1:0] glb_flush_crossbar_sel,

    // global buffer configuration
    output logic                                glb_cfg_wr_en,
    output logic                                glb_cfg_wr_clk_en,
    output logic [11:0]  glb_cfg_wr_addr,
    output logic [31:0]        glb_cfg_wr_data,
    output logic                                glb_cfg_rd_en,
    output logic                                glb_cfg_rd_clk_en,
    output logic [11:0]  glb_cfg_rd_addr,
    input  logic [31:0]        glb_cfg_rd_data,
    input  logic                                glb_cfg_rd_data_valid,

    // global buffer sram configuration
    output logic                                sram_cfg_wr_en,
    output logic [18:0]        sram_cfg_wr_addr,
    output logic [31:0]        sram_cfg_wr_data,
    output logic                                sram_cfg_rd_en,
    output logic [18:0]        sram_cfg_rd_addr,
    input  logic [31:0]        sram_cfg_rd_data,
    input  logic                                sram_cfg_rd_data_valid,

	// global buffer control signals
	output logic [3:0]         strm_g2f_start_pulse,
	output logic [3:0]         strm_f2g_start_pulse,
	output logic [3:0]         pc_start_pulse,
	input  logic [3:0]         strm_g2f_interrupt_pulse,
	input  logic [3:0]         strm_f2g_interrupt_pulse,
	input  logic [3:0]         pcfg_g2f_interrupt_pulse,

    // cgra configuration
    output logic                                cgra_cfg_read,
    output logic                                cgra_cfg_write,
    output logic [31:0]        cgra_cfg_addr,
    output logic [31:0]        cgra_cfg_wr_data,
    input  logic [31:0]        cgra_cfg_rd_data,

    // axi4-lite slave interface
    input  logic [12:0]        axi_awaddr,
    input  logic                                axi_awvalid,
    output logic                                axi_awready,
    input  logic [31:0]        axi_wdata,
    input  logic                                axi_wvalid,
    output logic                                axi_wready,
    input  logic                                axi_bready,
    output logic [1:0]                          axi_bresp,
    output logic                                axi_bvalid,
    input  logic [12:0]        axi_araddr,
    input  logic                                axi_arvalid,
    output logic                                axi_arready,
    output logic [31:0]        axi_rdata,
    output logic [1:0]                          axi_rresp,
    output logic                                axi_rvalid,
    input  logic                                axi_rready,

    output logic                                interrupt,

    // jtag interface signals
    input  logic                                tck,
    input  logic                                tdi,
    input  logic                                tms,
    input  logic                                trst_n,
    output logic                                tdo
);
  
//============================================================================//
// logic declaration
//============================================================================//
// internal clk is controlled by jtag
logic clk;
assign clk = clk_out;

// jtag control signal
logic [31:0]        config_addr_jtag_out;
logic [31:0]        config_data_jtag_out;
logic [4:0]          op_jtag;
logic [31:0]        config_data_jtag_in;
logic                                sys_clk_activated;

// cgra control signals
logic                                jtag_global_reset, axi_global_reset, global_reset;
logic [3:0]         jtag_glb_clk_en_master, axi_glb_clk_en_master;
logic [3:0]         jtag_glb_clk_en_bank_master, axi_glb_clk_en_bank_master;
logic [3:0]         jtag_glb_pcfg_broadcast_stall, axi_glb_pcfg_broadcast_stall;
logic [7:0]            jtag_cgra_stall, axi_cgra_stall;
logic [$clog2(4)*2-1:0] axi_glb_flush_crossbar_sel;

// global buffer configuration
logic                                jtag_glb_cfg_wr_en, axi_glb_cfg_wr_en;
logic                                jtag_glb_cfg_wr_clk_en, axi_glb_cfg_wr_clk_en;
logic [11:0]  jtag_glb_cfg_wr_addr, axi_glb_cfg_wr_addr;
logic [31:0]        jtag_glb_cfg_wr_data, axi_glb_cfg_wr_data;
logic                                jtag_glb_cfg_rd_en, axi_glb_cfg_rd_en;
logic                                jtag_glb_cfg_rd_clk_en, axi_glb_cfg_rd_clk_en;
logic [11:0]  jtag_glb_cfg_rd_addr, axi_glb_cfg_rd_addr;
logic [31:0]        jtag_glb_cfg_rd_data, axi_glb_cfg_rd_data;
logic                                jtag_glb_cfg_rd_data_valid, axi_glb_cfg_rd_data_valid;

// global buffer sram configuration
logic                               jtag_sram_cfg_wr_en;
logic [18:0]       jtag_sram_cfg_wr_addr;
logic [31:0]       jtag_sram_cfg_wr_data;
logic                               jtag_sram_cfg_rd_en;
logic                               jtag_sram_cfg_rd_clk_en;
logic [18:0]       jtag_sram_cfg_rd_addr;
logic [31:0]       jtag_sram_cfg_rd_data;
logic                               jtag_sram_cfg_rd_data_valid;

// cgra configuration
logic                                jtag_cgra_cfg_read, axi_cgra_cfg_read;
logic                                jtag_cgra_cfg_write, axi_cgra_cfg_write;
logic [31:0]        jtag_cgra_cfg_addr, axi_cgra_cfg_addr;
logic [31:0]        jtag_cgra_cfg_wr_data, axi_cgra_cfg_wr_data;
logic [31:0]        jtag_cgra_cfg_data_in, axi_cgra_cfg_data_in;

// jtag to axi addressmap
logic                                jtag_axi_wr_en;
logic [11:0]  jtag_axi_wr_addr;
logic [31:0]        jtag_axi_wr_data;
logic                                jtag_axi_rd_en;
logic [11:0]  jtag_axi_rd_addr;
logic [31:0]        jtag_axi_rd_data;
logic                                jtag_axi_rd_data_valid;

// axi global controller configuration
logic                                axi_glc_cfg_wr_en;
logic                                axi_glc_cfg_wr_clk_en;
logic [11:0]  axi_glc_cfg_wr_addr;
logic [31:0]        axi_glc_cfg_wr_data;
logic                                axi_glc_cfg_rd_en;
logic                                axi_glc_cfg_rd_clk_en;
logic [11:0]  axi_glc_cfg_rd_addr;
logic [31:0]        axi_glc_cfg_rd_data;
logic                                axi_glc_cfg_rd_data_valid;

//============================================================================//
// assign
//============================================================================//
assign global_reset = jtag_global_reset | axi_global_reset;
assign glb_clk_en_master = jtag_glb_clk_en_master | axi_glb_clk_en_master;
assign glb_clk_en_bank_master = jtag_glb_clk_en_bank_master | axi_glb_clk_en_bank_master;
assign glb_pcfg_broadcast_stall = jtag_glb_pcfg_broadcast_stall | axi_glb_pcfg_broadcast_stall;
assign glb_flush_crossbar_sel = axi_glb_flush_crossbar_sel;
assign cgra_stall = jtag_cgra_stall | axi_cgra_stall;

// reset output
assign reset_out    = global_reset;

// global buffer configuration
assign glb_cfg_wr_en                = jtag_glb_cfg_wr_en | axi_glb_cfg_wr_en;
assign glb_cfg_wr_clk_en            = jtag_glb_cfg_wr_clk_en | axi_glb_cfg_wr_clk_en;
assign glb_cfg_wr_addr              = jtag_glb_cfg_wr_addr | axi_glb_cfg_wr_addr;
assign glb_cfg_wr_data              = jtag_glb_cfg_wr_data | axi_glb_cfg_wr_data;
assign glb_cfg_rd_en                = jtag_glb_cfg_rd_en | axi_glb_cfg_rd_en;
assign glb_cfg_rd_clk_en            = jtag_glb_cfg_rd_clk_en | axi_glb_cfg_rd_clk_en;
assign glb_cfg_rd_addr              = jtag_glb_cfg_rd_addr | axi_glb_cfg_rd_addr;
assign jtag_glb_cfg_rd_data         = glb_cfg_rd_data;
assign axi_glb_cfg_rd_data          = glb_cfg_rd_data;
assign jtag_glb_cfg_rd_data_valid   = glb_cfg_rd_data_valid;
assign axi_glb_cfg_rd_data_valid    = glb_cfg_rd_data_valid;

// global buffer sram configuration
assign sram_cfg_wr_en                = jtag_sram_cfg_wr_en;
assign sram_cfg_wr_addr              = jtag_sram_cfg_wr_addr;
assign sram_cfg_wr_data              = jtag_sram_cfg_wr_data;
assign sram_cfg_rd_en                = jtag_sram_cfg_rd_en;
assign sram_cfg_rd_addr              = jtag_sram_cfg_rd_addr;
assign jtag_sram_cfg_rd_data         = sram_cfg_rd_data;
assign jtag_sram_cfg_rd_data_valid   = sram_cfg_rd_data_valid;

// cgra configuration
assign cgra_cfg_read                = jtag_cgra_cfg_read | axi_cgra_cfg_read;
assign cgra_cfg_write               = jtag_cgra_cfg_write | axi_cgra_cfg_write;
assign cgra_cfg_addr                = jtag_cgra_cfg_addr | axi_cgra_cfg_addr;
assign cgra_cfg_wr_data             = jtag_cgra_cfg_wr_data | axi_cgra_cfg_wr_data;
assign jtag_cgra_cfg_data_in        = cgra_cfg_rd_data;
assign axi_cgra_cfg_data_in         = cgra_cfg_rd_data;

//============================================================================//
// jtag controller instantiation
//============================================================================//
jtag  jtag_controller (
    .ifc_trst_n(trst_n),
    .ifc_tck(tck),
    .ifc_tms(tms),
    .ifc_tdi(tdi),
    .ifc_tdo(tdo),
    .ifc_config_addr_to_gc(config_addr_jtag_out),
    .ifc_config_data_from_gc(config_data_jtag_in),
    .ifc_config_data_to_gc(config_data_jtag_out),
    .ifc_config_op_to_gc(op_jtag),
    .clk(clk),
    .reset(reset_in),
    .sys_clk_activated(sys_clk_activated),
    .bsr_tdi(),
    .bsr_sample(),
    .bsr_intest(),
    .bsr_extest(),
    .bsr_update_en(),
    .bsr_capture_en(),
    .bsr_shift_dr(),
    .bsr_tdo()
);

//============================================================================//
// jtag controller 
//============================================================================//
glc_jtag_ctrl  jtag_ctrl (
    .clk_in(clk_in),
    .tck(tck),
    .reset_in(reset_in),

    .config_addr_jtag_out(config_addr_jtag_out),
    .config_data_jtag_out(config_data_jtag_out),
    .op_jtag(op_jtag),
    .config_data_jtag_in(config_data_jtag_in),

    .sys_clk_activated(sys_clk_activated),
    .clk_out(clk_out),
    .jtag_global_reset(jtag_global_reset),
    .jtag_glb_clk_en_master(jtag_glb_clk_en_master), 
    .jtag_glb_clk_en_bank_master(jtag_glb_clk_en_bank_master), 
    .jtag_glb_pcfg_broadcast_stall(jtag_glb_pcfg_broadcast_stall), 
    .jtag_cgra_stall(jtag_cgra_stall), 

    .jtag_glb_cfg_wr_en(jtag_glb_cfg_wr_en),
    .jtag_glb_cfg_wr_clk_en(jtag_glb_cfg_wr_clk_en),
    .jtag_glb_cfg_wr_addr(jtag_glb_cfg_wr_addr),
    .jtag_glb_cfg_wr_data(jtag_glb_cfg_wr_data),
    .jtag_glb_cfg_rd_en(jtag_glb_cfg_rd_en),
    .jtag_glb_cfg_rd_clk_en(jtag_glb_cfg_rd_clk_en),
    .jtag_glb_cfg_rd_addr(jtag_glb_cfg_rd_addr),
    .jtag_glb_cfg_rd_data(jtag_glb_cfg_rd_data),
    .jtag_glb_cfg_rd_data_valid(jtag_glb_cfg_rd_data_valid),

    .jtag_sram_cfg_wr_en(jtag_sram_cfg_wr_en),
    .jtag_sram_cfg_wr_addr(jtag_sram_cfg_wr_addr),
    .jtag_sram_cfg_wr_data(jtag_sram_cfg_wr_data),
    .jtag_sram_cfg_rd_en(jtag_sram_cfg_rd_en),
    .jtag_sram_cfg_rd_addr(jtag_sram_cfg_rd_addr),
    .jtag_sram_cfg_rd_data(jtag_sram_cfg_rd_data),
    .jtag_sram_cfg_rd_data_valid(jtag_sram_cfg_rd_data_valid),

    .jtag_cgra_cfg_read(jtag_cgra_cfg_read),
    .jtag_cgra_cfg_write(jtag_cgra_cfg_write),
    .jtag_cgra_cfg_addr(jtag_cgra_cfg_addr),
    .jtag_cgra_cfg_wr_data(jtag_cgra_cfg_wr_data),
    .jtag_cgra_cfg_data_in(jtag_cgra_cfg_data_in),

    .jtag_axi_wr_en(jtag_axi_wr_en),
    .jtag_axi_wr_addr(jtag_axi_wr_addr),
    .jtag_axi_wr_data(jtag_axi_wr_data),
    .jtag_axi_rd_en(jtag_axi_rd_en),
    .jtag_axi_rd_addr(jtag_axi_rd_addr),
    .jtag_axi_rd_data(jtag_axi_rd_data),
    .jtag_axi_rd_data_valid(jtag_axi_rd_data_valid)
);

//============================================================================//
// axi4-lite controller instantiation
//============================================================================//
glc_axi_ctrl  axi_controller (
    .clk(clk),
    .reset(reset_in),

    // axi4-lite slave interface
    .axi_awaddr(axi_awaddr),
    .axi_awvalid(axi_awvalid),
    .axi_awready(axi_awready),
    .axi_wdata(axi_wdata),
    .axi_wvalid(axi_wvalid),
    .axi_wready(axi_wready),
    .axi_bready(axi_bready),
    .axi_bresp(axi_bresp),
    .axi_bvalid(axi_bvalid),
    .axi_araddr(axi_araddr),
    .axi_arvalid(axi_arvalid),
    .axi_arready(axi_arready),
    .axi_rdata(axi_rdata),
    .axi_rresp(axi_rresp),
    .axi_rvalid(axi_rvalid),
    .axi_rready(axi_rready),

    .axi_glb_cfg_wr_en(axi_glb_cfg_wr_en),
    .axi_glb_cfg_wr_clk_en(axi_glb_cfg_wr_clk_en),
    .axi_glb_cfg_wr_addr(axi_glb_cfg_wr_addr),
    .axi_glb_cfg_wr_data(axi_glb_cfg_wr_data),
    .axi_glb_cfg_rd_en(axi_glb_cfg_rd_en),
    .axi_glb_cfg_rd_clk_en(axi_glb_cfg_rd_clk_en),
    .axi_glb_cfg_rd_addr(axi_glb_cfg_rd_addr),
    .axi_glb_cfg_rd_data(axi_glb_cfg_rd_data),
    .axi_glb_cfg_rd_data_valid(axi_glb_cfg_rd_data_valid),

    .axi_glc_cfg_wr_en(axi_glc_cfg_wr_en),
    .axi_glc_cfg_wr_clk_en(axi_glc_cfg_wr_clk_en),
    .axi_glc_cfg_wr_addr(axi_glc_cfg_wr_addr),
    .axi_glc_cfg_wr_data(axi_glc_cfg_wr_data),
    .axi_glc_cfg_rd_en(axi_glc_cfg_rd_en),
    .axi_glc_cfg_rd_clk_en(axi_glc_cfg_rd_clk_en),
    .axi_glc_cfg_rd_addr(axi_glc_cfg_rd_addr),
    .axi_glc_cfg_rd_data(axi_glc_cfg_rd_data),
    .axi_glc_cfg_rd_data_valid(axi_glc_cfg_rd_data_valid)
);

//============================================================================//
// axi4-lite addressmap
//============================================================================//
glc_axi_addrmap  axi_addressmap (
    .clk(clk),
    .reset(reset_in),

    .axi_global_reset(axi_global_reset),
    .axi_glb_clk_en_master(axi_glb_clk_en_master), 
    .axi_glb_clk_en_bank_master(axi_glb_clk_en_bank_master), 
    .axi_glb_pcfg_broadcast_stall(axi_glb_pcfg_broadcast_stall), 
    .axi_glb_flush_crossbar_sel(axi_glb_flush_crossbar_sel), 
    .axi_cgra_stall(axi_cgra_stall), 

	.strm_g2f_start_pulse(strm_g2f_start_pulse),
	.strm_f2g_start_pulse(strm_f2g_start_pulse),
	.pc_start_pulse(pc_start_pulse),
	.strm_g2f_interrupt_pulse(strm_g2f_interrupt_pulse),
	.strm_f2g_interrupt_pulse(strm_f2g_interrupt_pulse),
	.pcfg_g2f_interrupt_pulse(pcfg_g2f_interrupt_pulse),

    .axi_glc_cfg_wr_en(axi_glc_cfg_wr_en),
    .axi_glc_cfg_wr_clk_en(axi_glc_cfg_wr_clk_en),
    .axi_glc_cfg_wr_addr(axi_glc_cfg_wr_addr),
    .axi_glc_cfg_wr_data(axi_glc_cfg_wr_data),
    .axi_glc_cfg_rd_en(axi_glc_cfg_rd_en),
    .axi_glc_cfg_rd_clk_en(axi_glc_cfg_rd_clk_en),
    .axi_glc_cfg_rd_addr(axi_glc_cfg_rd_addr),
    .axi_glc_cfg_rd_data(axi_glc_cfg_rd_data),
    .axi_glc_cfg_rd_data_valid(axi_glc_cfg_rd_data_valid),

    .jtag_axi_wr_en(jtag_axi_wr_en),
    .jtag_axi_wr_addr(jtag_axi_wr_addr),
    .jtag_axi_wr_data(jtag_axi_wr_data),
    .jtag_axi_rd_en(jtag_axi_rd_en),
    .jtag_axi_rd_addr(jtag_axi_rd_addr),
    .jtag_axi_rd_data(jtag_axi_rd_data),
    .jtag_axi_rd_data_valid(jtag_axi_rd_data_valid),

    .axi_cgra_cfg_read(axi_cgra_cfg_read),
    .axi_cgra_cfg_write(axi_cgra_cfg_write),
    .axi_cgra_cfg_addr(axi_cgra_cfg_addr),
    .axi_cgra_cfg_wr_data(axi_cgra_cfg_wr_data),
    .axi_cgra_cfg_data_in(axi_cgra_cfg_data_in),

    .interrupt(interrupt)
);

endmodule
