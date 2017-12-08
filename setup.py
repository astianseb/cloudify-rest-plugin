########
# Copyright (c) 2014 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.


from setuptools import setup

# Replace the place holders with values for your project

setup(

    # Do not use underscores in the name.
    name='cloudify-rest-plugin',

    version='0.0.1',
    author='Grzegorz Kisiel',
    author_email='grzegorz.kisiel@cloudify.co',
    description='Generic rest plugin',
    packages=['rest_plugin', 'rest_sdk'],
    license='LICENSE',
    zip_safe=False,
    install_requires=[
        "cloudify-plugins-common>=4.2",
        "PyYAML", 'requests', 'jinja2','xmltodict'
    ]
)
