typedef enum int {
    WR  = 0,
    RD  = 1,
    G2F = 2,
    F2G = 3
} stream_type;

typedef logic [CGRA_DATA_WIDTH-1:0] data16[];
typedef logic [BANK_DATA_WIDTH-1:0] data64[];

class Kernel;
    static int cnt = 0;
    stream_type type_;
    int tile_id;
    int bank_id;
    int start_addr;
    int cycle_start_addr;
    int dim;
    int extent[LOOP_LEVEL];
    int cycle_stride[LOOP_LEVEL];
    int data_stride[LOOP_LEVEL];
    int new_start_addr;
    int new_extent[LOOP_LEVEL];
    int new_cycle_stride[LOOP_LEVEL];
    int new_data_stride[LOOP_LEVEL];
    string filename;
    data16 data_arr;
    data16 data_arr_out;
    int total_cycle;
    data64 data64_arr;
    data64 data64_arr_out;
endclass

class Test;
    const int tile_offset = 1 << (BANK_ADDR_WIDTH + BANK_SEL_ADDR_WIDTH);
    const int bank_offset = 1 << BANK_ADDR_WIDTH;
    const int cgra_data_byte_offset = 1;
    string filename;
    int num_kernels;
    Kernel kernels[];
    bit [NUM_GLB_TILES-1:0] g2f_tile_mask;
    bit [NUM_GLB_TILES-1:0] f2g_tile_mask;

    extern function new(string filename);
endclass

function Test::new(string filename);
    int fd = $fopen(filename, "r");
    string type_, data_filename;
    int tile_id, bank_id, dim;
    int tmp_start_addr, tmp_cycle_start_addr;
    string cycle_stride_s, extent_s, data_stride_s, tmp_s;

    $display("\n---- Test Initialization ----");
    if (fd) $display("Test file open %s", filename);
    else $error("Cannot open %s", filename);
    void'($fscanf(fd, " %d", num_kernels));
    kernels = new[num_kernels];
    for (int i = 0; i < num_kernels; i++) begin
        kernels[i] = new();
        void'($fscanf(
            fd, " %s%d%d%d%d", type_, tile_id, bank_id, tmp_start_addr, tmp_cycle_start_addr
        ));
        if (type_ == "WR") kernels[i].type_ = WR;
        else if (type_ == "RD") kernels[i].type_ = RD;
        else if (type_ == "G2F") kernels[i].type_ = G2F;
        else if (type_ == "F2G") kernels[i].type_ = F2G;
        else $error("This type [%s] is not supported", type_);
        void'($fscanf(fd, " %d", dim));
        kernels[i].tile_id = tile_id;
        kernels[i].bank_id = bank_id;
        kernels[i].start_addr = tile_offset * tile_id + bank_offset * bank_id + tmp_start_addr * cgra_data_byte_offset;
        kernels[i].cycle_start_addr = tmp_cycle_start_addr;
        kernels[i].dim = dim;
        for (int j = 0; j < dim; j++) begin
            void'($fscanf(fd, " %d", kernels[i].extent[j]));
        end
        for (int j = 0; j < dim; j++) begin
            void'($fscanf(fd, " %d", kernels[i].cycle_stride[j]));
        end
        for (int j = 0; j < dim; j++) begin
            void'($fscanf(fd, " %d", kernels[i].data_stride[j]));
        end
        void'($fscanf(fd, " %s", data_filename));
        kernels[i].filename = data_filename;

        // Convert start_addr/extent/stride to hardware-friendly start_addr/extent/stride
        kernels[i].new_start_addr = kernels[i].start_addr >> cgra_data_byte_offset;
        for (int j = 0; j < dim; j++) begin
            kernels[i].new_extent[j] = kernels[i].extent[j] - 2;
            if (j == 0) begin
                kernels[i].new_cycle_stride[j] = kernels[i].cycle_stride[j];
                kernels[i].new_data_stride[j]  = kernels[i].data_stride[j];
            end else begin
                kernels[i].new_cycle_stride[j] = kernels[i].cycle_stride[j] - kernels[i].cycle_stride[j-1] * (kernels[i].extent[j-1] - 1);
                kernels[i].new_data_stride[j]  = kernels[i].data_stride[j] - kernels[i].data_stride[j-1] * (kernels[i].extent[j-1] - 1);
            end
        end
    end
    $fclose(fd);

    for (int i = 0; i < num_kernels; i++) begin
        if (kernels[i].type_ == G2F) g2f_tile_mask[kernels[i].tile_id] = 1;
        else if (kernels[i].type_ == F2G) f2g_tile_mask[kernels[i].tile_id] = 1;
    end

    // Calculate total cycles
    for (int i = 0; i < num_kernels; i++) begin
        if (kernels[i].type_ == G2F || kernels[i].type_ == F2G) begin
            kernels[i].total_cycle = kernels[i].cycle_stride[kernels[i].dim - 1] * kernels[i].extent[kernels[i].dim - 1];
        end
    end

    // Display log
    $display("Number of kernels in the app is %0d", num_kernels);
    foreach (kernels[i]) begin
        extent_s = "";
        cycle_stride_s = "";
        data_stride_s = "";
        $display(
            "Kernel %0d: Type: %s, Tile_ID: %0d, Bank_ID: %0d, Start_addr: %0d, Cycle_start_addr: %0d",
            i, kernels[i].type_.name(), kernels[i].tile_id, kernels[i].bank_id,
            kernels[i].start_addr, kernels[i].cycle_start_addr);
        for (int j = 0; j < kernels[i].dim; j++) begin
            tmp_s.itoa(kernels[i].extent[j]);
            extent_s = {extent_s, " ", tmp_s};
            tmp_s.itoa(kernels[i].cycle_stride[j]);
            cycle_stride_s = {cycle_stride_s, " ", tmp_s};
            tmp_s.itoa(kernels[i].data_stride[j]);
            data_stride_s = {data_stride_s, " ", tmp_s};
        end
        $display("Extent: [%s], cycle_stride: [%s], data_stride: [%s]", extent_s, cycle_stride_s,
                 data_stride_s);
    end
endfunction
