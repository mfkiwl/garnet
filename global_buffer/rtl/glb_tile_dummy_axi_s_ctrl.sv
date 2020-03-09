/*=============================================================================
** Module: glb_tile_dummy_axi_s_ctrl.sv
** Description:
**              axi slave controller
** Author: Taeyoung Kong
** Change history: 02/01/2020 - Finish hand-written axi slave controller
**===========================================================================*/
import global_buffer_pkg::*;

module glb_tile_dummy_axi_s_ctrl (
    input  logic                            clk,
    input  logic                            reset,

    input  logic                            proc2glb_wr_en,
    input  logic [BANK_DATA_WIDTH/8-1:0]    proc2glb_wr_strb,
    input  logic [GLB_ADDR_WIDTH-1:0]       proc2glb_wr_addr,
    input  logic [BANK_DATA_WIDTH-1:0]      proc2glb_wr_data,
    input  logic                            proc2glb_rd_en,
    input  logic [GLB_ADDR_WIDTH-1:0]       proc2glb_rd_addr,
    output logic [BANK_DATA_WIDTH-1:0]      glb2proc_rd_data,

    input  packet_t                         proc_packet_esti,
    output packet_t                         proc_packet_esto
);

assign proc_packet_esto.wr.wr_en = proc2glb_wr_en;
assign proc_packet_esto.wr.wr_strb = proc2glb_wr_strb;
assign proc_packet_esto.wr.wr_addr = proc2glb_wr_addr;
assign proc_packet_esto.wr.wr_data = proc2glb_wr_data;

assign proc_packet_esto.rdrq.rd_en = proc2glb_rd_en;
assign proc_packet_esto.rdrq.rd_addr = proc2glb_rd_addr;

assign glb2proc_rd_data = proc_packet_esti.rdrs.rd_data;

// just wire to 0
assign proc_packet_esto.rdrs.rd_data = '0;

endmodule
