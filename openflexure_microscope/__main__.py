from .keyboard_control import parse_command_line_arguments
from .keyboard_control import control_microscope_with_keyboard
from .utilities.recalibrate_microscope import recalibrate_microscope
import argparse

def main():
    parser = argparse.ArgumentParser(description="Control an Openflexure Microscope")
    parser.add_argument("--recalibrate", action="store_true", 
            help="Reset the microscope's settings and regenerate the lens shading correction table.  Saves to ./microscope_settings.npz.")
    parser.add_argument("--output", help="directory or filepath (with %%d wildcard) for saved images", default="~/Desktop/images")
    args = parser.parse_args()
    if args.recalibrate:
        recalibrate_microscope()
    else:
        control_microscope_with_keyboard(output=args.output)

if __name__ == '__main__':
    main()

