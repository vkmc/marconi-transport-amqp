# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

from proton import Message

import errno
import re
import socket

import marconi.openstack.common.log as logging

LOG = logging.getLogger(__name__)


def get_host_port(server_address):
    """Parse the hostname and port out of the server_address."""
    regex = re.compile(r"^amqp://([a-zA-Z0-9.]+)(:([\d]+))?$")
    x = regex.match(server_address)
    if not x:
        raise Exception("Bad address syntax: %s" % server_address)
    matches = x.groups()
    host = matches[0]
    port = int(matches[2]) if matches[2] else None
    return host, port

def server_socket(host, port, backlog=10):
    """Create a TCP listening socket for a server."""
    addr = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    if not addr:
        raise Exception("Could not translate address '%s:%s'"
                        % (host, str(port)))
    s = socket.socket(addr[0][0], addr[0][1], addr[0][2])
    s.setblocking(0)  # 0 = non-blocking
    try:
        s.bind(addr[0][4])
        s.listen(backlog)
    except socket.error, e:
        if e[0] != errno.EINPROGRESS:
            raise
    return s


def proton_to_marconi(message):
    return [{'ttl': message.ttl, 'body': message.body}]