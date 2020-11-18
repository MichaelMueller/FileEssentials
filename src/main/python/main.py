import api
import sys

if __name__ == '__main__':
    # init
    args = api.ArgvArgs()
    log = api.Log(log_level=args.get("log_level", "info"))
    file_essentials = api.FileEssentials()
    sys.exit(file_essentials.boot(args, log))
