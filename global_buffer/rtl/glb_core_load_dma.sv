/*=============================================================================
** Module: glb_core_load_dma.sv
** Description:
**              Global Buffer Core Load DMA
** Author: Taeyoung Kong
** Change history: 01/27/2020
**      - Implement first version of global buffer core load DMA
**===========================================================================*/
import  global_buffer_pkg::*;

module glb_core_load_dma (
    input  logic                            clk,
    input  logic                            clk_en,
    input  logic                            reset,

    // cgra streaming word
    output logic [CGRA_DATA_WIDTH-1:0]      stream_data_g2f,
    output logic                            stream_data_valid_g2f,

    // read req packet
    output rdrq_packet_t                    rdrq_packet,

    // read res packet
    input  rdrs_packet_t                    rdrs_packet,

    // Configuration registers
    input  logic                            cfg_load_dma_on,
    input  logic                            cfg_load_dma_auto_on,
    input  dma_ld_header_t                  cfg_load_dma_header [QUEUE_DEPTH],

    // glb internal signal
    output logic                            cfg_load_dma_invalidate_pulse [QUEUE_DEPTH],

    // interrupt pulse
    output logic                            stream_g2f_done_pulse
);

//============================================================================//
// Internal logic
//============================================================================//
// state enum
enum logic[2:0] {OFF, IDLE, READY, ACC1, ACC2, ACC3, ACC4, DONE} state, next_state;

// cache register control
logic [BANK_DATA_WIDTH-1:0]     cache_data, next_cache_data;
logic [BANK_DATA_WIDTH/8-1:0]   cache_strb, next_cache_strb;

// working dma header register
logic [GLB_ADDR_WIDTH-1:0]      start_addr;
logic [MAX_NUM_WORDS_WIDTH-1:0] num_words;
logic [$clog2(QUEUE_DEPTH)-1:0] q_sel_cnt_r, q_sel_cnt;

// dma control logic
logic [GLB_ADDR_WIDTH-1:0]      cur_addr, next_cur_addr;
logic [MAX_NUM_WORDS_WIDTH-1:0] num_cnt, next_num_cnt;
logic                           is_first_word, next_is_first_word;

// stream_g2f_done
logic stream_g2f_done;
logic stream_g2f_done_d1;

dma_ld_header_t dma_header_int [QUEUE_DEPTH];
logic dma_validate [QUEUE_DEPTH];
logic dma_validate_d1 [QUEUE_DEPTH];
logic dma_validate_pulse [QUEUE_DEPTH];
logic dma_invalidate_pulse [QUEUE_DEPTH];

//============================================================================//
// Internal dma
//============================================================================//
always_comb begin
    for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
        dma_validate[i] = cfg_load_dma_header[i].valid;
    end
end

always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
            dma_validate_d1[i] <= 0;
        end
    end
    else if (clk_en) begin
        for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
            dma_validate_d1[i] <= dma_validate[i];
        end
    end
end

always_comb begin
    for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
        dma_validate_pulse[i] = dma_validate[i] & !dma_validate_d1[i];
    end
end

always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
            dma_header_int[i] <= '0;
        end
    end
    else if (clk_en) begin
        for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
            if (dma_validate_pulse[i] == 1) begin
                dma_header_int[i] <= cfg_load_dma_header[i];
            end
            else if (dma_invalidate_pulse[i] == 1) begin
                dma_header_int[i].valid <= 0;
            end
        end
    end
