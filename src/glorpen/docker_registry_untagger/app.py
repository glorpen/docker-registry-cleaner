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

class SelectorFactory(object):
    def __init__(self):
        super(SelectorFactory, self).__init__()
        self._selectors = {}
    
    def add_selector(self, cls, symbol, config=None):
        self._selectors[symbol] = (cls, config)
    
    def get(self, symbol, kwargs):
        s_cls, config = self._selectors[symbol]
        return s_cls(kwargs, config)

class AppCompositor(object):
    
    def __init__(self, config_path):
        super(AppCompositor, self).__init__()
        self._c = di.Container()
    
        svc = self._c.add_service(Loader)
        svc.kwargs(path=config_path)
        
        svc = self._c.add_service(SelectorFactory)
        
        svc = self._c.add_service("app.registries")
        svc.implementation(self._create_registries)
        svc.kwargs(loader__svc=Loader)
        
        svc = self._c.add_service("app.cleaners")
        svc.implementation(self._create_cleaners)
        svc.kwargs(loader__svc=Loader, selector_factory__svc=SelectorFactory)
        
        svc = self._c.add_service(Untagger)
        svc.kwargs(registries__svc="app.registries", cleaners__svc="app.cleaners")
    
    def add_selector(self, cls, symbol, config_cls=None):
        svc = self._c.get_definition(SelectorFactory)
        svc.call("add_selector", cls=cls, symbol=symbol, config__svc=config_cls)
        
        config_schema = cls.get_config_fields()
        
        svc = self._c.get_definition(Loader)
        svc.call('add_selector_schema', type_name=symbol, schema=config_schema)
    
    def create_selector_config(self, cls, loader: Loader, config_key):
        return cls(loader.data.get(config_key))
    
    def add_selector_config(self, cls, config_key=None):
        svc = self._c.add_service(cls)
        svc.factory(callable=self.create_selector_config, loader__svc=Loader, config_key=config_key, cls=cls)
        
        if config_key:
            svc = self._c.get_definition(Loader)
            config_schema = cls.get_config_fields()
            svc.call('add_selector_config_schema', config_key=config_key, schema=config_schema)
    
    def register_module(self, path):
        getattr(importlib.import_module(path), "register")(self)
    
    def _create_registries(self, loader: Loader):
        registries = []
        for name, conf in loader.data["accounts"].items():
            registries.append(api.DockerRegistry(name, conf))
        return tuple(registries)
    
    def _create_cleaners(self, loader, selector_factory: SelectorFactory):
        cleaners = []
        for name, conf in loader.data["repositories"].items():
            types = OrderedDict((k, selector_factory.get(*v)) for k,v in conf["cleaners"].items())
            cleaners.append(api.DockerRepository(name, conf["paths"], types))
        return tuple(cleaners)
    
    def commit(self):
        svc = self._c.get_definition(Loader)
        svc.call("load")
        
        return self._c.get(Untagger)

class Untagger(object):
    
    fake_tag = "untagger-for-deletion"
    
    def __init__(self, registries, cleaners):
        super(Untagger, self).__init__()
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.registries = registries
        self.cleaners = cleaners
    
    def get_supported_cleaner(self, repository):
        for r in self.cleaners:
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
            self.logger.info("Using cleaner %r for repo %r", cleaner.name, repo_name)
            if tags:
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
        for r in self.registries:
            if not r.check():
                raise Exception('Could not connect to %s' % r)
            
            for repo in r.get_repositories():
                self.clean_repository(r, repo, pretend)
    
    def list_repos(self):
        ret = {}
        for r in self.registries:
            for repo in r.get_repositories():
                ret["%s/%s" % (r.name, repo)] = r.get_tags(repo)
        return ret
