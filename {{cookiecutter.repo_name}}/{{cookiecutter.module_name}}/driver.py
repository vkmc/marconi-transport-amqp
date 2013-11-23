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


import marconi.openstack.common.log as logging
from marconi.queues import transport


_OPTIONS = []
_OPTIONS_GROUP = 'drivers:transport:{{ cookiecutter.module_name }}'

LOG = logging.getLogger(__name__)


class Driver(transport.DriverBase):

    def __init__(self, conf, storage):
        super(Driver, self).__init__(conf, storage)

        self._conf.register_opts(_OPTIONS, group=_OPTIONS_GROUP)
        self._transport_conf = self._conf[_OPTIONS_GROUP]

    def listen(self):
        raise NotImplementedError()
