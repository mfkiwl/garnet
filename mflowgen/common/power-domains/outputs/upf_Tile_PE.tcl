# Set env var WHICH_SOC=amber for amber build, else uses default settings
set WHICH_SOC "default"
if { [info exists ::env(WHICH_SOC)] } { set WHICH_SOC $::env(WHICH_SOC) }

######## Create Power Domains ###########
# Default Power Domain - SD when tile not used 
create_power_domain TOP -include_scope

# AON Domain - Modules that stay ON when tile is OFF 
# PS configuration logic and tie cells for hi/lo outputs that drive the tile_id

########################################################################
# pe_power_domain_config_reg_addr
# 
# Note that DECODE_FEATURE and FEATURE_AND modules (at least) are
# auto-assigned names that may change at the whim of the generator.
# So the designer has to track that and update this parm by hand :(
# See garnet issue 922 and ~steveri/0notes/vto/pwr-aware-gls.txt
# 
# Used by upf_Tile_PE.tcl
# 
# We have a script (check-pdcr-address.sh) that updates the address
# automatically, so should be survivable when/if address not accurate.

set pe_power_domain_config_reg_addr 15
if { $WHICH_SOC == "amber" } { set pe_power_domain_config_reg_addr 17 }
set aon_elements "
  PowerDomainOR
  DECODE_FEATURE_$pe_power_domain_config_reg_addr
  coreir_eq_16_inst0 and_inst1
  FEATURE_AND_$pe_power_domain_config_reg_addr
  PowerDomainConfigReg_inst0
  const_511_9
  const_0_8
"
create_power_domain AON -elements $aon_elements

### Toplevel Connections ######
## VDD 
create_supply_port VDD
create_supply_net  VDD -domain TOP
create_supply_net  VDD -domain AON -reuse

connect_supply_net VDD -ports  VDD

## VSS (0.0V)
create_supply_port VSS
create_supply_net  VSS -domain TOP
create_supply_net  VSS -domain AON -reuse

connect_supply_net VSS -ports  VSS

#### TOP SD Domain Power Connections ##########
create_supply_net VDD_SW -domain TOP 

#### Establish Connections ################
set_domain_supply_net AON -primary_power_net VDD -primary_ground_net VSS
set_domain_supply_net TOP -primary_power_net VDD_SW -primary_ground_net VSS

########### Set all Global Signals as AON
set_related_supply_net -object_list {tile_id hi lo clk clk_pass_through reset config_config_addr config_config_data config_read config_write read_config_data_in stall flush} -power VDD -ground VSS
set_related_supply_net -object_list {clk_out clk_pass_through_out_bot clk_pass_through_out_right reset_out config_out_config_addr config_out_config_data config_out_read config_out_write read_config_data stall_out flush_out} -power VDD -ground VSS

########### Create Shut-Down Logic for SD #######
create_power_switch SD_sw \
-domain TOP \
-input_supply_port {in VDD} \
-output_supply_port {out VDD_SW} \
-control_port {SD_sd PowerDomainConfigReg_inst0/read_config_data[0]} \
-on_state {ON_STATE in !SD_sd}

#### Create Power State Table ##################
add_port_state VDD -state {HighVoltage 0.8}
add_port_state SD_sw/out -state {HighVoltage 0.8} -state {SD_OFF off}
create_pst lvds_system_pst -supplies {VDD VDD_SW}
add_pst_state LOGIC_ON -pst lvds_system_pst -state {HighVoltage SD_OFF}
add_pst_state ALL_ON -pst lvds_system_pst -state {HighVoltage HighVoltage}
