# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import subprocess
import sys
import tarfile
from distutils.dir_util import copy_tree
from fnmatch import fnmatch
from io import BytesIO
from tempfile import mkdtemp
from time import gmtime, strftime

import docker
import yaml
from adcm_client.packer.data.config_data import ConfigData
from git import Repo


class NoVersionFound(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


# grab required python modules that are not in adcm:latest
def python_mod_req(file, source_path, workspace):
    with open(str(file), 'r') as stream:
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
                       ' --no-deps -t ' + source_path + '/pmod"'

        volumes = {
            workspace: {'bind': workspace, 'mode': 'rw'}
        }
        client.containers.run(image, command, volumes=volumes, remove=True)


func = {
    'python_mod_req': python_mod_req,
}


def except_var(config):
    tar_except = []
    for k, v in config.items():
        if '_dir' in k:
            tar_except.append(v)
    for k in config.get('processing'):
        if k.get('except_file', False):
            tar_except.append(k.get('file'))
    return tar_except


def spec_processing(config, path, workspace):
    info = ''
    for x in config.get('processing'):
        if x.get('script'):
            script_name = path + '/' + config[x['name'] + '_dir'] + '/' + x['script']
            command = ['python3', script_name, path + '/' + x['file']]
            info += subprocess.check_output(command).decode("utf-8")
        else:
            func[x['name']](path + '/' + x['file'], path, workspace)  # very dirty
    return info


def add_build_id(path, reponame):
    def write_version(file, old_version, new_version):
        with open(file, 'r+') as config:
            data = config.read()
            data = data.replace(old_version, new_version)
            config.seek(0)
            config.truncate()
            config.write(data)

    git = Repo(path).git
    bundle = ConfigData(git=git, catalog=path, branch='origin/master')
    version = bundle.get_data('version', 'catalog', explict_raw=True).split('-')[0]

    if git.describe('--all').split('/')[0] == 'tags':
        tag = git.describe('--all')
        branch = [out.split('/')[2] for out in git.branch('-a', '--contains', tag).splitlines()
                  if 'origin' in out][0]
    else:
        try:
            branch = git.describe('--all').split('/')[2]
        except IndexError:
            branch = git.rev_parse('--abbrev-ref', 'HEAD')

    if branch == 'master':
        branch = '-1'
    elif git.describe('--all').split('/')[1] == 'pr':
        branch = '-rc' + branch + '.' + strftime("%Y%m%d%H%M%S", gmtime())
    else:
        branch = '-' + branch

    if version is None:
        raise NoVersionFound('No version detected').with_traceback(sys.exc_info()[2])

    write_version(bundle.file, version, version + branch)
    return str(reponame) + '_v' + str(version) + branch + '.tar.gz'


def build(reponame, repopath, workspace='/tmp', tarball_path=None):
    """Moves sources to workspace inside of temporary directory. \
    Some operations over sources cant be proceed concurent(for exemple in pytest with xdist \
    plugin) that why each thread need is own tmp dir with sources. \
    Also when there is complex docker containers launching to process some information there is \
    necessery to share same workspace with every used container.
    Proceed spec file.
    Writes build number to bundle config file.
    Form a list of name paterns to be ignored from sources.
    Recursively add files to tarball.

    :param reponame: arenadata repository name. Used for naming aftifact and tmp dir.
    :type reponame: str
    :param repopath: Where bundle sources are
    :type repopath: str
    :param workspace: where build operations will be performed, defaults to /tmp.
    :type workspace: str, optional
    :param tarball_path: where to copy builded bundle, defaults to None.
    None means that tarball will be left in temporary directory inside of workspace.
    :type tarball_path: str, optional
    :return: return a dict. Keys:
        info - some output usefull for visual control
        tarball - path to aftifact
    :rtype: dict
    """

    def add_to_tar(directory, except_list, tar, top_dir=None):
        """Recursive function to add sources to bundle.

        :param directory: directory with sources
        :type directory: str
        :param except_list: list with name paterns to be ignored
        :type except_list: list
        :param tar: inmemory tarfile
        :type tar: tarfile
        :param top_dir: top directory of current files that are added to tarfile, defaults to None
        :type top_dir: str, optional
        """
        for sub in os.listdir(directory):
            args = [x for x in [top_dir, sub] if x]
            if not [sub for n in except_list if fnmatch(os.path.join(*args), n) or
                    fnmatch(sub, n)]:
                if os.path.isdir(os.path.join(directory, sub)):
                    add_to_tar(os.path.join(directory, sub), except_list, tar, os.path.join(*args))
                else:
                    tar.add(os.path.join(directory, sub), arcname=os.path.join(*args))

    # tar exception string initialization
    tar_except = []
    # info string initialization. All output will be gathered here.
    info = ''

    # init temp directory
    temp = mkdtemp(prefix=reponame + '_', dir=workspace)
    copy_tree(repopath, temp)
    repopath = temp
    # spec file running
    try:
        with open(str(repopath + '/spec.yaml'), 'r') as file:
            spec = yaml.safe_load(file)

            info += spec_processing(spec, repopath, workspace)
            tar_except = except_var(spec)
    except IOError:
        pass

    tar_except.extend([
        'spec.yaml', 'pylintrc', '.[0-9a-zA-Z]*', '*pycache*',
        'README.md', '*test*', '*requirements*', '*gz', '*md'])
    stream = BytesIO()
    # naming rules
    tarname = add_build_id(repopath, reponame)
    tar = tarfile.open(fileobj=stream, mode='w|gz')
    add_to_tar(repopath, tar_except, tar)
    info = "#######\n Files list:\n%s\n#######" % "\n".join(tar.getnames())
    tar.close()

    # dir where to create bundle
    tarpath = repopath if not tarball_path else tarball_path
    os.makedirs(tarpath, exist_ok=True)

    # saving tarball
    tarball = os.path.join(tarpath, tarname)
    with open(tarball, 'wb') as file:
        stream.seek(0)
        file.write(stream.read())

    return {'info': info, 'tarball': tarball}
