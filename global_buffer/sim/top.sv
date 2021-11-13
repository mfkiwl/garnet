/*=============================================================================
** Module: top.sv
** Description:
**              simple top testbench for glb
** Author: Taeyoung Kong
** Change history:  05/22/2021 - Implement first version of testbench
**===========================================================================*/
`define CLK_PERIOD 1000ps

import global_buffer_param::*;

module top;

`ifdef PWR
    supply1 VDD;
    supply0 VSS;
`endif

// ---------------------------------------
// GLB signals
// ---------------------------------------
logic                     clk;
logic [NUM_GLB_TILES-1:0] stall;
logic [NUM_GLB_TILES-1:0] cgra_stall_in;
logic                     reset;
logic                     cgra_soft_reset;

// cgra configuration from global controller
logic                           cgra_cfg_jtag_gc2glb_wr_en;
logic                           cgra_cfg_jtag_gc2glb_rd_en;
logic [CGRA_CFG_ADDR_WIDTH-1:0] cgra_cfg_jtag_gc2glb_addr;
logic [CGRA_CFG_DATA_WIDTH-1:0] cgra_cfg_jtag_gc2glb_data;

// control pulse
logic [NUM_GLB_TILES-1:0] strm_start_pulse;
logic [NUM_GLB_TILES-1:0] pcfg_start_pulse;
logic [NUM_GLB_TILES-1:0] strm_f2g_interrupt_pulse;
logic [NUM_GLB_TILES-1:0] strm_g2f_interrupt_pulse;
logic [NUM_GLB_TILES-1:0] pcfg_g2f_interrupt_pulse;

// Processor
logic                         proc_wr_en;
logic [BANK_DATA_WIDTH/8-1:0] proc_wr_strb;
logic [GLB_ADDR_WIDTH-1:0]    proc_wr_addr;
logic [BANK_DATA_WIDTH-1:0]   proc_wr_data;
logic                         proc_rd_en;
logic [GLB_ADDR_WIDTH-1:0]    proc_rd_addr;
logic [BANK_DATA_WIDTH-1:0]   proc_rd_data;
logic                         proc_rd_data_valid;

// configuration of glb from glc
logic                      if_cfg_wr_en;
logic [AXI_ADDR_WIDTH-1:0] if_cfg_wr_addr;
logic [AXI_DATA_WIDTH-1:0] if_cfg_wr_data;
logic                      if_cfg_rd_en;
logic [AXI_ADDR_WIDTH-1:0] if_cfg_rd_addr;
logic [AXI_DATA_WIDTH-1:0] if_cfg_rd_data;
logic                      if_cfg_rd_data_valid;

// configuration of sram from glc
logic                      if_sram_cfg_wr_en;
logic [GLB_ADDR_WIDTH-1:0] if_sram_cfg_wr_addr;
logic [AXI_DATA_WIDTH-1:0] if_sram_cfg_wr_data;
logic                      if_sram_cfg_rd_en;
logic [GLB_ADDR_WIDTH-1:0] if_sram_cfg_rd_addr;
logic [AXI_DATA_WIDTH-1:0] if_sram_cfg_rd_data;
logic                      if_sram_cfg_rd_data_valid;

// BOTTOM
// stall
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0]                          cgra_stall;

// cgra to glb streaming word
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0][CGRA_DATA_WIDTH-1:0]     stream_data_f2g;
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0]                          stream_data_valid_f2g;

// glb to cgra streaming word
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0][CGRA_DATA_WIDTH-1:0]     stream_data_g2f;
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0]                          stream_data_valid_g2f;

// cgra configuration to cgra
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0]                          cgra_cfg_g2f_cfg_wr_en;
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0]                          cgra_cfg_g2f_cfg_rd_en;
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0][CGRA_CFG_ADDR_WIDTH-1:0] cgra_cfg_g2f_cfg_addr;
logic [NUM_GLB_TILES-1:0][CGRA_PER_GLB-1:0][CGRA_CFG_DATA_WIDTH-1:0] cgra_cfg_g2f_cfg_data;
logic [NUM_GLB_TILES-1:0][CGRA_CFG_DATA_WIDTH-1:0]                   cgra_cfg_f2g_cfg_data;

// ---------------------------------------
// CGRA signals
// ---------------------------------------
logic [NUM_PRR-1:0]                           g2c_cgra_stall;
logic [NUM_PRR-1:0]                           g2c_cfg_wr_en;
logic [NUM_PRR-1:0][CGRA_CFG_ADDR_WIDTH-1:0]  g2c_cfg_wr_addr;
logic [NUM_PRR-1:0][CGRA_CFG_DATA_WIDTH-1:0]  g2c_cfg_wr_data;
logic [NUM_PRR-1:0]                           g2c_cfg_rd_en;
logic [NUM_PRR-1:0][CGRA_CFG_ADDR_WIDTH-1:0]  g2c_cfg_rd_addr;
logic [NUM_PRR-1:0][CGRA_CFG_DATA_WIDTH-1:0]  c2g_cfg_rd_data;

logic [NUM_PRR-1:0]                           g2c_io1;
logic [NUM_PRR-1:0][15:0]                     g2c_io16;
logic [NUM_PRR-1:0]                           c2g_io1;
logic [NUM_PRR-1:0][15:0]                     c2g_io16;

// SDF annotation
initial begin
    $sdf_annotate("netlist/glb.sdf", "top.dut", , "glb_sdf.log", "MAXIMUM");
    // $sdf_annotate("netlist/glbtile_.sdf", top.dut.glb_tile_gen*, , "glb_tile_sdf.log", "MAXIMUM");
end

// max cycle set
initial begin
    repeat(10000000) @(posedge clk);
    $display("\n%0t\tERROR: The 10000000 cycles marker has passed!", $time);
    $finish(2);
end

// clk generation
initial begin
    #0.5ns
    clk = 0;
    forever
    #(`CLK_PERIOD/2.0) clk = !clk;
