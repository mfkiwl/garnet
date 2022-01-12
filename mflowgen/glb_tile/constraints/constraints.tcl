#=========================================================================
# Design Constraints File
#=========================================================================

# This constraint sets the target clock period for the chip in
# nanoseconds. Note that the first parameter is the name of the clock
# signal in your verlog design. If you called it something different than
# clk you will need to change this. You should set this constraint
# carefully. If the period is unrealistically small then the tools will
# spend forever trying to meet timing and ultimately fail. If the period
# is too large the tools will have no trouble but you will get a very
# conservative implementation.

set clock_net  clk
set clock_name ideal_clock

create_clock -name ${clock_name} \
             -period ${clock_period} \
             [get_ports ${clock_net}]

# This constraint sets the load capacitance in picofarads of the
# output pins of your design.

set_load -pin_load $ADK_TYPICAL_ON_CHIP_LOAD [all_outputs]

# This constraint sets the input drive strength of the input pins of
# your design. We specifiy a specific standard cell which models what
# would be driving the inputs. This should usually be a small inverter
# which is reasonable if another block of on-chip logic is driving
# your inputs.

set_driving_cell -no_design_rule \
  -lib_cell $ADK_DRIVING_CELL [all_inputs]

# set_input_delay
set_input_delay -clock ${clock_name} 0.2 [all_inputs -no_clocks]
# all est<->wst connections
set_input_delay -clock ${clock_name} 0.3 [get_ports *_est* -filter "direction==in"]
set_input_delay -clock ${clock_name} 0.3 [get_ports *_wst* -filter "direction==in"]
# set_input_delay -clock ${clock_name} -min 0.1 [get_ports *_est* -filter "direction==in"]
# set_input_delay -clock ${clock_name} -min 0.1 [get_ports *_wst* -filter "direction==in"]
set_input_delay -clock ${clock_name} 0 glb_tile_id

# set_output_delay constraints for output ports
set_output_delay -clock ${clock_name} 0.3 [all_outputs]
set_output_delay -clock ${clock_name} 0.5 [get_ports *_est* -filter "direction==out"]
set_output_delay -clock ${clock_name} 0.5 [get_ports *_wst* -filter "direction==out"]

# set_min_delay for all tile-connected inputs
set_min_delay -from [get_ports *_est* -filter "direction==in"] 0.5
set_min_delay -from [get_ports *_wst* -filter "direction==in"] 0.5
# set_min_delay -to [get_ports *_est* -filter "direction==out"] 0.6
# set_min_delay -to [get_ports *_wst* -filter "direction==out"] 0.6
set_max_delay -to [get_ports *_est* -filter "direction==out"] 1.0
set_max_delay -to [get_ports *_wst* -filter "direction==out"] 1.0

# set false path
# glb_tile_id is constant
set_false_path -from {glb_tile_id*}

# clk_en for core/rtr/pcfg_rtr are multi_cycle path
# NOTE: clk_en for cfg and jtag are not multi cycle path
set_multicycle_path -setup 10 -from {clk_en_core}
set_multicycle_path -hold 9 -from {clk_en_core}
set_multicycle_path -setup 10 -from {clk_en_*rtr}
set_multicycle_path -hold 9 -from {clk_en_*rtr}

