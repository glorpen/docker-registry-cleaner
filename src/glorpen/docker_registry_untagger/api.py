'''
Created on 18 wrz 2018

@author: glorpen
'''
import requests
import re
import fnmatch

class DockerRegistry(object):
    _version = "v2"
    
    def __init__(self, url, conf):
        super(DockerRegistry, self).__init__()
        self._url = url
    
        self._req = requests.Session()
        self._setup(**conf)
    
    def _setup_auth(self, user, password):
        self._req.auth = (user, password)
    
    def _setup(self, auth=None):
        self._req.headers.update({
            'accept': 'application/vnd.docker.distribution.manifest.v2+json'
        })
        if auth:
            self._setup_auth(**auth)
    
    def _api(self, path):
        return self._req.get("%s/%s/%s" % (self._url, self._version, path))
    
    def check(self):
        return self._api("").status_code == 200
    
    def get_repositories(self):
        return tuple(self._api("_catalog").json().get("repositories", tuple()))
    
    def get_tags(self, repository):
        return tuple(self._api("%s/tags/list" % repository).json().get("tags", tuple()))

class DockerRepository(object):
    def __init__(self, pattern, selectors):
        super(DockerRepository, self).__init__()
        
        self.pattern = pattern
        self.selectors = selectors
    
    def supports_repo(self, name):
        return fnmatch.fnmatch(name, self.pattern)
    
    def select_tags(self, tags):
        unmatched = list(sorted(tags, reverse=True))
        
        for_deletion = set()
        
        for s in self.selectors.values():
            old_unmatched = set(unmatched)
            selected, unmatched = s.select(unmatched)
            for_deletion.update(old_unmatched - set(unmatched) - set(selected))
            
        return for_deletion
