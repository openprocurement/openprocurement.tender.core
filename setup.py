from setuptools import setup, find_packages
import os

version = '2.3'

requires = [
    'setuptools',
    'openprocurement.api>=2.3',  # TODO XXX 2.3.x version
]
test_requires = requires + [
    'webtest',
    'python-coveralls',
]
docs_requires = requires + [
    'sphinxcontrib-httpdomain',
]

entry_points = {
    'openprocurement.api.plugins': [
        'tender_core = openprocurement.tender.core.includeme:includeme'
    ],
    'nose.plugins.0.10': [
        'todo = openprocurement.tender.core.tests.nose_todo_plugin:TodoWarningPlugin'
    ],
    # 'openprocurement.tender.core.migrations': [
        # 'contracts = openprocurement.tender.core.migration:migrate_data'
    # ]
}

setup(name='openprocurement.tender.core',
      version=version,
      description="",
      long_description=open("README.txt").read(),
      # Get more strings from
      # http://pypi.python.org/pypi?:action=list_classifiers
      classifiers=[
          "License :: OSI Approved :: Apache Software License",
          "Programming Language :: Python",
      ],
      keywords='',
      author='Quintagroup, Ltd.',
      author_email='info@quintagroup.com',
      url='https://github.com/openprocurement/openprocurement.tender.core',
      license='Apache License 2.0',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['openprocurement', 'openprocurement.tender'],
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=test_requires,
      extras_require={'test': test_requires, 'docs': docs_requires},
      test_suite="openprocurement.tender.core.tests.main.suite",
      entry_points=entry_points
      )
