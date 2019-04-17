'''
.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
'''

import logging
import argparse
import pathlib
from glorpen.docker_registry_cleaner.app import AppCompositor
from inspect import signature

class Cli(object):
    """Commandline application.
    """
    
    log_levels = [
        logging.WARNING,
        logging.INFO,
        logging.DEBUG
    ]
    
    def __init__(self):
        super(Cli, self).__init__()
        
        self.parser = argparse.ArgumentParser()
        self._setup()
    
    def _setup(self):
        self.parser.add_argument("-v", "--verbose", action="count", default=0)
        self.parser.add_argument("-d", "--registry-data", action="store", default="/var/lib/registry")
        self.parser.add_argument("-b", "--registry-bin", action="store", default="registry")
        self.parser.add_argument("config", action="store", type=pathlib.Path)
        
        sp = self.parser.add_subparsers()
        p = sp.add_parser('list-repos')
        p.set_defaults(f=self.list_repos)
        
        p = sp.add_parser('clean')
        p.set_defaults(f=self.clean)
        p.add_argument("-p","--pretend", action="store_true")
    
    def set_verbosity(self, local_level):
        """Sets log levels, available are: 0:WARNING, 1:INFO, 2:DEBUG"""
        
        level = min(local_level, len(self.log_levels))
        logging.basicConfig(level=self.log_levels[level])
    
    def create_app(self, config_path, registry_data, registry_bin):
        """Creates application main object."""
        compositor = AppCompositor(config_path, registry_data, registry_bin)
        compositor.register_module("glorpen.docker_registry_cleaner.selectors.simple")
        compositor.register_module("glorpen.docker_registry_cleaner.selectors.semver")
        return compositor.commit()
    
    def run(self, args=None):
        """Runs application with provided args."""
        ns = self.parser.parse_args(args)
        self.set_verbosity(ns.verbose)
        app = self.create_app(ns.config, ns.registry_data, ns.registry_bin)
        
        args = {}
        for k in signature(ns.f).parameters.keys():
            if k == "app":
                v = app
            else:
                v = getattr(ns, k)
            
            args[k] = v
        
        ns.f(**args)
        
    def clean(self, app, pretend):
        """Run cleanup tasks."""
        app.clean(pretend=pretend)
    
    def list_repos(self, app):
        """Prints repositories."""
        for repo, images in app.list_repos().items():
            for tag in images:
                print("%s:%s" % (repo, tag))
            if not images:
                print("Empty repo %s" % repo)


if __name__ == "__main__":
    Cli().run()
