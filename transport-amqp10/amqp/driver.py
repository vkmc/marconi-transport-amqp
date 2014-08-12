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

import zaqar.openstack.common.log as logging
from zaqar.openstack.common.gettextutils import _
from zaqar.queues import transport
from zaqar.queues.transport import auth
from zaqar.queues.transport import validation
from zaqar.queues.transport.amqp import utils
from zaqar.queues.transport.amqp import messages
from zaqar.queues.transport.amqp import eventloop

_AMQP_OPTIONS = (
    cfg.StrOpt('bind',
                default='amqp://127.0.0.1',
                help='Address on which the self-hosting server will listen.'),
    cfg.IntOpt('port',
                default='8888',
                help='Port on which the self-hosting server will listen.')
)

_AMQP_GROUP = 'drivers:transport:amqp'

LOG = logging.getLogger(__name__)


class Driver(transport.DriverBase):

    def __init__(self, conf, storage, cache, control):
        super(Driver, self).__init__(conf, storage, cache, control)

        self._conf.register_opts(_AMQP_OPTIONS, group=_AMQP_GROUP)
        self._amqp_conf = self._conf[_AMQP_GROUP]
        self._validate = validation.Validator(self._conf)

        self._init_routes()

    def _init_routes(self):
        """Initialize routes to resources."""

        message_controller = self._storage.message_controller
        queue_controller = self._storage.queue_controller

        self.controllers = messages.CollectionResource(message_controller, queue_controller)

    def listen(self):
        """Self-host using 'bind' and 'port' from the AMQP config group."""

        msgtmpl = _(u'Serving on host %(bind)s:%(port)s')
        LOG.info(msgtmpl,
                 {'bind': self._amqp_conf.bind, 'port': self._amqp_conf.port})

        # I know this is ugly
        opts = self._amqp_conf.bind + ':' + str(self._amqp_conf.port)

        eventloop.run(opts, self.controllers)
