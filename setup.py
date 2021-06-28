from setuptools import setup, find_packages
# from pip._internal.download import PipSession
# from pip._internal.req import parse_requirements
try:
    from pip.req import parse_requirements
except ImportError:
    from pip._internal.req import parse_requirements

# install_reqs = parse_requirements("requirements.txt", session=PipSession())
# requires = [str(ir.req) for ir in install_reqs]

install_reqs = parse_requirements("requirements.txt", session=False)
requires = None
try:
    requires = [str(ir.req) for ir in install_reqs]
except:
    requires = [str(ir.requirement) for ir in install_reqs]

setup(name='SGDBackend',
      version='0.0',
      description='SGDBackend',
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web pyramid pylons',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires,
      test_suite="sgdbackend",
      entry_points="""\
      [paste.app_factory]
      main = src:main
      """,
      )
