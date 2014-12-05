from __future__ import print_function
import os.path as op
import os
import sys
from subprocess import check_output
import yaml
import time
import tarfile
import shutil
try:
    from urllib.request import urlretrieve
except ImportError:
    # Python 2 compat
    from urllib2 import urlretrieve

WINEPREFIX_PATTERN = 'wine-py{version}-{arch}'
PYTHON_MSI_PATTERN = "python-{version}{arch_marker}.msi"
PYTHON_URL_PATTERN = ("https://www.python.org/ftp/python/{version}/"
                      + PYTHON_MSI_PATTERN)
MINGW_FILE_PATTERN = "mingw{arch}static-{version}.tar.xz"
MINGW_URL_PATTERN = ("https://bitbucket.org/carlkl/mingw-w64-for-python/"
                     "downloads/" + MINGW_FILE_PATTERN)

ENV_REGISTRY_KEY = (rb"[HKEY_CURRENT_USER\Environment]")


def run(command, *args, prepend_wine='auto', **kwargs):
    """Execute a windows command (using wine under Linux)"""
    if ((prepend_wine == 'auto' and sys.prefix != 'win32')
            or prepend_wine is True):
        command = ['wine'] + command
    print("=> " + " ".join(command))
    return check_output(command, *args, stderr=sys.stdout, **kwargs)


def set_env(attribute, value, env=None):
    """Edit the wine registry to configure an environment variable"""
    print("Setting '%s'='%s'" % (attribute, value))

    # Prepare a '.reg' file with the new parameters
    filename = '_custom_path.reg'
    value_line = u'"%s"="%s"' % (attribute, value.replace(u'\\', u'\\\\'))
    value_ascii = value_line.encode('ascii')
    with open(filename, 'wb') as f:
        f.write(ENV_REGISTRY_KEY)
        f.write(b'\r\n')
        f.write(value_ascii)
        f.write(b'\r\n')

    # Use regedit to load the new configuration
    command = ['regedit', filename]
    run(command, env=env, prepend_wine=False)

    # XXX [hackish]: Wait for regedit to apply those updates
    print("Waiting for registry to get updated...")
    user_reg = op.join(env['WINEPREFIX'], 'user.reg')
    for i in range(100):
        if op.exists(user_reg):
            with open(user_reg, 'rb') as f:
                if value_ascii in f.read():
                    print('registry updated')
                    break
        print('.', end='')
        time.sleep(1)


def make_path(python_home, mingw_home):
    python_path = "{python_home};{python_home}\\Scripts".format(**locals())
    mingw_path = "{mingw_home}\\bin".format(**locals())
    return ";".join([python_path, mingw_path])


def download_python(version, arch, download_folder='.', env=None):
    if arch == "32":
        arch_marker = ""
    elif arch == "64":
        arch_marker = ".amd64"
    else:
        raise ValueError("Unsupported windows architecture: %s" % arch)

    url = PYTHON_URL_PATTERN.format(version=version, arch_marker=arch_marker)
    filename = PYTHON_MSI_PATTERN.format(
        version=version, arch_marker=arch_marker)
    filepath = op.join(download_folder, filename)
    if not op.exists(filepath):
        print("Downloading %s to %s" % (url, filepath))
        urlretrieve(url, filepath)
    return filepath


def install_python(python_home, version, arch, download_folder='.', env=None):
    if sys.platform == 'win32':
        local_python_folder = python_home
    else:
        local_python_folder = run(['winepath', python_home],
                                  env=env).decode('utf-8').strip()
    if not op.exists(local_python_folder):
        python_msi_filepath = download_python(version, arch)

        if sys.platform != 'win32':
            python_msi_filepath = run(['winepath', python_msi_filepath],
                                      env=env).decode('utf-8').strip()

        print('Installing Python %s (%s bit) to %s' % (
            version, arch, python_home))
        command = ['msiexec', '/qn', '/i', python_msi_filepath,
                   '/log', 'msi_install.log', 'TARGETDIR=%s' % python_home]
        run(command, env=env)


def download_mingw(mingw_version="2014-11", arch="64", download_folder='.'):
    filename = MINGW_FILE_PATTERN.format(arch=arch, version=mingw_version)
    url = MINGW_URL_PATTERN.format(arch=arch, version=mingw_version)
    filepath = op.join(download_folder, filename)
    if not op.exists(filepath):
        print("Downloading %s to %s" % (url, filepath))
        urlretrieve(url, filepath)
    return filepath


def install_mingw(mingw_home, mingw_version="2014-11", arch="64",
                  download_folder='.', env=None):
    # XXX: This function only works under Python 3.3+ that has native support
    # for extracting .tar.xz archives with the LZMA compression library.
    if sys.platform == 'win32':
        mingwn_home_path = mingw_home
    else:
        # Under Linux, compute the Linux path from the virtual windows path
        mingwn_home_path = run(['winepath', mingw_home],
                               env=env).decode('utf-8').strip()
    if not op.exists(mingwn_home_path):
        mingw_filepath = download_mingw(
            mingw_version=mingw_version, arch=arch,
            download_folder=download_folder)

        tmp_mingw_folder = op.join(download_folder, 'mingw%sstatic' % arch)
        if not op.exists(tmp_mingw_folder):
            print("Extracting %s..." % mingw_filepath)
            with tarfile.open(mingw_filepath) as f:
                f.extractall(download_folder)
        print("Installing mingwn to %s..." % mingw_home)
        shutil.move(tmp_mingw_folder, mingwn_home_path)


def congigure_mingw(mingw_home, python_home, arch, env=None):
    pass


def make_wine_env(python_version, python_arch, wine_prefix_root='.'):
    """Set the wineprefix environment"""
    wine_prefix_root = op.abspath(wine_prefix_root)
    env = os.environ.copy()
    if sys.platform != 'win32':
        wine_prefix = WINEPREFIX_PATTERN.format(
            version=python_version, arch=python_arch)
        env['WINEPREFIX'] = op.join(wine_prefix_root, wine_prefix)
    return env


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        config = yaml.load(f)
    environments = config.get('environments', ())
    for environment in environments:
        python_home = environment['python_home']
        python_version = environment['python_version']
        python_arch = environment['python_arch']
        mingw_home = environment['mingw_home']

        env = make_wine_env(python_version, python_arch)
        install_python(python_home, python_version, python_arch, env=env)
        install_mingw(mingw_home, arch=python_arch,
                      download_folder='.', env=env)
        set_env(u'PATH', make_path(python_home, mingw_home), env=env)
        congigure_mingw(mingw_home, python_home, python_arch, env=env)

        # Sanity check to make sure that python and gcc are in the PATH
        run(['python', '--version'], env=env)
        run(['gcc', '--version'], env=env)
