# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid

import marconi.openstack.common.log as logging
from marconi.queues.transport.amqp import utils

LOG = logging.getLogger(__name__)


class CollectionResource(object):

    __slots__ = ('message_controller', 'queue_controller')

    def __init__(self, message_controller, queue_controller):
        self.message_controller = message_controller
        self.queue_controller = queue_controller

    def on_post(self, message, queue_name):

        client_id = uuid.uuid4()
        marconi_message = utils.proton_to_marconi(message)

        # NOTE(vkmc): This control has to be removed since exists()
        # is deprecated
        if not self.queue_controller.exists(queue_name):
            self.queue_controller.create(queue_name)

        self.message_controller.post(
            queue_name,
            messages=marconi_message,
            client_uuid=client_id)

    def on_get(self, queue_name):

        try:
            results = self.message_controller.list(queue_name)

            # Buffer messages
            cursor = next(results)
            messages = list(cursor)
        except Exception as ex:
            LOG.exception(ex)

        if not messages:
            proton_messages = []
        else:
            # Found some messages, so convert them to Proton Messages
            proton_messages = []
            for each_message in messages:
                msg = utils.marconi_to_proton(each_message)
                proton_messages.append(msg)

        return proton_messages

    def on_delete(self, queue_name):

        # NOTE(vkmc) Cannot keep the message id
        # I directly remove the queue
        try:
            self.queue_controller.delete(queue_name)
        except Exception as ex:
            LOG.exception(ex)