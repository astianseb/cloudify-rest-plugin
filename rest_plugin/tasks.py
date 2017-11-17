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
from cloudify import ctx
from jinja2 import Template
import requests
from cloudify.exceptions import NonRecoverableError


def execute(params, template_file, **kwargs):
    ctx.logger.debug('execute \n params : {} \n template_file : {} \n'.format(params, template_file))
    if not template_file:
        return
    template = ctx.get_resource(template_file)
    template_engine = Template(template)
    rendered_template = template_engine.render(params)
    object = yaml.load(rendered_template)
    for call in object['rest_calls']:
        ctx.logger.debug('call \n {}'.format(call))
        response = _send_request(call['url'], call['method'], call.get('headers', None), call.get('payload', None))
        _process_response(response, call.get('response_translation', None), call.get('response_format', None))


def _send_request(url, method, headers, payload):
    ctx.logger.debug('_send_request \n   payload:{}\n url = {}'.format(payload, url))
    port = ctx.node.properties['port']
    ssl = ctx.node.properties['ssl']
    if port == -1:
        port = 443 if ssl else 80
    for i, host in enumerate(ctx.node.properties['hosts']):
        ctx.logger.info('i {}  host {}'.format(i,host))
        full_url = '{}://{}:{}{}'.format('https' if ssl else 'http', host, port, url)
        ctx.logger.debug('full_url'.format(full_url))
        try:
            response = requests.request(method, full_url, headers=headers, data=payload, verify=ctx.node.properties['verify'])
        except requests.exceptions.ConnectionError:
            ctx.logger.debug('ConnectionError for host : {}'.format(host))
            if i == len(ctx.node.properties['hosts']) - 1:
                raise NonRecoverableError("No host from list available")
            else:
                continue

    ctx.logger.debug('response \n text:{}\n status_code:{}\n'.format(response.text, response.status_code))
    response.raise_for_status()

    return response


def _process_response(response, response_translation, response_format):
    if response_format == 'json' and response_translation != None:
        json = response.json()
        _translate_and_save(json, response_translation, ctx.instance.runtime_properties)
    elif response_format == 'raw':
        ctx.logger.debug('no action for raw response_format')
    else:
        raise NonRecoverableError(
            "response_format {} is not supported. Only json or raw response_format is supported".format(
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
        runtime_properties_dict_or_subdict[first_el] = runtime_properties_dict_or_subdict.get(first_el, {})
        _save(runtime_properties_dict_or_subdict[first_el], list, value)
