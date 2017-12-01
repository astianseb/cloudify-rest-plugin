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

import traceback
from cloudify import ctx
from cloudify.exceptions import NonRecoverableError, RecoverableError
from rest_sdk import utility, exceptions


def execute(params, template_file, **kwargs):
    ctx.logger.debug(
        'execute \n params {} \n template \n'.format(params, template_file))
    if not template_file:
        ctx.logger.debug(
            'Processing finished. No template file provide to method')
        return
    if not params:
        params = {}
    template = ctx.get_resource(template_file)
    params.update(ctx.instance.runtime_properties)
    try:
        ctx.instance.runtime_properties.update(
            utility.process(params, template, ctx.node.properties.copy()))
    except (exceptions.ExpectationException,
            exceptions.RecoverebleStatusCodeCodeException)as e:
        raise RecoverableError(e)
    except Exception as e:
        ctx.logger.info(
            'Exception traceback : {}'.format(traceback.format_exc()))
        raise NonRecoverableError(e)
