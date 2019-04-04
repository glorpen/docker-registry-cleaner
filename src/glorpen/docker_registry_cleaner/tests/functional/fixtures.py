'''
Created on 4 kwi 2019

@author: glorpen
'''
import tempfile
import yaml

def generate_config(repositories):
    f = tempfile.NamedTemporaryFile(mode="w+t", delete=False)
    yaml.dump({
        "repositories": repositories
    }, f)
    f.close()
    
    return f.name
