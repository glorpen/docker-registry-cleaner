'''
Created on 18 wrz 2018

@author: glorpen
'''
from glorpen.docker_registry_untagger.parser import Loader
import glorpen.di as di
import importlib
from glorpen.docker_registry_untagger import api
import functools
from collections import OrderedDict

def create_selector_config(cls, loader, config_key):
    return cls(loader.data.get(config_key))

class App(object):
    
    def __init__(self, config_path):
        super(App, self).__init__()
        self._c = di.Container()
    
        svc = self._c.add_service(Loader)
        svc.kwargs(path=config_path)
        
        svc = self._c.add_service(Factory)
        svc.kwargs(loader__svc=Loader)
        
        svc = self._c.add_service(Untagger)
        svc.kwargs(factory__svc=Factory)
    
    def add_selector(self, cls, symbol, config_cls=None):
        svc = self._c.get_definition(Factory)
        svc.call("add_selector", selector_cls=cls, symbol=symbol, config__svc=config_cls)
        
        config_schema = cls.get_config_fields()
        
        svc = self._c.get_definition(Loader)
        svc.call('add_selector_schema', type_name=symbol, schema=config_schema)
    
    def add_selector_config(self, cls, config_key=None):
        svc = self._c.add_service(cls)
        svc.factory(callable=create_selector_config, loader__svc=Loader, config_key=config_key, cls=cls)
        
        if config_key:
            svc = self._c.get_definition(Loader)
            config_schema = cls.get_config_fields()
            svc.call('add_selector_config_schema', config_key=config_key, schema=config_schema)
    
    def register_module(self, path):
        getattr(importlib.import_module(path), "register")(self)
    
    def commit(self):
        svc = self._c.get_definition(Loader)
        svc.call("load")
    
    @property
    def untagger(self):
        return self._c.get(Untagger)

class Factory(object):
    def __init__(self, loader):
        super(Factory, self).__init__()
        
        self._config = loader.data
        self._registries = None
        self._repositories = None
        self._selectors = {}
    
    def add_selector(self, selector_cls, symbol, config=None):
        self._selectors[symbol] = (selector_cls, config)
    
    def _load_registries(self):
        for name, conf in self._config["accounts"].items():
            yield api.DockerRegistry(name, conf)
    
    def _get_type(self, type, kwargs):
        # instantinated by parser.RepoConfigField
        s_cls, config = self._selectors[type]
        return s_cls(kwargs, config)
    
    def _load_repositories(self):
        for name, conf in self._config["repositories"].items():
            types = OrderedDict((k, self._get_type(*v)) for k,v in conf.items())
            yield api.DockerRepository(name, types)
    
    @property
    def registries(self):
        if self._registries is None:
            self._registries = tuple(self._load_registries())
        return self._registries
    
    @property
    def repositories(self):
        if self._repositories is None:
            self._repositories = tuple(self._load_repositories())
        return self._repositories

class Untagger(object):
    def __init__(self, factory):
        super(Untagger, self).__init__()
        
        self.factory = factory
        
    def search(self):
        #a._c.get("selectors.pattern")
        for r in self.factory.repositories:
            print("is supported", r.supports_repo("docker.example/example/asd"))
            #r = r.select_tags(('r-20', 'r-17', 'r-21', 'r-18', '16', '1.0.0', '1.0.1', 'latest', 'r-19', 'build-22', '0-131', '1.0.1-r1-alpine'))
            r = r.select_tags(('1.0.0', '1.0.1', '1.0.1-alpine', '1.0.2', '1.1.2', '1.1.3', '1.1.3+alpine.php70', '1.1.3+centos.php71', '1.1.3+alpine.php71', '1.1.4', '0.4.0', '0.5.0'))
            print("tags for deletion", r)
        return
        for r in self.factory.registries:
            print(r.check())
            for repo in r.get_repositories():
                print(r.get_tags(repo))


if __name__ == "__main__":
    a = App("/srv/.local/example.yml")
    a.register_module("glorpen.docker_registry_untagger.selectors.simple")
    a.register_module("glorpen.docker_registry_untagger.selectors.semver")
    a.commit()
    a.untagger.search()
