'''
.. moduleauthor:: Arkadiusz Dzięgiel <arkadiusz.dziegiel@glorpen.pl>
'''
import requests
import fnmatch
import hashlib
import random
import logging

class DockerRegistry(object):
    """Manages single remote repository through Docker Registry API."""
    _version = "v2"
    
    def __init__(self, url, auth=None):
        """
        :param url: Docker Registry URL
        :type url: str
        :param auth: Optional user and password in format ``{"user": user, "password": password}``. 
        :type auth: dict
        """
        super(DockerRegistry, self).__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._url = url
        self._cache = {}
    
        self._req = requests.Session()
        
        self._setup()
        if auth:
            self._setup_auth(**auth)
    
    def _setup_auth(self, user, password):
        self._req.auth = (user, password)
    
    def _setup(self):
        self._req.headers.update({
            'accept': 'application/vnd.docker.distribution.manifest.v2+json'
        })
    
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
        """Checks wheter we can connect to registry."""
        return self._api("").status_code == 200
    
    def get_repositories(self):
        """List repositories names."""
        return tuple(self._api("_catalog").json().get("repositories", tuple()))
    
    def get_tags(self, repository):
        """List tag names for given repository."""
        return tuple(self._api("%s/tags/list" % repository).json().get("tags") or [])
    
    def remove_image(self, repository, reference):
        """Removes image by given reference."""
        self.logger.info("Removing image referenced by %s:%s", repository, reference)
        
        r = self._api("%s/manifests/%s" % (repository, reference), 'delete')
        r.raise_for_status()
    
    def get_reference(self, repository, tag):
        """Returns digest for given tag."""
        r = self._api("%s/manifests/%s" % (repository, tag))
        r.raise_for_status()
        return r.headers.get("Docker-Content-Digest")
    
    def upload_fake_image(self, repository, tag, data=None):
        
        self.logger.info("Uploaded fake image to %s:%s", repository, tag)
        
        data = str(random.random()).encode() if data is None else data
        digest = "sha256:%s" % hashlib.sha256(data).hexdigest()
        
        # get location for upload and start upload session
        r = self._api("%s/blobs/uploads/" % repository, method="post")
        url = r.headers['Location']
        
        # upload data and end upload process
        r = self._api(
            "%s&digest=%s" % (url, digest),
            method="put",
            data=data,
            content_type="application/octet-stream"
        )
        r.raise_for_status()
        
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
        
        # create manifest with given tag
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
    
    def close(self):
        self._req.close()
    
class DockerRepository(object):
    """Stores cleaner configuration for repository."""
    
    def __init__(self, name, patterns, selectors):
        super(DockerRepository, self).__init__()
        
        self.name = name
        self.patterns = patterns
        self.selectors = selectors
    
    def supports_repo(self, name):
        """Checks if name is matched by any of the patterns. Uses fnmatch."""
        for pattern in self.patterns:
            if fnmatch.fnmatch(name, pattern):
                return True
        return False
    
    def select_tags(self, tags):
        """Returns tags that should be deleted."""
        unmatched = list(sorted(tags, reverse=True))
        
        for_deletion = set()
        
        for s in self.selectors.values():
            old_unmatched = set(unmatched)
            selected, unmatched = s.select(unmatched)
            for_deletion.update(old_unmatched - set(unmatched) - set(selected))
            
        return for_deletion