end
always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
            dma_invalidate_pulse[i] <= 0;
        end
    end
    else if (clk_en) begin
        if (   state == IDLE 
            && dma_header_int[q_sel_cnt].valid == '1
            && dma_header_int[q_sel_cnt].num_words != '0 ) begin
            dma_invalidate_pulse[q_sel_cnt] <= 1;
        end
        else begin
            dma_invalidate_pulse[q_sel_cnt] <= 0;
        end
    end
end

always_comb begin
    for (int i=0; i<QUEUE_DEPTH; i=i+1) begin
        cfg_load_dma_invalidate_pulse[i] = dma_invalidate_pulse[i];
    end
end

//============================================================================//
// State
//============================================================================//
// state FSM
always_comb begin
    next_cache_data = cache_data;
    next_cache_strb = cache_strb;
    next_num_cnt = num_cnt;
    next_cur_addr = cur_addr;
    next_state = state;
    next_is_first_word = is_first_word;
    case (state)
        OFF: begin
            if (cfg_load_dma_on == '1) begin
                next_state = IDLE;
            end
        end
        IDLE: begin
            next_num_cnt = '0;
            next_cur_addr = '0;
            if (dma_header_int[q_sel_cnt].valid == '1 && dma_header_int[q_sel_cnt].num_words !='0) begin
                next_cur_addr = dma_header_int[q_sel_cnt].start_addr;
                next_num_cnt = dma_header_int[q_sel_cnt].num_words;
                next_is_first_word = 1'b1;
                case (next_cur_addr[2:1])
                    2'b00: begin
                        next_state = READY;
                    end
                    2'b01: begin
                        next_state = ACC1;
                    end
                    2'b10: begin
                        next_state = ACC2;
                    end
                    2'b11: begin
                        next_state = ACC3;
                    end
                    default: begin
                        next_state = READY;
                    end
                endcase
            end
        end
        READY: begin
            if (num_cnt == '0) begin
                next_state = DONE;
            end
            else if (stream_data_valid_f2g == '1) begin
                next_is_first_word = 1'b0;
                next_cache_data[0*CGRA_DATA_WIDTH +: CGRA_DATA_WIDTH] = stream_data_f2g;
                next_cache_strb[1:0] = 2'b11;
                next_num_cnt = num_cnt - 1;
                if (!is_first_word) begin
                    next_cur_addr = cur_addr + (CGRA_DATA_WIDTH/8);
                end
                next_state = ACC1;
            end
        end
        ACC1: begin
            if (num_cnt == '0) begin
                next_state = DONE;
            end
            else if (stream_data_valid_f2g == '1) begin
                next_is_first_word = 1'b0;
                next_cache_data[1*CGRA_DATA_WIDTH +: CGRA_DATA_WIDTH] = stream_data_f2g;
                next_cache_strb[3:2] = 2'b11;
                next_num_cnt = num_cnt - 1;
                if (!is_first_word) begin
                    next_cur_addr = cur_addr + (CGRA_DATA_WIDTH/8);
                end
                next_state = ACC2;
            end
        end
        ACC2: begin
            if (num_cnt == '0) begin
                next_state = DONE;
            end
            else if (stream_data_valid_f2g == '1) begin
                next_is_first_word = 1'b0;
                next_cache_data[2*CGRA_DATA_WIDTH +: CGRA_DATA_WIDTH] = stream_data_f2g;
                next_cache_strb[5:4] = 2'b11;
                next_num_cnt = num_cnt - 1;
                if (!is_first_word) begin
                    next_cur_addr = cur_addr + (CGRA_DATA_WIDTH/8);
                end
                next_state = ACC3;
            end
        end
        ACC3: begin
            if (num_cnt == '0) begin
                next_state = DONE;
            end
            else if (stream_data_valid_f2g == '1) begin
                next_is_first_word = 1'b0;
                next_cache_data[3*CGRA_DATA_WIDTH +: CGRA_DATA_WIDTH] = stream_data_f2g;
                next_cache_strb[7:6] = 2'b11;
                next_num_cnt = num_cnt - 1;
                if (!is_first_word) begin
                    next_cur_addr = cur_addr + (CGRA_DATA_WIDTH/8);
                end
                next_state = ACC4;
            end
        end
        ACC4: begin
            if (num_cnt == '0) begin
                next_state = DONE;
            end
            else if (stream_data_valid_f2g == '1) begin
                next_is_first_word = 1'b0;
                // reset cache
                next_cache_data = {{(BANK_DATA_WIDTH-CGRA_DATA_WIDTH){1'b0}}, stream_data_f2g};
                next_cache_strb = {6'h0, 2'b11};
                next_num_cnt = num_cnt - 1;
                if (!is_first_word) begin
                    next_cur_addr = cur_addr + (CGRA_DATA_WIDTH/8);
                end
                next_state = ACC1;
            end
            else begin
                next_cache_data = '0;
                next_cache_strb = '0;
                next_state = READY;
            end
        end
        DONE: begin
            next_cache_data = '0;
            next_cache_strb = '0;
            next_num_cnt = '0;
            next_state = IDLE;
        end
        default: begin
            next_cache_data = cache_data;
            next_cache_strb = cache_strb;
            next_num_cnt = num_cnt;
            next_state = IDLE;
        end
    endcase
end

// state register
always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        state <= OFF;
    end
    else if (clk_en) begin
        if (cfg_load_dma_on == '0) begin
            state <= OFF;
        end
        else begin
            state <= next_state;
        end
    end
end

// cache register
always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        cache_data <= '0;
        cache_strb <= '0;
    end
    else if (clk_en) begin
        cache_data <= next_cache_data;
        cache_strb <= next_cache_strb;
    end
end

// num_cnt and cur_addr register
always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        num_cnt <= '0;
        cur_addr <= '0;
        is_first_word <= '0;
    end
    else if (clk_en) begin
        num_cnt <= next_num_cnt;
        cur_addr <= next_cur_addr;
        is_first_word <= next_is_first_word;
    end
end

//============================================================================//
// Internal dma header registers
//============================================================================//
always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        q_sel_cnt_r <= 0;
    end
    else if (clk_en) begin
        if (state == IDLE) begin
            if (cfg_load_dma_auto_on == '1) begin
                if (dma_header_int[q_sel_cnt].valid == '1 && dma_header_int[q_sel_cnt].num_words != '0) begin
                    q_sel_cnt_r <= q_sel_cnt_r + 1;
                end
            end
            else begin
                q_sel_cnt_r <= 0;
            end
        end
    end
end

always_comb begin
    if (cfg_load_dma_auto_on == '1) begin
        q_sel_cnt = q_sel_cnt_r;
    end
    else begin
        q_sel_cnt = '0;
    end
end

//============================================================================//
// DMA output
//============================================================================//
// output wr_packet
always_comb begin
    if (state == DONE) begin
        wr_packet.wr_en = 1'b1;
        wr_packet.wr_strb = cache_strb;
        wr_packet.wr_data = cache_data;
        wr_packet.wr_addr = {cur_addr[GLB_ADDR_WIDTH-1:BANK_ADDR_BYTE_OFFSET], {BANK_ADDR_BYTE_OFFSET{1'b0}}};
    end
    else if (state == ACC4 && (num_cnt != '0)) begin
        wr_packet.wr_en = 1'b1;
        wr_packet.wr_strb = cache_strb;
        wr_packet.wr_data = cache_data;
        wr_packet.wr_addr = {cur_addr[GLB_ADDR_WIDTH-1:BANK_ADDR_BYTE_OFFSET], {BANK_ADDR_BYTE_OFFSET{1'b0}}};
    end
    else begin
        wr_packet.wr_en = 1'b0;
        wr_packet.wr_strb = '0;
        wr_packet.wr_data = '0;
        wr_packet.wr_addr = '0;
    end
end

//============================================================================//
// stream in done pulse
//============================================================================//
assign stream_g2f_done = (state == DONE);

always_ff @(posedge clk or posedge reset) begin
    if (reset) begin
        stream_g2f_done_d1 <= 1'b0;
    end
    else if (clk_en) begin
        stream_g2f_done_d1 <= stream_g2f_done;
    end
end
assign stream_g2f_done_pulse = stream_g2f_done & (!stream_g2f_done_d1);

endmodule
