"""Utilities to setup a mingw based build setup for Python projects."""
# Author: Olivier Grisel <olivier.grisel@ensta.org>
# License: MIT
from __future__ import print_function
import os.path as op
import os
import sys
from subprocess import check_output
import time
import tarfile
import shutil
try:
    from urllib.request import urlretrieve
except ImportError:
    # Python 2 compat
    from urllib import urlretrieve

WINEPREFIX_PATTERN = 'wine-py{version}-{arch}'
PYTHON_MSI_PATTERN = "python-{version}{arch_marker}.msi"
PYTHON_URL_PATTERN = ("https://www.python.org/ftp/python/{version}/"
                      + PYTHON_MSI_PATTERN)
GET_PIP_SCRIPT = 'get-pip.py'
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
GCC_VERSION = '4.9.2'
MINGW_FILE_PATTERN = "mingw{arch}static-{version}.tar.xz"
MINGW_URL_PATTERN = ("https://bitbucket.org/carlkl/mingw-w64-for-python/"
                     "downloads/" + MINGW_FILE_PATTERN)

ENV_REGISTRY_KEY = b"[HKEY_CURRENT_USER\\Environment]"

DISTUTILS_CFG_CONTENT = u"""\
[build]
compiler=mingw32
"""

DISTUTILS_CFG_ISSUE_4709_CONTENT = u"""\

[build_ext]
define=MS_WIN64
"""


def run(command, prepend_wine='auto', *args, **kwargs):
    """Execute a windows command (using wine under Linux)"""
    if ((prepend_wine == 'auto' and sys.platform != 'win32')
            or prepend_wine is True):
        command = ['wine'] + command
    # Use the windows shell under Windows to get the PATH-based command
    # resolution. Under Linux, stick to wine and its fake registry.
    shell = sys.platform == 'win32'
    print("=> " + " ".join(command), flush=True)
    return check_output(command, *args, stderr=sys.stdout, shell=shell,
                        **kwargs)


def unix_path(path, env=None):
    if sys.platform == 'win32':
        # Nothing to do under Windows
        return path
    # Under Linux, compute the Linux path from the virtual windows path
    return run(['winepath', '--unix', path], env=env).decode('utf-8').strip()


def windows_path(path, env=None):
    if sys.platform == 'win32':
        # Nothing to do under Windows
        return path
    # Under Linux, compute the virtual Windows path from the concrete Linux
    # path
    return run(['winepath', '--windows', path],
               env=env).decode('utf-8').strip()


def set_env_in_registry(attribute, value, env=None):
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
    command = ['regedit', '/s', filename]
    run(command, env=env, prepend_wine=False)

    if sys.platform != 'win32':
        # XXX [hackish]: Wait for regedit to apply those updates under wine
        print("Waiting for registry to get updated...")
        if env is None or 'WINEPREFIX' not in env:
            user_reg = op.expanduser(op.join('~', '.wine', 'user.reg'))
        else:
            user_reg = op.join(env['WINEPREFIX'], 'user.reg')
        for i in range(100):
            if op.exists(user_reg):
                with open(user_reg, 'rb') as f:
                    if value_ascii in f.read():
                        print('registry updated')
                        break
            print('.', end='', flush=True)
            sys.stdout.flush()
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
    if not op.exists(download_folder):
        os.makedirs(download_folder)
    filepath = op.abspath(op.join(download_folder, filename))
    if not op.exists(filepath):
        print("Downloading %s to %s" % (url, filepath), flush=True)
        urlretrieve(url, filepath)
    return filepath


def install_python(python_home, version, arch, download_folder='.', env=None):
    local_python_folder = unix_path(python_home, env=env)
    if not op.exists(local_python_folder):
        python_msi_filepath = download_python(version, arch,
                                              download_folder=download_folder)

        # Install the Python MSI
        print('Installing Python %s (%s bit) to %s' % (
            version, arch, python_home))
        python_msi_filepath = windows_path(python_msi_filepath, env=env)
        command = ['msiexec', '/qn', '/i', python_msi_filepath,
                   '/log', 'msi_install.log', 'TARGETDIR=%s' % python_home]
        run(command, env=env)

    # Install / upgrade pip
    if not op.exists(download_folder):
        os.makedirs(download_folder)
    getpip_filepath = op.abspath(op.join(download_folder, GET_PIP_SCRIPT))
    if not op.exists(getpip_filepath):
        print("Downloading %s to %s" % (GET_PIP_URL, getpip_filepath),
              flush=True)
        urlretrieve(GET_PIP_URL, getpip_filepath)

    getpip_filepath = windows_path(getpip_filepath, env=env)
    run([python_home + '\\python', getpip_filepath], env=env)
    run([python_home + '\\python', '-m', 'pip', 'install', '--upgrade',
        'pip'], env=env)


