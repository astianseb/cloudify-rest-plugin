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
from jinja2 import Template
import requests
from . import LOGGER_NAME
from .exceptions import RecoverebleStatusCodeCodeException,\
    ExpectationException, WrongTemplateDataException

logger = logging.getLogger(LOGGER_NAME)


#  request_props (port, ssl, verify, hosts )
def process(params, template, request_props):
    logger.debug('template : {}'.format(template))
    template_yaml = yaml.load(template)
    result_propeties = {}
    for call in template_yaml['rest_calls']:
        logger.debug('call \n {}'.format(call))
        # enrich params with items stored in runtime props by prev calls
        params.update(result_propeties)
        template_engine = Template(str(call))
        rendered_call = template_engine.render(params)
        call = ast.literal_eval(rendered_call)
        logger.debug('rendered call \n {}'.format(call))

        call.update(request_props)
        response = _send_request(call)
        _process_response(response, call, result_propeties)
    return result_propeties


def _send_request(call):
    logger.debug(
        '_send_request request_props:{}'.format(call))
    port = call['port']
    ssl = call['ssl']
    if port == -1:
        port = 443 if ssl else 80
    for i, host in enumerate(call['hosts']):
        full_url = '{}://{}:{}{}'.format('https' if ssl else 'http', host,
                                         port,
                                         call['url'])
        logger.debug('full_url : {}'.format(full_url))
        try:
            response = requests.request(call['method'], full_url,
                                        headers=call.get('headers', None),
                                        data=call.get('payload', None),
                                        verify=call['verify'])
        except requests.exceptions.ConnectionError:
            logger.debug('ConnectionError for host : {}'.format(host))
            if i == len(call['hosts']) - 1:
                logger.error('No host from list available')
                raise
            else:
                continue

    logger.debug(
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


def _check_expectation(json, response_expectation):
    if not response_expectation:
        return
    if not isinstance(response_expectation, list):
        raise WrongTemplateDataException(
            "response_expectation had to be list. "
            "Type {} not supported. ".format(
                type(response_expectation)))
    if isinstance(response_expectation[0], list):
        for item in response_expectation:
            _check_expectation(json, item)
    else:
        pattern = response_expectation.pop(-1)
        for key in response_expectation:
            json = json[key]
        if not re.match(pattern, str(json)):
            raise ExpectationException(
                'Response value "{}" does not match regexp "{}" from '
                'response_expectation'.format(
                    json, pattern))


def _process_response(response, call, store_props):
    response_format = call.get('response_format', 'json')

    if response_format == 'json':
        json = response.json()
        _check_expectation(json, call.get('response_expectation', None))
        _translate_and_save(json, call.get('response_translation', None),
                            store_props)
    elif response_format == 'raw':
        logger.debug('no action for raw response_format')
    else:
        raise WrongTemplateDataException(
            "response_format {} is not supported. "
            "Only json or raw response_format is supported".format(
                response_format))


def _translate_and_save(response_json, response_translation, runtime_dict):
    if isinstance(response_translation, list):
        for idx, val in enumerate(response_translation):
            if isinstance(val, (list, dict)):
                _translate_and_save(response_json[idx], val, runtime_dict)
            else:
                _save(runtime_dict, response_translation, response_json)
    elif isinstance(response_translation, dict):
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
