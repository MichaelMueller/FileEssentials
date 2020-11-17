import file_essentials_api
import sys
from typing import Dict


def start(args: Dict, log: file_essentials_api.Log):
    config_file = args["config_file"] if "config_file" in args.keys() else None


def boot(args: Dict, log: file_essentials_api.Log):
    # determine log level
    log_level = args["log_level"] if "log_level" in args.keys() else log.log_level
    if log_level not in log.log_levels.keys():
        log.warn("value '{}' is invalid".format(log_level), "log_level")
        log.info("falling back to log_level '{}'".format(log.log_level))
        log_level = log.log_level
    log.log_level = log_level

    # determine function
    func_name = args["run"] if "run" in args.keys() else "start"
    if func_name == "boot" or not hasattr(sys.modules[__name__], func_name):
        log.error("function '{}' unknown".format(func_name), "run")
        sys.exit(-1)

    getattr(sys.modules[__name__], func_name)(args, log)
