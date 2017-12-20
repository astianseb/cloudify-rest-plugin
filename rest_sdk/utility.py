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

import yaml
import logging
import ast
import re
import xmltodict
from jinja2 import Template
import requests
from . import LOGGER_NAME
from .exceptions import RecoverebleStatusCodeCodeException, \
    ExpectationException, UnExpectationException, WrongTemplateDataException

logger = logging.getLogger(LOGGER_NAME)


#  request_props (port, ssl, verify, hosts )
def process(params, template, request_props):
    logger.debug('template : {}'.format(template))
    template_yaml = yaml.load(template)
    result_propeties = {}
    for call in template_yaml['rest_calls']:
        call_with_request_props = request_props.copy()
        logger.debug('call \n {}'.format(call))
        # enrich params with items stored in runtime props by prev calls
        params.update(result_propeties)
        template_engine = Template(str(call))
        rendered_call = template_engine.render(params)
        call = ast.literal_eval(rendered_call)
        logger.debug('rendered call \n {}'.format(call))
        call_with_request_props.update(call)
        logger.info(
            'call_with_request_props \n {}'.format(call_with_request_props))
        response = _send_request(call_with_request_props)
        _process_response(response, call, result_propeties)
    return result_propeties


def _send_request(call):
    logger.info(
        '_send_request request_props:{}'.format(call))
    port = call['port']
    ssl = call['ssl']
    if port == -1:
        port = 443 if ssl else 80
    for i, host in enumerate(call['hosts']):
        full_url = '{}://{}:{}{}'.format('https' if ssl else 'http', host,
                                         port,
                                         call['path'])
        logger.debug('full_url : {}'.format(full_url))
        # check if payload can be used as json
        if call.get('payload_format', 'json') == 'json':
            data = None
            json_payload = call.get('payload', None)
        else:
            data = call.get('payload', None)
            json_payload = None

        try:
            response = requests.request(call['method'], full_url,
                                        headers=call.get('headers', None),
                                        data=data,
                                        json=json_payload,
                                        verify=call['verify'])
        except requests.exceptions.ConnectionError:
            logger.debug('ConnectionError for host : {}'.format(host))
            if i == len(call['hosts']) - 1:
                logger.error('No host from list available')
                raise
            else:
                continue

    logger.info(
        'response \n text:{}\n status_code:{}\n'.format(response.text,
                                                        response.status_code))
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code in call.get('recoverable_codes', []):
            raise RecoverebleStatusCodeCodeException(
                'Response code {} defined as recoverable'.format(
                    response.status_code))
        raise
    return response


def _process_response(response, call, store_props):
    logger.debug(
        '_process_response \n response:{}\n call:{}\n store_props:{}'.format(
            response,
            call, store_props))
    response_format = call.get('response_format', 'json').upper()

    if re.match('JSON|XML', response_format):
        if response_format == 'JSON':
            logger.debug('response_format json')
            json = response.json()
        else:  # XML
            logger.debug('response_format xml')
            json = xmltodict.parse(response.text)
            logger.debug('xml transformed to dict \n{}'.format(json))
        _check_expectation(json, call.get('response_expectation', None))
        _check_expectation(json, call.get('response_unexpectation', None),
                           True)
        _translate_and_save(json, call.get('response_translation', None),
                            store_props)
    elif response_format == 'RAW':
        logger.debug('no action for raw response_format')
    else:
        raise WrongTemplateDataException(
            "response_format {} is not supported. "
            "Only json or raw response_format is supported".format(
                response_format))


def _check_expectation(json, expectation, unexpectation=False):
    logger.debug(
        '_check_expectation \n json:{}\n '
        'expectation:{}\n '
        'unexpectation:{}'.format(
            json, expectation, unexpectation))
    if not expectation:
        return
    if not isinstance(expectation, list):
        raise WrongTemplateDataException(
            "response_expectation had to be list. "
            "Type {} not supported. ".format(
                type(expectation)))
    if isinstance(expectation[0], list):
        for item in expectation:
            _check_expectation(json, item, unexpectation)
    else:
        pattern = expectation.pop(-1)
        for key in expectation:
            try:
                json = json[key]
            except (IndexError, KeyError):
                if not unexpectation:
                    raise ExpectationException(
                        'No key or index {} in json {}'.format(key, json))
        if unexpectation:
            if re.match(pattern, str(json)):
                raise UnExpectationException(
                    'Response value "{}" matches regexp "{}" from '
                    'response_unexpectation'.format(
                        json, pattern))
        else:
            if not re.match(pattern, str(json)):
                raise ExpectationException(
                    'Response value "{}" does not match regexp "{}" from '
                    'response_expectation'.format(
                        json, pattern))


def _translate_and_save(response_json, response_translation, runtime_dict):
    if isinstance(response_translation, list):
        for idx, val in enumerate(response_translation):
            if isinstance(val, (list, dict)):
                _translate_and_save(response_json[idx], val, runtime_dict)
            else:
                _save(runtime_dict, response_translation, response_json)
    elif isinstance(response_translation, dict):
        if isinstance(response_json, list):
            list_of_paths = []
            _collect_runtime_props_paths(response_translation, list_of_paths)
            for path in list_of_paths:
                _prepare_runtime_props_for_list(runtime_dict,path,len(response_json)-1)
                for l_idx, value in enumerate(response_json):
                    _prepare_runtime_props_path_for_list()
        else:
            for key, value in response_translation.items():
                _translate_and_save(response_json[key], value, runtime_dict)


def _save(runtime_properties_dict_or_subdict, list, value):
    first_el = list.pop(0)
    if len(list) == 0:
        runtime_properties_dict_or_subdict[first_el] = value
    else:
        runtime_properties_dict_or_subdict[
            first_el] = runtime_properties_dict_or_subdict.get(first_el, {})
        _save(runtime_properties_dict_or_subdict[first_el], list, value)

def _collect_runtime_props_paths(response_translation, paths):
    if isinstance(response_translation, list):
        for idx, val in enumerate(response_translation):
            if isinstance(val, (list, dict)):
                _collect_runtime_props_paths( val, paths)
            else:
                paths.append( response_translation)
    else:
        for key, value in response_translation.items():
            _collect_runtime_props_paths(value, paths)

def _prepare_runtime_props_path_for_list(runtime_props_path, idx):
    path = list(runtime_props_path)
    for l_idx, value in enumerate(path):
        if isinstance(value,list):
            path[l_idx]=value.pop()
            break
    path.insert(l_idx+1,idx)
    return path

def _prepare_runtime_props_for_list(runtime_props, runtime_props_path , count):
    for l_idx, value in enumerate(runtime_props_path):
        if isinstance(value,list):
            runtime_props[value.pop()] = [None]
            return
        else:
            runtime_props[value] = runtime_props.get(value,{})
            if value == runtime_props_path[-1]:
                runtime_props[value] = [None] * count
            else:
                runtime_props = runtime_props[value]

