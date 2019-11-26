import os

import docker
import jinja2
import yaml


def python_mod_req(source_path, workspace, **kwargs):
    with open(os.path.join(source_path, kwargs['requirements']), 'r') as stream:
        client = docker.from_env()
        image = client.images.pull("arenadata/adcm:latest")
        data = yaml.safe_load(stream)
        command = '/bin/sh -c "pip freeze"'
        pmod_before = client.containers.run(image, command, remove=True).decode("utf-8").split()

        command = '/bin/sh -c "'
        if data.get('system_pkg'):
            command += 'apk add ' + ' '.join(data.get('system_pkg')) + ' >/dev/null ;'
        if data.get('python_mod'):
            command += ' pip install ' + ' '.join(data.get('python_mod')) + ' >/dev/null ;'
        command += ' pip freeze"'
        pmod_after = client.containers.run(image, command, remove=True).decode("utf-8").split()

        req_modules = [var for var in pmod_after if var not in pmod_before]

        command = '/bin/sh -c "'
        if data.get('system_pkg'):
            command += 'apk add ' + ' '.join(data.get('system_pkg')) + ' >/dev/null ;'
        if data.get('python_mod'):
            command += ' pip install ' + ' '.join(req_modules) + \
                       ' --no-deps -t ' + source_path + '/pmod ;'
            command += ' chown -R %s %s/pmod"' % (os.getuid(), source_path)
        volumes = {
            workspace: {'bind': workspace, 'mode': 'rw'}
        }
        client.containers.run(image, command, volumes=volumes, remove=True)


def splitter(*args, **kwargs):
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(args[0]))
    for file in kwargs['files']:
        tmpl = env.get_template(file)
        with open(os.path.join(args[0], (os.path.splitext(file)[0])), 'w') as f:
            f.write(tmpl.render(kwargs['edition']))


def get_type_func(tpe):
    types = {'python_mod_req': python_mod_req, 'splitter': splitter}
    return types[tpe]
