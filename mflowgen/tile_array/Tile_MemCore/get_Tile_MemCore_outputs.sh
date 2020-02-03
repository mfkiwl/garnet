#!/bin/bash
../../configure --design $GARNET_HOME/mflowgen/Tile_MemCore/
make synopsys-ptpx-genlibdb
make mentor-calibre-gdsmerge
mkdir -p outputs
cp -L *synopsys-ptpx-genlibdb/outputs/design.lib outputs/Tile_MemCore_tt.lib
cp -L *synopsys-ptpx-genlibdb/outputs/design.db outputs/Tile_MemCore.db
cp -L *cadence-innovus-signoff/outputs/design.lef outputs/Tile_MemCore.lef
cp -L *mentor-calibre-gdsmerge/outputs/design_merged.gds outputs/Tile_MemCore.gds