end

// reset generation
initial begin
    reset <= 1;
    repeat(10) @(posedge clk);
    reset <= 0;
end

// instantiate test
glb_test test (
    .clk(clk),
    .reset(reset),
    // proc ifc
    .proc_wr_en                 ( proc_wr_en         ),
    .proc_wr_strb               ( proc_wr_strb       ),
    .proc_wr_addr               ( proc_wr_addr       ),
    .proc_wr_data               ( proc_wr_data       ),
    .proc_rd_en                 ( proc_rd_en         ),
    .proc_rd_addr               ( proc_rd_addr       ),
    .proc_rd_data               ( proc_rd_data       ),
    .proc_rd_data_valid         ( proc_rd_data_valid ),
    // config ifc
    .if_cfg_wr_en               ( if_cfg_wr_en         ),
    .if_cfg_wr_addr             ( if_cfg_wr_addr       ),
    .if_cfg_wr_data             ( if_cfg_wr_data       ),
    .if_cfg_rd_en               ( if_cfg_rd_en         ),
    .if_cfg_rd_addr             ( if_cfg_rd_addr       ),
    .if_cfg_rd_data             ( if_cfg_rd_data       ),
    .if_cfg_rd_data_valid       ( if_cfg_rd_data_valid ),
    // sram config ifc
    .if_sram_cfg_wr_en          ( if_sram_cfg_wr_en         ),
    .if_sram_cfg_wr_addr        ( if_sram_cfg_wr_addr       ),
    .if_sram_cfg_wr_data        ( if_sram_cfg_wr_data       ),
    .if_sram_cfg_rd_en          ( if_sram_cfg_rd_en         ),
    .if_sram_cfg_rd_addr        ( if_sram_cfg_rd_addr       ),
    .if_sram_cfg_rd_data        ( if_sram_cfg_rd_data       ),
    .if_sram_cfg_rd_data_valid  ( if_sram_cfg_rd_data_valid ),
    .* );

