#!/bin/bash

# Exit on error in any stage of any pipeline
set -eo pipefail

function where_this_script_lives {
  # Where this script lives
  scriptpath=$0      # E.g. "build_tarfile.sh" or "foo/bar/build_tarfile.sh"
  scriptdir=${0%/*}  # E.g. "build_tarfile.sh" or "foo/bar"
  if test "$scriptdir" == "$scriptpath"; then scriptdir="."; fi
  # scriptdir=`cd $scriptdir; pwd`
  (cd $scriptdir; pwd)
}
script_home=`where_this_script_lives`

# setup assumes this script lives in garnet/mflowgen/test/
garnet=`cd $script_home/../..; pwd`

# Check requirements for python, coreir, magma etc.
echo "--- CHECK REQUIREMENTS"
tmpfile=/tmp/tmp.test_pe.$USER.$$
(cd $garnet; $garnet/bin/requirements_check.sh) \
    |& tee $tmpfile.reqchk \
    || exit 13

# Separate egg check
# FIXME should be part of requirements_check.sh
# echo 


# Lots of useful things in /usr/local/bin. coreir for instance ("type"=="which")
# echo ""; type coreir
export PATH="$PATH:/usr/local/bin"; hash -r
# type coreir; echo ""

# Set up paths for innovus, genus, dc etc.
source $garnet/.buildkite/setup.sh
source $garnet/.buildkite/setup-calibre.sh

# OA_HOME weirdness
echo "--- UNSET OA_HOME"
echo ""
echo "buildkite (but not arm7 (???)) errs if OA_HOME is set"
echo "BEFORE: OA_HOME=$OA_HOME"
echo "unset OA_HOME"
unset OA_HOME
echo "AFTER:  OA_HOME=$OA_HOME"
echo ""

# Oop "make rtl" needs GARNET_HOME env var
export GARNET_HOME=$garnet

# Make a build space for mflowgen; clone mflowgen
echo ""; echo "--- pwd="`pwd`; echo ""
if [ "$USER" == "buildkite-agent" ]; then
    build=$garnet/mflowgen/test
else
    build=/sim/$USER
fi
echo "--- CLONE MFLOWGEN REPO"
test  -d $build || mkdir $build; cd $build
test  -d $build/mflowgen || git clone https://github.com/cornell-brg/mflowgen.git
mflowgen=$build/mflowgen
echo ""

# tsmc16 adk
# Yeah, this ain't gonna fly.
# gitlab repo requires username/pwd permissions and junk
# 
# test -d tsmc16-adk || git clone http://gitlab.r7arm-aha.localdomain/alexcarsello/tsmc16-adk.git
# test -d tsmc16     || ln -s tsmc16-adk tsmc16
# 
# Instead, let's just use a cached copy
cd $mflowgen/adks
cached_adk=/sim/steveri/mflowgen/adks/tsmc16-adk
# 
# Symlink to steveri no good. Apparently need permission to "touch" adk files(??)
# test -e tsmc16 || ln -s ${cached_adk} tsmc16
test -e tsmc16 || cp -rp ${cached_adk} tsmc16


# Tile_PE
module=Tile_PE
if test -d $mflowgen/$module; then
    echo "oops $mflowgen/$module exists"
    echo "giving up already love ya bye-bye"
    exit 13
fi

echo ""; set -x
mkdir $mflowgen/$module; cd $mflowgen/$module
../configure --design $garnet/mflowgen/Tile_PE
set +x; echo ""

# Targets: run "make list" and "make status"
# make list
# 
# echo "make mentor-calibre-drc \
#   |& tee mcdrc.log \
#   | gawk -f $script_home/filter.awk"

########################################################################
# Makefile assumes "python" means "python3" :(
# Note requirements_check.sh (above) not sufficient to fix this :(
# Python check
echo "--- PYTHON=PYTHON3 FIX"
v=`python -c 'import sys; print(sys.version_info[0]*1000+sys.version_info[1])'`
echo "Found python version $v -- should be at least 3007"
if [ $v -lt 3007 ] ; then
  echo ""
  echo "WARNING found python version $v -- should be 3007"
  echo "WARNING I will try and fix it for you with my horrible hackiness"
  # On arm7 machine it's in /usr/local/bin, that's just how it is
  echo "ln -s bin/python /usr/local/bin/python3"
  test -d bin || mkdir bin
  (cd bin; ln -s /usr/local/bin/python3 python)
  export PATH=`pwd`/bin:"$PATH"
  hash -r
  v=`python -c 'import sys; print(sys.version_info[0]*1000+sys.version_info[1])'`
  echo "Found python version $v -- should be at least 3007"
  if [ $v -lt 3007 ] ; then
    echo ""; echo "ERROR could not fix python sorry!!!"
  fi
  echo
fi
echo ""

# Prime the pump w/req-chk results
cat $tmpfile.reqchk > mcdrc.log; /bin/rm $tmpfile.reqchk
echo "----------------------------------------" >> mcdrc.log

# So. BECAUSE makefile files silently (and maybe some other good
# reasons as well), we now do (at least) two stages of build.
# "make rtl" fails frequently, so that's where we'll put the
# first break point
# 
echo "--- MAKE RTL"
nobuf='stdbuf -oL -eL'
make rtl < /dev/null \
  |& $nobuf tee -a mcdrc.log \
  |  $nobuf gawk -f $script_home/rtl-filter.awk \
  || exit 13                

if [ ! -e *rtl/outputs/design.v ] ; then
    echo ""; echo ""; echo ""
    echo "***ERROR Cannot find design.v, make-rtl musta failed"
    echo ""; echo ""; echo ""
    exit 13
else
    echo ""
    echo Built verilog file *rtl/outputs/design.v
    ls -l *rtl/outputs/design.v
    echo ""
fi

echo "--- MAKE DRC"
nobuf='stdbuf -oL -eL'
make mentor-calibre-drc < /dev/null \
  |& $nobuf tee -a mcdrc.log \
  |  $nobuf gawk -f $script_home/post-rtl-filter.awk \
  || exit 13                

# Error summary. Note makefile often fails silently :(
echo "+++ ERRORS"
echo ""
echo "First twelve errors:"
grep -i error mcdrc.log | grep -v "Message Sum" | head -n 12 || echo "-"

echo "Last four errors:"
grep -i error mcdrc.log | grep -v "Message Sum" | tail -n 4 || echo "-"

# Did we get the desired result?
unset FAIL
ls -l */drc.summary > /dev/null || FAIL=1
if [ "$FAIL" ]; then
    echo ""; echo ""; echo ""
    echo "Cannot find drc.summary file. Looks like we FAILED."
    echo ""; echo ""; echo ""
    echo "tail mcdrc.log"
    tail -100 mcdrc.log | egrep -v '^touch' | tail -8
    exit 13
fi
# echo status=$?
echo "DRC SUMMARY FILE IS HERE:"
echo `pwd`/*/drc.summary

echo ""; echo ""; echo ""
echo "FINAL RESULT"
echo "------------------------------------------------------------------------"
echo ""

cat <<EOF
--- EXPECTED: 2 error(s), 2 warning(s)
CELL Tile_PE ................................................ TOTAL Result Count = 4
    RULECHECK OPTION.COD_CHECK:WARNING ...................... TOTAL Result Count = 1
    RULECHECK IO_CONNECT_CORE_NET_VOLTAGE_IS_CORE:WARNING ... TOTAL Result Count = 1
    RULECHECK M3.S.2 ........................................ TOTAL Result Count = 1
    RULECHECK M5.S.5 ........................................ TOTAL Result Count = 1
------------------------------------------------------------------------------------

EOF

############################################################################
# Detailed per-cell result
# CELL Tile_PE .............................. TOTAL Result Count = 248 (248)
#     RULECHECK OPTION.COD_CHECK:WARNING .... TOTAL Result Count = 1   (1)
#     RULECHECK IO_CON..._IS_CORE:WARNING ... TOTAL Result Count = 1   (1)
#     RULECHECK G.4:M2 ...................... TOTAL Result Count = 164 (164)
#     RULECHECK M2.W.4.1 .................... TOTAL Result Count = 82  (82)
# --------------------------------------------------------------------------
tmpfile=/tmp/tmp.test_pe.$USER.$$
echo ""; sed -n '/^CELL/,/^--- SUMMARY/p' */drc.summary \
    | grep -v SUMM > $tmpfile
echo ""

########################################################################
# PASS or FAIL?
n_checks=`grep RULECHECK $tmpfile | wc -l`
n_warnings=`egrep 'RULECHECK.*WARNING' $tmpfile | wc -l`
n_errors=`expr $n_checks - $n_warnings`
echo "+++ GOT: $n_errors error(s), $n_warnings warning(s)"
cat $tmpfile
echo ""
if [ $n_errors -le 2 ]; then
    echo "GOOD ENOUGH"; echo PASS; exit 0
else
    echo "TOO MANY ERRORS"; echo FAIL; exit 13
fi