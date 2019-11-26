import sys
from time import gmtime, strftime

from git import Repo

from .data.config_data import ConfigData


class NoVersionFound(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


class RestrictedSymbol(Exception):
    def __init__(self, message, errors=None):
        super().__init__(message)
        self.errors = errors


def add_build_id(path, reponame, edition):
    def write_version(file, old_version, new_version):
        with open(file, 'r+') as config:
            data = config.read()
            data = data.replace(old_version, new_version)
            config.seek(0)
            config.truncate()
            config.write(data)

    git = Repo(path).git
    bundle = ConfigData(git=git, catalog=path, branch='origin/master')
    version = bundle.get_data('version', 'catalog', explict_raw=True)

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
    if '-' in version:
        raise RestrictedSymbol('Version contains restricted symbol \
            "-" in position %s' % version.index('-')).with_traceback(sys.exc_info()[2])

    if edition is None or edition == "None":
        edition = "ce"

    write_version(bundle.file, version, version + branch)
    return str(reponame) + '_v' + str(version) + branch + '_' + edition + '.tgz'
