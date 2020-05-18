#-----------------------------------------------------------------------------
# Synopsys Design Constraint (SDC) File
#-----------------------------------------------------------------------------
# Purpose: Design Constraints
#------------------------------------------------------------------------------
#
#
# Author   : Gedeon Nyengele
# Date     : May 9, 2020
#------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Tech Parameters
# ------------------------------------------------------------------------------
source -echo -verbose inputs/cons_scripts/tech_params.tcl

# ------------------------------------------------------------------------------
# Set-up Design Configuration Options
# ------------------------------------------------------------------------------
source -echo -verbose inputs/cons_scripts/design_info.tcl

# ------------------------------------------------------------------------------
# Clock Constraints
# ------------------------------------------------------------------------------
source -echo -verbose inputs/cons_scripts/clocks.tcl

# ------------------------------------------------------------------------------
# IO Constraints for Source-Sync Interfaces
# ------------------------------------------------------------------------------
source -echo -verbose inputs/cons_scripts/io.tcl

# ------------------------------------------------------------------------------
# Set Design Context
# ------------------------------------------------------------------------------
source -echo -verbose inputs/cons_scripts/design_context.tcl