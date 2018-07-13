"""
This program generates the verilog for the connect box and parses it into a
Magma circuit. The circuit declaration is printed at the end of the program.
"""
import argparse
from connect_box.cb_wrapper import define_cb


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("infile", type=str)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--num_tracks", type=int, default=10)
    parser.add_argument("--feedthrough_outputs", type=str, default=("1"*10))
    parser.add_argument("--has_constant", type=int, default=0)
    parser.add_argument("--default_value", type=int, default=0)
    return parser


def main(args):

    # Check some of the inputs.
    for c in args.feedthrough_outputs:
        assert c == "1" or c == "0"

    cb = define_cb(args.width,
                   args.num_tracks,
                   args.feedthrough_outputs,
                   args.has_constant,
                   args.default_value,
                   args.infile)
    print(cb)

if __name__ == "__main__":
    parser = create_parser()
    main(parser.parse_args())
