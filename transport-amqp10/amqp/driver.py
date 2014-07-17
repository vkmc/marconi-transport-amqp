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

import select

from proton import Message
import pyngus

from oslo.config import cfg

import marconi.openstack.common.log as logging
from marconi.openstack.common.gettextutils import _
from marconi.queues import transport
from marconi.queues.transport import auth
from marconi.queues.transport import validation
from marconi.queues.transport.amqp import utils
from marconi.queues.transport.amqp import messages
from marconi.queues.transport.amqp import eventloop

_AMQP_OPTIONS = (
    cfg.StrOpt('bind',
                default='amqp://127.0.0.1',
                help='Address on which the self-hosting server will listen.'),
    cfg.IntOpt('port',
                default='8888',
                help='Port on which the self-hosting server will listen.'),
    cfg.StrOpt('verbose',
                default=False,
                help='Print debug information'),
)

_AMQP_GROUP = 'drivers:transport:amqp'

LOG = logging.getLogger(__name__)


class Driver(transport.DriverBase):

    def __init__(self, conf, storage, cache, control):
        super(Driver, self).__init__(conf, storage, cache, control)

        self._conf.register_opts(_AMQP_OPTIONS, group=_AMQP_GROUP)
        self._transport_conf = self._conf[_AMQP_GROUP]
        self._validate = validation.Validator(self._conf)

        self._init_routes()

    def _init_routes(self):
        """Initialize routes to resources."""

        message_controller = self._storage.message_controller
        queue_controller = self._storage.queue_controller

        self.controllers = messages.CollectionResource(message_controller, queue_controller)

    def listen(self):
        """Self-host using 'bind' and 'port' from the AMQP config group."""

        # NOTE(vkmc) We will gather this information from the
        # config
        opts = "amqp://127.0.0.1:8888"

        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': 'amqp://127.0.0.1', 'port': '8888'})

        eventloop.run(opts, self.controllers)
