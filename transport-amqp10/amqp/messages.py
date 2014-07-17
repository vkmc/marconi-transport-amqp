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

    def on_post(self, message, project_id, queue_name):

        client_id = uuid.uuid4()
        m = utils.proton_to_marconi(message)

        if not self.queue_controller.exists(queue_name, project_id):
            self.queue_controller.create(queue_name, project_id)

        self.message_controller.post(
            queue_name,
            messages=m,
            project=project_id,
            client_uuid=client_id)