// instantiate dut
global_buffer dut (
    // proc ifc
    .proc_wr_en                 ( proc_wr_en         ),
    .proc_wr_strb               ( proc_wr_strb       ),
    .proc_wr_addr               ( proc_wr_addr       ),
    .proc_wr_data               ( proc_wr_data       ),
    .proc_rd_en                 ( proc_rd_en         ),
    .proc_rd_addr               ( proc_rd_addr       ),
    .proc_rd_data               ( proc_rd_data       ),
    .proc_rd_data_valid         ( proc_rd_data_valid ),
    // config ifc
    .if_cfg_wr_en               ( if_cfg_wr_en         ),
    .if_cfg_wr_addr             ( if_cfg_wr_addr       ),
    .if_cfg_wr_data             ( if_cfg_wr_data       ),
    .if_cfg_rd_en               ( if_cfg_rd_en         ),
    .if_cfg_rd_addr             ( if_cfg_rd_addr       ),
    .if_cfg_rd_data             ( if_cfg_rd_data       ),
    .if_cfg_rd_data_valid       ( if_cfg_rd_data_valid ),
    // sram config ifc
    .if_sram_cfg_wr_en          ( if_sram_cfg_wr_en         ),
    .if_sram_cfg_wr_addr        ( if_sram_cfg_wr_addr       ),
    .if_sram_cfg_wr_data        ( if_sram_cfg_wr_data       ),
    .if_sram_cfg_rd_en          ( if_sram_cfg_rd_en         ),
    .if_sram_cfg_rd_addr        ( if_sram_cfg_rd_addr       ),
    .if_sram_cfg_rd_data        ( if_sram_cfg_rd_data       ),
    .if_sram_cfg_rd_data_valid  ( if_sram_cfg_rd_data_valid ),
`ifdef PWR
    .VDD (VDD),
    .VSS (VSS),
`endif
    .*
);

cgra cgra (
    // stall
    .stall          ( g2c_cgra_stall  ),
    // configuration
    .cfg_wr_en      ( g2c_cfg_wr_en   ),
    .cfg_wr_addr    ( g2c_cfg_wr_addr ),
    .cfg_wr_data    ( g2c_cfg_wr_data ),
    .cfg_rd_en      ( g2c_cfg_rd_en   ),
    .cfg_rd_addr    ( g2c_cfg_rd_addr ),
    .cfg_rd_data    ( c2g_cfg_rd_data ),
    // data
    .io1_g2io       ( g2c_io1  ),
    .io16_g2io      ( g2c_io16 ),
    .io1_io2g       ( c2g_io1  ),
    .io16_io2g      ( c2g_io16 ),
    .*
);

// Configuration interface
// TODO: Assume that NUM_PRR == NUM_GLB_TILES. Use the first one among two signals.
always_comb begin
    for (int i=0; i<NUM_PRR; i++) begin
        g2c_cgra_stall[i] = cgra_stall[i][0];
        g2c_cfg_wr_en[i] = cgra_cfg_g2f_cfg_wr_en[i][0];
        g2c_cfg_wr_addr[i] = cgra_cfg_g2f_cfg_addr[i][0];
        g2c_cfg_wr_data[i] = cgra_cfg_g2f_cfg_data[i][0];
        g2c_cfg_rd_en[i] = cgra_cfg_g2f_cfg_rd_en[i][0];
        g2c_cfg_rd_addr[i] = cgra_cfg_g2f_cfg_addr[i][0];
    end
end

// Data interface
// Note: Connect g2f to [0] column. Connect f2g to [1] column.
always_comb begin
    for (int i=0; i<NUM_PRR; i++) begin
        g2c_io1[i] = stream_data_valid_g2f[i][0];
        g2c_io16[i] = stream_data_g2f[i][0];
        stream_data_valid_f2g[i][0] = c2g_io1[i];
        stream_data_f2g[i][0] = c2g_io16[i];
        stream_data_valid_f2g[i][1] = c2g_io1[i];
        stream_data_f2g[i][1] = c2g_io16[i];
    end
end

endmodule
