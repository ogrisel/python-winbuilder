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
    from urllib2 import urlretrieve

WINEPREFIX_PATTERN = 'wine-py{version}-{arch}'
PYTHON_MSI_PATTERN = "python-{version}{arch_marker}.msi"
PYTHON_URL_PATTERN = ("https://www.python.org/ftp/python/{version}/"
                      + PYTHON_MSI_PATTERN)
GCC_VERSION = '4.9.2'
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
    if not op.exists(download_folder):
        os.makedirs(download_folder)
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
        python_msi_filepath = download_python(version, arch,
                                              download_folder=download_folder)

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
    if not op.exists(download_folder):
        os.makedirs(download_folder)
    filepath = op.join(download_folder, filename)
    if not op.exists(filepath):
        print("Downloading %s to %s" % (url, filepath))
        urlretrieve(url, filepath)
    return filepath


def normalize_win_path(win_path, env=None):
    if sys.platform == 'win32':
        # Nothing to do under Windows
        return win_path
    # Under Linux, compute the Linux path from the virtual windows path
    return run(['winepath', win_path], env=env).decode('utf-8').strip()


def install_mingw(mingw_home, mingw_version="2014-11", arch="64",
                  download_folder='.', env=None):
    # XXX: This function only works under Python 3.3+ that has native support
    # for extracting .tar.xz archives with the LZMA compression library.
    mingw_home_path = normalize_win_path(mingw_home, env=env)
    if not op.exists(mingw_home_path):
        mingw_filepath = download_mingw(
            mingw_version=mingw_version, arch=arch,
            download_folder=download_folder)

        tmp_mingw_folder = op.join(download_folder, 'mingw%sstatic' % arch)
        if not op.exists(tmp_mingw_folder):
            print("Extracting %s..." % mingw_filepath)
            with tarfile.open(mingw_filepath) as f:
                f.extractall(download_folder)
        print("Installing mingw to %s..." % mingw_home)
        shutil.move(tmp_mingw_folder, mingw_home_path)


def congigure_mingw(mingw_home, python_home, python_version, arch, env=None):
    mingw_home_path = normalize_win_path(mingw_home, env=env)
    python_home_path = normalize_win_path(python_home, env=env)
    v_major, v_minor = tuple(int(x) for x in python_version.split('.')[:2])
    cwd_orig = os.getcwd()

    # Generate the libpythonXX.dll.a archive
    dlla_name = 'libpython%d%d.dll.a' % (v_major, v_minor)
    dlla_path = op.join(python_home_path, 'libs', dlla_name)
    if not op.exists(dlla_path):
        print('Generating %s from %s' % (dlla_name, python_home))
        dll_name = 'python%d%d.dll' % (v_major, v_minor)
        def_name = 'python%d%d.def' % (v_major, v_minor)
        try:
            os.chdir(python_home_path)
            run(['gendef', dll_name], env=env)
            run(['dlltool', '-D', dll_name, '-d', def_name, '-l', dlla_name],
                env=env)
            print("Moving %s to %s" % (dlla_name, dlla_path))
            shutil.move(dlla_name, dlla_path)
        finally:
            os.chdir(cwd_orig)

    # Use the correct MSVC runtime depending on the arch and the Python version
    if arch == '64':
        arch_folder = 'x86_64-w64-mingw32'
    elif arch == '32':
        arch_folder = 'i686-w64-mingw32'
    vc_tag = '100' if v_major == 3 else '90'
    libmsvcr = 'libmsvcr%s.a' % vc_tag
    specs = 'specs%s' % vc_tag

    # Copy the msvc runtime library
    libmsvcr_path = op.join(mingw_home_path, arch_folder, 'lib', libmsvcr)
    libs_folder = op.join(python_home_path, 'libs')
    print('Copying %s to %s' % (libmsvcr_path, libs_folder))
    shutil.copy2(libmsvcr_path, libs_folder)

    # Configure the msvc runtime specs file
    specs_folder = op.join(mingw_home_path, 'lib', 'gcc', arch_folder,
                           GCC_VERSION)
    specs_source_path = op.join(specs_folder, specs)
    specs_target_path = op.join(specs_folder, 'specs')
    print('Copying %s to %s' % (specs_source_path, specs_target_path))
    shutil.copy2(specs_source_path, specs_target_path)


def make_wine_env(python_version, python_arch, wine_prefix_root='.'):
    """Set the wineprefix environment"""
    wine_prefix_root = op.abspath(wine_prefix_root)
    if not op.exists(wine_prefix_root):
        os.makedirs(wine_prefix_root)
    env = os.environ.copy()
    if sys.platform != 'win32':
        wine_prefix = WINEPREFIX_PATTERN.format(
            version=python_version, arch=python_arch)
        env['WINEPREFIX'] = op.join(wine_prefix_root, wine_prefix)
    return env


def setup_wine_env(python_home, python_version, python_arch,
                   wine_prefix_root='wine', download_folder='download'):
    env = make_wine_env(python_version, python_arch,
                        wine_prefix_root=wine_prefix_root)
    install_python(python_home, python_version, python_arch,
                   download_folder=download_folder, env=env)
    install_mingw(mingw_home, arch=python_arch,
                  download_folder=download_folder, env=env)
    set_env(u'PATH', make_path(python_home, mingw_home), env=env)
    congigure_mingw(mingw_home, python_home, python_version, python_arch,
                    env=env)
    # Sanity check to make sure that python and gcc are in the PATH
    run(['python', '--version'], env=env)
    run(['gcc', '--version'], env=env)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        import yaml
        with open(sys.argv[1]) as f:
            config = yaml.load(f)
        wine_prefix_root = config.get('wine_prefix_root', 'wine')
        environments = config.get('environments', ())
        for environment in environments:
            python_home = environment['python_home']
            python_version = environment['python_version']
            python_arch = environment['python_arch']
            mingw_home = environment['mingw_home']

            setup_wine_env(python_home, python_version, python_arch,
                           wine_prefix_root=wine_prefix_root,
                           download_folder=wine_prefix_root)

    else:
        # Perform one setup using environment variables
        python_home = os.environ['PY_HOME']
        python_version = os.environ['PY_VERSION']
        python_arch = os.environ['ARCH']
        mingw_home = os.environ['MINGW_HOME']
        wine_prefix_root = os.environ['WINE_ROOT']
        download_folder = os.environ.get('DOWNLOAD_FOLDER', '.')

        setup_wine_env(python_home, python_version, python_arch,
                       wine_prefix_root=wine_prefix_root,
                       download_folder=download_folder)
