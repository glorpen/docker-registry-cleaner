'''
Created on 27 paź 2018

@author: glorpen
'''
from glorpen.docker_registry_untagger.parser import Loader
import glorpen.di as di
import importlib
from glorpen.docker_registry_untagger import api
from collections import OrderedDict
import logging

def create_selector_config(cls, loader, config_key):
    return cls(loader.data.get(config_key))

class AppCompositor(object):
    
    def __init__(self, config_path):
        super(AppCompositor, self).__init__()
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
    
    fake_tag = "untagger-for-deletion"
    
    def __init__(self, factory):
        super(Untagger, self).__init__()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.factory = factory
    
    def get_supported_cleaner(self, repository):
        for r in self.factory.repositories:
            if r.supports_repo(repository):
                return r
    
    def delete_tags(self, registry, repo, tags):
        fake_ref = registry.upload_fake_image(repo, self.fake_tag)
        
        for t in tags:
            if t == self.fake_tag:
                continue
            # dont delete, just tag fake image with tags for deletion
            registry.tag(repo, self.fake_tag, t, cache=True)
        
        # will remove _image_ referenced by tag, not just tag
        registry.remove_image(repo, fake_ref)
    
    def clean_repository(self, registry, repo, pretend=False):
        repo_name = "%s/%s" % (registry.name, repo)
        cleaner = self.get_supported_cleaner(repo_name)
        
        if cleaner:
            tags = registry.get_tags(repo)
            if tags:
                self.logger.info("Cleaner for %s found", repo_name)
                tags_for_deletion = cleaner.select_tags(tags)
                
                if tags_for_deletion:
                    if pretend:
                        for i in tags_for_deletion:
                            self.logger.info("Would delete %s:%s", repo_name, i)
                    else:
                        self.delete_tags(registry, repo, tags_for_deletion)
                    return True
            else:
                self.logger.info("Found empty repo %s", repo_name)
        else:
            self.logger.info("Cleaner for %s not found", repo_name)
        
        return False
    
    # TODO: removing empty repository when GC in docker-registry
    def clean(self, pretend=False):
        for r in self.factory.registries:
            if not r.check():
                raise Exception('Could not connect to %s' % r)
            
            for repo in r.get_repositories():
                self.clean_repository(r, repo, pretend)
