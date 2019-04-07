'''
Created on 4 kwi 2019

@author: glorpen
'''
import unittest
from glorpen.docker_registry_cleaner.tests.functional import fixtures

class TestApi(unittest.TestCase):
    
    def _get_repositories_config(self, max_items=0):
        return {
          "all": {
              "paths": ["*"],
              "cleaners": {
                  "other": {
                      "type": "max",
                      "max_items": max_items
                  }
              }
          }
        }
    
    def test_cleaning_whole_repos(self):
        with fixtures._app(self._get_repositories_config(0)) as app:
            self.assertNotIn("simple-cleaning", app.list_repos(), "No image before uploading")
            with app._native.run():
                with fixtures._registry() as r:
                    r.upload_fake_image('simple-cleaning', 'latest', b'1231231232')
            self.assertDictContainsSubset({"simple-cleaning": ("latest",)}, app.list_repos(), "Image after uploading")
            app.clean()
            self.assertNotIn("simple-cleaning", app.list_repos(), "No image after cleaning")
    
    def test_cleaning_some_images(self):
        with fixtures._app(self._get_repositories_config(1)) as app:
            with app._native.run():
                with fixtures._registry() as r:
                    r.upload_fake_image('some-cleaning', '2', b'3333333332')
                    r.upload_fake_image('some-cleaning', '1', b'1231231232')
            app.clean()
            self.assertDictContainsSubset({"some-cleaning": ("2",)}, app.list_repos(), "Second image was not removed")
    
    def test_cross_tagging(self):
        with fixtures._app(self._get_repositories_config(1)) as app:
            with app._native.run():
                with fixtures._registry() as r:
                    r.upload_fake_image('first-cross-cleaning', '1', b'3333333332')
                    r.upload_fake_image('second-cross-cleaning', '1', b'3333333331')
                    r.upload_fake_image('first-cross-cleaning', '2', b'3333333331')
                    r.upload_fake_image('second-cross-cleaning', '2', b'3333333332')
            app.clean()
            self.assertDictContainsSubset({"first-cross-cleaning": ("2",), "second-cross-cleaning": ("2",)}, app.list_repos(), "Newer images are not removed")
    
    def test_nested_repos(self):
        with fixtures._app(self._get_repositories_config(0)) as app:
            with app._native.run():
                with fixtures._registry() as r:
                    r.upload_fake_image('some-nested/name', 'latest', b'11111111111')
            app.clean()
            self.assertNotIn("some-nested", app.list_repos(), "No image after cleaning")
