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

import unittest
import requests_mock
import os

from rest_sdk import utility


class TestPlugin(unittest.TestCase):

    def test_prepare_runtime_props_path_for_list(self):
        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', ['k2'], 'k3'], 2),
            ['key1', 'k2', 2, 'k3'])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(['key1', 'k2', 'k3'],
                                                         1),
            ['key1', 'k2', 'k3', 1])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                [['key1'], 'k2', ['k3']],
                2),
            ['key1', 2, 'k2', ['k3']])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', 'k2', ['k3']], 1),
            ['key1', 'k2', 'k3', 1])

    def test_prepare_runtime_props_for_list(self):
        runtime_props = {}
        utility._prepare_runtime_props_for_list(runtime_props, ['key1', ['k2'], 'k3'], 2)
        self.assertDictEqual(runtime_props ,  {'key1': {'k2': [None, None]}})

        runtime_props = {}
        utility._prepare_runtime_props_for_list(runtime_props, ['k1', 'k2', 'k3'], 5)
        self.assertDictEqual(runtime_props, {'k1': {'k2': {'k3': [None, None, None, None, None]}}})

    def test_collect_runtime_props_paths(self):
        response_translation = {'id': [ 'id0' ],
                                'nested': { 'nested_key': [ 'nested_key0' ]
          }}
        paths = []
        utility._collect_runtime_props_paths(response_translation, paths)
        print(paths)
