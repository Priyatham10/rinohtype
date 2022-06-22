
import glob
import os
import shutil
import sys

import nox
import nox_poetry

sys.path.append('.')
from noxutil import get_versions

CURRENT_PYTHON = (('pypy' if hasattr(sys, 'pypy_version_info') else '')
                  + f'{sys.version_info.major}.{sys.version_info.minor}')

nox.options.sessions = ['check', 'check_docs',
                        f'unit-{CURRENT_PYTHON}(wheel)',
                        f'regression-{CURRENT_PYTHON}(wheel)']


PYTHONS = ['3.7', '3.8', '3.9', '3.10', '3.11']
PYTHONS += ['pypy3'] if os.getenv('CI') else ['pypy3.9']

DEPENDENCIES = ['pytest', 'pytest-xdist', 'pytest-cov', 'coverage', 'Sphinx']
if os.getenv('GITHUB_SHA'):
    DEPENDENCIES.append('pytest-github-actions-annotate-failures')


def parametrize_dist():
    return nox.parametrize('dist', ['sdist', 'wheel'], ids=['sdist', 'wheel'])


def parametrize(dependency, granularity='minor'):
    return nox.parametrize(dependency, get_versions(dependency, granularity))


# sessions

@nox_poetry.session()
def check(session):
    session.run('poetry', 'check', external=True)


@nox_poetry.session()
def check_docs(session):
    _install(session, dependencies=['doc8', 'sphinxcontrib-autoprogram'])
    session.run('doc8', 'README.rst', 'CHANGES.rst', 'CONTRIBUTING.rst',
                'DEVELOPING.rst', 'doc')
    session.run('python', 'doc/build.py', 'doctest')


@nox_poetry.session()
def build_docs(session):
    _install(session, dependencies=['sphinx', 'furo',
                                    'sphinxcontrib-autoprogram'])
    session.chdir('doc')
    session.run('python', 'build.py', *session.posargs)
    for pdf in glob.glob("_build/rinoh/*.pdf"):
        shutil.copy(pdf, "_build/html")


@nox_poetry.session(python=PYTHONS)
@parametrize_dist()
def unit(session, dist):
    _unit(session, dist=dist)


@nox_poetry.session(python='3.9')   # Sphinx >3.5 fail on 3.10
@parametrize('sphinx')
def unit_sphinx(session, sphinx):
    _unit(session, sphinx=sphinx, ignore_deprecation_warnings=True)


@nox_poetry.session(python=PYTHONS)
@parametrize_dist()
def regression(session, dist):
    _regression(session, dist=dist)


@nox_poetry.session()
@parametrize('docutils')
def regression_docutils(session, docutils):
    _regression(session, docutils=docutils, ignore_deprecation_warnings=True)


@nox_poetry.session(python='3.9')   # Sphinx >3.5 fail on 3.10
@parametrize('sphinx')
def regression_sphinx(session, sphinx):
    _regression(session, sphinx=sphinx, ignore_deprecation_warnings=True)


# utility functions

def _install(session, docutils=None, sphinx=None, dist='wheel',
             dependencies=[]):
    session.poetry.installroot(distribution_format=dist)
    if dependencies:
        session.install(*dependencies)
    if docutils:
        session.run("pip", "install", f"docutils=={docutils}")
    if sphinx:
        session.run("pip", "install", f"sphinx=={sphinx}")
        major, _ = sphinx.split('.', maxsplit=1)
        if int(major) < 4:  # https://github.com/sphinx-doc/sphinx/issues/10291
            session.run("pip", "install", "jinja2<3.1")


def _unit(session, docutils=None, sphinx=None, dist='wheel',
          ignore_deprecation_warnings=False):
    _install(session, docutils=docutils, sphinx=sphinx, dist=dist,
             dependencies=DEPENDENCIES)
    mark_expr = ['-m', 'with_sphinx'] if sphinx else []
    if dist == 'sdist':
        session.env['WITH_COVERAGE'] = '0'
    _run_tests(session, 'tests', *mark_expr,
               ignore_deprecation_warnings=ignore_deprecation_warnings)


def _regression(session, docutils=None, sphinx=None, dist='wheel',
                ignore_deprecation_warnings=False):
    _install(session, docutils=docutils, sphinx=sphinx, dist=dist,
             dependencies=[*DEPENDENCIES, 'pytest-assume',
                           'pytest-console-scripts'])
    mark_expr = ['-m', 'with_sphinx'] if sphinx else ['-m', 'not longrunning']
    if dist == 'sdist':
        session.env['WITH_COVERAGE'] = '0'
    _run_tests(session, 'tests_regression', *mark_expr,
               '--script-launch-mode=subprocess',
               ignore_deprecation_warnings=ignore_deprecation_warnings)

    
def _run_tests(session, tests_dir, *args, ignore_deprecation_warnings=False):
    filterwarnings = ['-W', ''] if ignore_deprecation_warnings else []
    session.run('python', 'run_tests.py', *args, *filterwarnings,
                *session.posargs, tests_dir)


# currently unmaintained sessions

@nox_poetry.session(python='python3.7')
def macapp(session):
    session.run('python', 'macapp.py', '--use-tox-sdist')


@nox_poetry.session(python='python3.6')
def wininst(session):
    session.env['SPHINXOPTS'] = '"-Dhtml_theme=bizstyle"'
    session.run('python', 'doc/build.py', 'rinoh', 'htmlhelp')
    session.run('python', 'wininst.py', '--use-tox-sdist')
