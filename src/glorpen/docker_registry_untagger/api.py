'''
.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
'''
import requests
import re
import fnmatch
import hashlib
import random
import logging

class DockerRegistry(object):
    _version = "v2"
    
    _re_simple_name = re.compile(r'[a-z]+://([a-z0-9.-]+)(?:[0-9]+)?')
    
    def __init__(self, url, conf):
        super(DockerRegistry, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._url = url
        self._cache = {}
    
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
    
    def _api(self, path, method="get", data=None, json=None, content_type=None):
        headers = {}
        if content_type:
            headers['content-type'] = content_type
        
        if path.startswith("http"):
            url = path
        else:
            url = "%s/%s/%s" % (self._url, self._version, path)
        
        return getattr(self._req, method)(url, headers=headers, json=json, data=data)
    
    def check(self):
        return self._api("").status_code == 200
    
    def get_repositories(self):
        return tuple(self._api("_catalog").json().get("repositories", tuple()))
    
    def get_tags(self, repository):
        return tuple(self._api("%s/tags/list" % repository).json().get("tags") or [])
    
    def remove_image(self, repository, reference):
        r = self._api("%s/manifests/%s" % (repository, reference), 'delete')
        r.raise_for_status()
        print("remove", r.text, r.status_code)
    
    def get_reference(self, repository, tag):
        r = self._api("%s/manifests/%s" % (repository, tag))
        r.raise_for_status()
        #print(r.json())
        return r.headers.get("Docker-Content-Digest")
    
    def upload_fake_image(self, repository, tag):
        
        self.logger.info("Uploaded fake image to %s:%s", repository, tag)
        
        data = str(random.random()).encode()
        digest = "sha256:%s" % hashlib.sha256(data).hexdigest()
        
        d = {
            'schemaVersion': 2,
            'mediaType': 'application/vnd.docker.distribution.manifest.v2+json',
            'config': {
                'mediaType': 'application/vnd.docker.container.image.v1+json',
                'size': len(data),
                'digest': digest
            },
            'layers': [
            ]
        }
        
        r = self._api("%s/blobs/uploads/" % repository, method="post")
        url = r.headers['Location']
        
        r = self._api(
            "%s&digest=%s" % (url, digest),
            method="put",
            data=data,
            content_type="application/octet-stream"
        )
        r.raise_for_status()
        
        r = self._api(
            "%s/manifests/%s" % (repository, tag),
            method="put",
            content_type=d["mediaType"],
            json = d
        )
        r.raise_for_status()
        
        return r.headers['Docker-Content-Digest']
    
    def clear_cache(self):
        self.cache.clear()
    
    def tag(self, repository, source_tag, target_tag, cache=False):
        
        self.logger.info("Tagging %s:%s as %s:%s", repository, source_tag, repository, target_tag)
        cache_key = "manifest:%s:%s" % (repository, source_tag)
        
        if not cache or cache_key not in self._cache:
            r = self._api("%s/manifests/%s" % (repository, source_tag))
            r.raise_for_status()
            manifest = r.json()
            if cache:
                self._cache[cache_key] = manifest
        else:
            manifest = self._cache[cache_key]
        
        r = self._api(
            "%s/manifests/%s" % (repository, target_tag),
            method="put",
            content_type=manifest["mediaType"],
            json = manifest
        )
        r.raise_for_status()
    
    @property
    def name(self):
        return self._re_simple_name.match(self._url).group(1)

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
