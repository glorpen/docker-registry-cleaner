'''
.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
'''

import logging
from glorpen.docker_registry_untagger import app
import argparse
import pathlib

if __name__ == "__main__":
    
    p = argparse.ArgumentParser()
    p.add_argument("--pretend", action="store_true")
    p.add_argument("config", action="store", type=pathlib.Path)
    
    ns = p.parse_args()
    
    logging.basicConfig(level=logging.DEBUG)
    
    a = app.AppCompositor(ns.config)
    a.register_module("glorpen.docker_registry_untagger.selectors.simple")
    a.register_module("glorpen.docker_registry_untagger.selectors.semver")
    untagger = a.commit()
    untagger.clean(pretend=ns.pretend)
