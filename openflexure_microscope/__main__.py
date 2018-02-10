from .keyboard_control import parse_command_line_arguments
from .keyboard_control import control_microscope_with_keyboard

if __name__ == '__main__':
    args = parse_command_line_arguments()
    control_microscope_with_keyboard(output=args.output)