# path from configuration registers are multi_cycle path
set_multicycle_path -setup 10 -through [get_cells glb_cfg/glb_pio/pio_logic/*] -through [get_pins glb_cfg/cfg_* -filter "direction==out"]
set_multicycle_path -hold 9 -through [get_cells glb_cfg/glb_pio/pio_logic/*] -through [get_pins glb_cfg/cfg_* -filter "direction==out"]
set_multicycle_path -setup 10 -from [get_cells glb_cfg/glb_pio/pio_logic/*] -through [get_pins glb_cfg/cfg_* -filter "direction==out"]
set_multicycle_path -hold 9 -from [get_cells glb_cfg/glb_pio/pio_logic/*] -through [get_pins glb_cfg/cfg_* -filter "direction==out"]
# these inputs/outputs are configuration register
set_multicycle_path -setup 10 -from {cfg_tile_connected_wsti}
set_multicycle_path -hold 9 -from {cfg_tile_connected_wsti}
set_multicycle_path -setup 10 -from {cfg_pcfg_tile_connected_wsti}
set_multicycle_path -hold 9 -from {cfg_pcfg_tile_connected_wsti}
set_multicycle_path -setup 10 -to {cfg_tile_connected_esto}
set_multicycle_path -hold 9 -to {cfg_tile_connected_esto}
set_multicycle_path -setup 10 -to {cfg_pcfg_tile_connected_esto}
set_multicycle_path -hold 9 -to {cfg_pcfg_tile_connected_esto}

# jtag bypass mode is false path
set_false_path -from [get_ports cgra_cfg_jtag_wsti_rd_en_bypass] -to [get_ports cgra_cfg_jtag_esto_rd_en_bypass]
set_false_path -from [get_ports cgra_cfg_jtag_wsti_addr_bypass] -to [get_ports cgra_cfg_jtag_esto_addr_bypass]

# jtag cgra configuration read
# ignore timing when rd_en is 1
set_case_analysis 0 cgra_cfg_jtag_wsti_rd_en
set_multicycle_path -setup 10 -from cgra_cfg_jtag_wsti_rd_en
set_multicycle_path -hold 9 -from cgra_cfg_jtag_wsti_rd_en
set_multicycle_path -setup 10 -from cgra_cfg_jtag_wsti_addr -to cgra_cfg_jtag_esto_addr
set_multicycle_path -hold 9 -from cgra_cfg_jtag_wsti_addr -to cgra_cfg_jtag_esto_addr
set_multicycle_path -setup 10 -from cgra_cfg_jtag_wsti_data -to cgra_cfg_jtag_esto_data
set_multicycle_path -hold 9 -from cgra_cfg_jtag_wsti_data -to cgra_cfg_jtag_esto_data
set_false_path -from cgra_cfg_jtag_wsti_wr_en -to cgra_cfg_jtag_esto_wr_en

# jtag sram read
# jtag sram read is multicycle path because you assert rd_en for long cycles
# glb_sram_cfg_ctrl input to bank signals
# The first two constraints may be duplicate
set_multicycle_path -setup 4 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_wst_s*rd* -filter "direction==in"] -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd* -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_wst_s*rd* -filter "direction==in"] -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd* -filter "direction==out"]
set_multicycle_path -setup 4 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd* -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd* -filter "direction==out"]

# bank to output signals
# The first two constraints may be duplicate
set_multicycle_path -setup 4 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd_data* -filter "direction==in"] -through [get_cells glb_sram_cfg_ctrl/if_sram_cfg_wst_s*rd_data*] 
set_multicycle_path -hold 3 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd_data* -filter "direction==in"] -through [get_cells glb_sram_cfg_ctrl/if_sram_cfg_wst_s*rd_data*] 
set_multicycle_path -setup 4 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd* -filter "direction==in"]
set_multicycle_path -hold 3 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*rd* -filter "direction==in"]

# bank_ctrl ports through mem
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_rd_en -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_rd_en -filter "direction==out"]
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_addr -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_addr -filter "direction==out"]
# bank_ctrl internal registers
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd* -filter "direction==in"] -through [get_cells glb_bank_*/glb_bank_ctrl/sram_cfg_rd*]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd* -filter "direction==in"] -through [get_cells glb_bank_*/glb_bank_ctrl/sram_cfg_rd*]
# bank_ctrl sram data out and data_valid out
# set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/mem_data_out] -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd_data]
# set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/mem_data_out] -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd_data]
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd_data*]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*rd_data*]

# jtag write
# jtag sram write is asserted for 4 cycles from glc
# The first two constraints may be duplicate
set_multicycle_path -setup 4 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_wst_s*wr* -filter "direction==in"] -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*wr* -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_wst_s*wr* -filter "direction==in"] -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*wr* -filter "direction==out"]
set_multicycle_path -setup 4 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*wr* -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_sram_cfg_ctrl/if_sram_cfg_ctrl*wr* -filter "direction==out"]

# bank_ctrl ports through mem
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*wr* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_wr_en -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*wr* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_wr_en -filter "direction==out"]
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*wr* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_addr -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*wr* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_addr -filter "direction==out"]
set_multicycle_path -setup 4 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*wr* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_data* -filter "direction==out"]
set_multicycle_path -hold 3 -through [get_pins glb_bank_*/glb_bank_ctrl/if_sram_cfg*wr* -filter "direction==in"] -through [get_pins glb_bank_*/glb_bank_ctrl/mem_data* -filter "direction==out"]

# Make all signals limit their fanout
set_max_fanout 20 $design_name

# Make all signals meet good slew
set_max_transition [expr 0.10*${clock_period}] $design_name