def download_mingw(mingw_version="2014-11", arch="64", download_folder='.'):
    filename = MINGW_FILE_PATTERN.format(arch=arch, version=mingw_version)
    url = MINGW_URL_PATTERN.format(arch=arch, version=mingw_version)
    if not op.exists(download_folder):
        os.makedirs(download_folder)
    filepath = op.abspath(op.join(download_folder, filename))
    if not op.exists(filepath):
        print("Downloading %s to %s" % (url, filepath), flush=True)
        urlretrieve(url, filepath)
    return filepath


def install_mingw(mingw_home, mingw_version="2014-11", arch="64",
                  download_folder='.', env=None):
    # XXX: This function only works under Python 3.3+ that has native support
    # for extracting .tar.xz archives with the LZMA compression library.
    mingw_home_path = unix_path(mingw_home, env=env)
    if not op.exists(mingw_home_path):
        mingw_filepath = download_mingw(
            mingw_version=mingw_version, arch=arch,
            download_folder=download_folder)

        tmp_mingw_folder = op.join(download_folder, 'mingw%sstatic' % arch)
        if not op.exists(tmp_mingw_folder):
            print("Extracting %s..." % mingw_filepath, flush=True)
            with tarfile.open(mingw_filepath) as f:
                f.extractall(download_folder)
        print("Installing mingw to %s..." % mingw_home, flush=True)
        shutil.move(tmp_mingw_folder, mingw_home_path)


def configure_mingw(mingw_home, python_home, python_version, arch, env=None):
    mingw_home_path = unix_path(mingw_home, env=env)
    python_home_path = unix_path(python_home, env=env)
    v_major, v_minor = tuple(int(x) for x in python_version.split('.')[:2])

    mingw_bin = mingw_home + "\\bin\\"

    # Generate the libpythonXX.dll.a archive
    dlla_name = 'libpython%d%d.dll.a' % (v_major, v_minor)
    dlla_path = op.join(python_home_path, 'libs', dlla_name)
    if not op.exists(dlla_path):
        print('Generating %s from %s' % (dlla_name, python_home))
        dll_name = 'python%d%d.dll' % (v_major, v_minor)
        def_name = 'python%d%d.def' % (v_major, v_minor)

        # Look for the Python dll in the Python folder.
        dll_win_path = python_home + '\\' + dll_name
        if not op.exists(unix_path(dll_win_path, env=env)):
            print('Python dll not found in %s' % dll_win_path)

            # Look for a copy of the Python dll installed in the system folder:
            if arch == '64':
                # On a 64 bit system, 64 bit DLLs are stored in System64...
                dll_win_path = 'C:\\Windows\\System32\\' + dll_name
            else:
                # 32 bit DLLs are stored in SysWoW64
                dll_win_path = 'C:\\Windows\\SysWoW64\\' + dll_name

        if not op.exists(unix_path(dll_win_path, env=env)):
            raise RuntimeError("Could not find %s" % dll_win_path)

        run([mingw_bin + 'gendef', dll_win_path], env=env)
        run([mingw_bin + 'dlltool', '-D', dll_win_path, '-d', def_name, '-l',
            dlla_name], env=env)
        print("Moving %s to %s" % (dlla_name, dlla_path), flush=True)
        shutil.move(dlla_name, dlla_path)

    # Install a disutils.cfg file to select mingw as the default compiler
    # (useful for pip in particular)
    distutils_cfg = op.join(python_home_path, 'Lib', 'distutils',
                            'distutils.cfg')
    print("Setting mingw as the default compiler in %s" % distutils_cfg,
          flush=True)
    with open(distutils_cfg, 'w') as f:
        f.write(DISTUTILS_CFG_CONTENT)

    # Use the correct MSVC runtime depending on the arch and the Python version
    if arch == '64':
        arch_folder = 'x86_64-w64-mingw32'
    elif arch == '32':
        arch_folder = 'i686-w64-mingw32'
    else:
        raise ValueError("Unsupported architecture: %s" % arch)
    vc_tag = '100' if v_major == 3 else '90'
    libmsvcr = 'libmsvcr%s.a' % vc_tag
    specs = 'specs%s' % vc_tag

    # Copy the msvc runtime library
    libmsvcr_path = op.join(mingw_home_path, arch_folder, 'lib', libmsvcr)
    libs_folder = op.join(python_home_path, 'libs')
    print('Copying %s to %s' % (libmsvcr_path, libs_folder),
          flush=True)
    shutil.copy2(libmsvcr_path, libs_folder)

    # Configure the msvc runtime specs file
    specs_folder = op.join(mingw_home_path, 'lib', 'gcc', arch_folder,
                           GCC_VERSION)
    specs_source_path = op.join(specs_folder, specs)
    specs_target_path = op.join(specs_folder, 'specs')
    print('Copying %s to %s' % (specs_source_path, specs_target_path),
          flush=True)
    shutil.copy2(specs_source_path, specs_target_path)


