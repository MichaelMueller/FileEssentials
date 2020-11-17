import file_essentials_api
import file_essentials_shell
import sys

if __name__ == '__main__':
    log = file_essentials_api.Log()
    args = {}
    num_args = len(sys.argv)
    next_numeric_key = 0
    i = 1
    while i < num_args:
        arg = sys.argv[i]  # type: str
        curr_key = None
        if arg.startswith("--") and len(arg) > 2:
            curr_key = arg[2:].lower()
        elif arg.startswith("-") and len(arg) > 1:
            curr_key = arg[1:].lower()
        if curr_key:
            i = i + 1
            arg = sys.argv[i] if i < num_args else None
            args[curr_key] = arg
        else:
            args[next_numeric_key] = arg
            next_numeric_key = next_numeric_key + 1
        i = i + 1

    file_essentials_shell.boot(args, log)
