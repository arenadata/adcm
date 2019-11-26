import logging
import sys
from os.path import join
from subprocess import check_output

import yaml

from .types import get_type_func


class SpecFile:

    def __init__(self, spec):
        try:
            with open(spec, 'r') as file:
                self.data = yaml.safe_load(file)
        except FileNotFoundError:
            self.data = {}

    def to_1_0(self):
        new_spec = dict([('version', None),
                         ('editions', [{
                             'name': None,
                             'exclude': self.except_var(self.data),
                             'preprocessors': []}])])
        for i in self.data.get('processing', {}):
            if i.get('script'):
                new_spec['editions'][0]['preprocessors'].append(
                    {
                        'type': 'script',
                        'script': join(self.data[i['name'] + '_dir'], i['script']),
                        'args': [i['file']]
                    }
                )
            elif i.get('name') == 'python_mod_req':
                new_spec['editions'][0]['preprocessors'].append(
                    {
                        'type': i['name'],
                        'requirements': i['file']
                    }
                )
            else:
                sys.exit('Used unrecognized func:%s' % i.get('name'))
        return new_spec

    def normalize_spec(self):
        versions = ['1.0']
        migrations = dict([('1.0', self.to_1_0)])
        index = versions.index(self.data.get('version')) + 1\
            if self.data.get('version') in versions else 0
        for i in versions[index:]:
            self.data = migrations[i]()

        return self.data

    # deprecated method. Needed for backward compatibility with old specs
    def except_var(self, config):
        tar_except = []
        for k, v in config.items():
            if '_dir' in k:
                tar_except.append(v)
        for k in config.get('processing', {}):
            if k.get('except_file', False):
                tar_except.append(k.get('file'))
        return tar_except


def spec_processing(spec: SpecFile, path, workspace):
    for edition in spec.data['editions']:
        for x in edition['preprocessors']:
            if x.get('script'):
                command = [x['script']]
                command.extend(x.get('args'))
                logging.info(check_output(command, cwd=path[edition['name']]).decode("utf-8"))
            else:
                jinja_values = {'edition': edition['name']}
                get_type_func(x['type'])(path[edition['name']], workspace,
                                         edition=jinja_values, **x)