def fix_issue_4709(python_home, python_version, arch, env=None):
    # http://bugs.python.org/issue4709
    if arch == "64" and python_version.startswith('2.'):
        python_home_path = unix_path(python_home, env=env)
        distutils_cfg = op.join(python_home_path, 'Lib', 'distutils',
                                'distutils.cfg')
        print("Setting workaround for issue 4709 in %s" % distutils_cfg,
              flush=True)
        with open(distutils_cfg, 'a') as f:
            f.write(DISTUTILS_CFG_ISSUE_4709_CONTENT)


def make_wine_env(python_version, python_arch, wine_prefix_root=None):
    """Set the wineprefix environment"""
    env = os.environ.copy()
    if sys.platform == 'win32':
        # Do nothing under Windows
        return env

    if wine_prefix_root is not None:
        wine_prefix_root = op.abspath(wine_prefix_root)
        if not op.exists(wine_prefix_root):
            os.makedirs(wine_prefix_root)
        wine_prefix = WINEPREFIX_PATTERN.format(
            version=python_version, arch=python_arch)
        env['WINEPREFIX'] = op.join(wine_prefix_root, wine_prefix)

    if python_arch == '32':
        # wine 64 has many bugs when running 32 bit apps, better force the
        # creation of a wine 32 prefix
        env['WINEARCH'] = 'win32'
    return env


def setup_wine_env(python_home, python_version, python_arch, mingw_home,
                   wine_prefix_root=None, download_folder='downloads'):
    env = make_wine_env(python_version, python_arch,
                        wine_prefix_root=wine_prefix_root)
    install_python(python_home, python_version, python_arch,
                   download_folder=download_folder, env=env)
    install_mingw(mingw_home, arch=python_arch,
                  download_folder=download_folder, env=env)
    custom_path = make_path(python_home, mingw_home)
    if sys.platform == 'win32':
        # Under Windows, prepend the existing PATH with the new folders in
        # in the current process environment
        env['PATH'] = custom_path + ";" + env['PATH']
    else:
        # Under wine: use the registry to setup the path
        set_env_in_registry(u'PATH', custom_path, env=env)
    configure_mingw(mingw_home, python_home, python_version, python_arch,
                    env=env)
    fix_issue_4709(python_home, python_version, python_arch, env=env)
    # Sanity check to make sure that python and gcc are in the PATH
    run(['python', '--version'], env=env)
    run(['gcc', '--version'], env=env)


def setup_configure_from_yaml(config_filename):
    import yaml
    with open(config_filename) as f:
        config = yaml.load(f)
    wine_prefix_root = config.get('wine_prefix_root', 'wine')
    environments = config.get('matrix', ())
    for environment in environments:
        python_home = environment['python_home']
        python_version = environment['python_version']
        python_arch = environment['python_arch']
        mingw_home = environment['mingw_home']
        download_folder = environment.get('DOWNLOAD_FOLDER', '.')
        setup_wine_env(python_home, python_version, python_arch, mingw_home,
                       wine_prefix_root=wine_prefix_root,
                       download_folder=download_folder)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Setup one isolated WINEPREFIX install per configuration
        # provided in a YAML formatted specification.
        setup_configure_from_yaml(sys.argv[1])
    else:
        # Perform one setup using environment variables. The WINEPREFIX
        # environment variable should be defined externally if needed.
        try:
            python_home = os.environ['PYTHON_HOME']
            python_version = os.environ['PYTHON_VERSION']
            python_arch = os.environ['ARCH']
        except KeyError as e:
            print("pywinbuilder require configuration as"
                  " environment variable: %s" % e)
            sys.exit(1)
        mingw_home = os.environ.get('MINGW_HOME', 'C:\\mingw-static')
        download_folder = os.environ.get('DOWNLOAD_FOLDER', '.')
        setup_wine_env(python_home, python_version, python_arch, mingw_home,
                       download_folder=download_folder)
