echo "${num_words}x${word_size}m${mux_size}s" >> config.txt
mc_name=tsn16ffcllhdspsbsram_20131200_130a
export MC_HOME=inputs/adk/mc/${mc_name}
export PATH="${PATH}:inputs/adk/mc/MC2_2013.12.00.f/bin"
sram_name="ts1n16ffcllsblvtc${num_words}x${word_size}m${mux_size}s"
if [ $partial_write == True ]; then
  sram_name+="w"
fi

sram_name+="_130a"

##############################################################################
USE_CACHED=True
if [ $USE_CACHED == True ]; then
    echo '+++ HACK TIME! Using cached srams...'
    set -x
    GOLD=/build/gold.219/full_chip/17-tile_array/16-Tile_MemCore/12-gen_sram_macro
    ln -s $GOLD/outputs
    ln -s $GOLD/lib2db
    ls -l outputs/sram_tt.lib
    head outputs/sram_tt.lib || exit 13
    set +x
    echo '--- continue...'


else
    cmd="./inputs/adk/mc/${mc_name}/tsn16ffcllhdspsbsram_130a.pl -file config.txt -NonBIST -NonSLP -NonDSLP -NonSD"
    if [ ! $partial_write == True ]; then
        cmd+=" -NonBWEB"
    fi
    eval $cmd

    ln -s ../$sram_name/NLDM/${sram_name}_${corner}.lib outputs/sram_tt.lib
    ln -s ../$sram_name/NLDM/${sram_name}_${bc_corner}.lib outputs/sram_ff.lib
    ln -s ../$sram_name/GDSII/${sram_name}_m4xdh.gds outputs/sram.gds
    ln -s ../$sram_name/LEF/${sram_name}_m4xdh.lef outputs/sram.lef
    ln -s ../$sram_name/VERILOG/${sram_name}_pwr.v outputs/sram-pwr.v
    ln -s ../$sram_name/VERILOG/${sram_name}.v outputs/sram.v
    ln -s ../$sram_name/SPICE/${sram_name}.spi outputs/sram.spi

    cd lib2db/
    make
fi
##############################################################################

cd ..

