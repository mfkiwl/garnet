# ==============================================================================
# loads SOC design files (RTL)
# ==============================================================================
# Cortex-M3 Files
set soc_cm3_files [concat [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_wic/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_itm/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_tpiu/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_fpb/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_mpu/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_dwt/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_nvic/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_dpu/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_dap_ahb_ap/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cm3_bus_matrix/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/dapswjdp/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/cortexm3/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cortex-m3/models/cells -types f *.v ] ]

# CMSDK Files
set soc_cmdk_files [concat [
  glob -nocomplain -directory rtl/components/cmsdk/cmsdk_apb_dualtimers/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cmsdk/cmsdk_apb_uart/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cmsdk/cmsdk_apb_watchdog/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cmsdk/cmsdk_apb3_eg_slave/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/cmsdk/cmsdk_apb_slave_mux/verilog -types f *.v ] ]

# RTC (Real Time Clock) Files
set  soc_rtc_files [concat [
  glob -nocomplain -directory rtl/components/rtc -types f *.v] ]

# SRAMs
set soc_sram_files [concat [
  glob -nocomplain -directory rtl/components/sram/common -types f *.v] [
  glob -nocomplain -directory rtl/components/sram/common/axi-sram -types f *.v] [
  glob -nocomplain -directory rtl/components/sram/synthesis -types f *.v] ]

# STDCELL Wrapper Files
set soc_stdcell_wrp_files [concat [
  glob -nocomplain -directory rtl/components/std-cells/synthesis -types f *.v]]

# SOC SDK Files
set soc_sdk_files [concat [
  glob -nocomplain -directory rtl/components/socsdk -types f *.v]]

# SoC Controller Files
set soc_ctrl_files [concat [
  glob -nocomplain -directory rtl/components/soc_controller -types f *.v]]

# Integration Files
set soc_integration_files [concat [
  glob -nocomplain -directory rtl/integration -types f *.v]]

# PL330 DMA Files
set soc_dma_files [concat [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_dma_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_axi_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_icache_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_lsq_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_pipeline_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_mfifo_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_engine_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_merge_buffer_aha/verilog -types f *.v] [
  glob -nocomplain -directory rtl/components/nic450/logical/DMA330_aha/logical/pl330_dma_aha/pl330_periph_aha/verilog -types f *.v]]

# TLX-400 Files
source scripts/tlx_design_files.tcl

# NIC-400 Files
source scripts/nic400_design_files.tcl

# CGRA-SoC Interface Files
set soc_cgra_if_files [concat [
  glob -nocomplain -directory rtl/components/cgra/axi_to_cgra_data -types f *.v] [
  glob -nocomplain -directory rtl/components/cgra/axi_to_cgra_reg -types f *.v] ]

# All SoC Files
set soc_design_files [concat \
  $soc_cm3_files \
  $soc_cmdk_files \
  $soc_rtc_files \
  $soc_sram_files \
  $soc_stdcell_wrp_files \
  $soc_sdk_files \
  $soc_integration_files \
  $soc_dma_files \
  $soc_tlx_files \
  $soc_nic400_files \
  $soc_cgra_if_files \
  $soc_ctrl_files \
]
