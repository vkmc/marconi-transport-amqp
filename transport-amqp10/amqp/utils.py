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
    """Convert a Proton Message into a storage compatible message"""
    default_ttl = 100 if message.ttl == 0 else message.ttl

    # NOTE(vkmc) For now this only parses one single message
    # it should receive a list of messages

    # NOTE(vkmc) The Proton Message body is a sequence of bytes
    # (at least, it should be in py3). We store the message with
    # garbage (string terminators used by Proton for the repr)

    # NOTE(vkmc) The extra field is not stored automagically by
    # the storage backend. The feature has been discussed for future
    # development
    return [{'ttl': default_ttl, 'body': message.body, 'amqp10': {'priority': message.priority,
                                                                  'first_acquirer': message.first_acquirer,
                                                                  'delivery_count': message.delivery_count,
                                                                  'id': message.id,
                                                                  'user_id': message.user_id,
                                                                  'address': message.address,
                                                                  'subject': message.subject,
                                                                  'reply_to': message.reply_to,
                                                                  'correlation_id': message.correlation_id,
                                                                  'content_type': message.content_type,
                                                                  'content_encoding': message.content_encoding,
                                                                  'expiry_time': message.expiry_time,
                                                                  'creation_time': message.creation_time,
                                                                  'group_id': message.group_id,
                                                                  'group_sequence': message.group_sequence,
                                                                  'reply_to_group_id': message.reply_to_group_id,
                                                                  'format': message.format}}]


def marconi_to_proton(message):
    """Convert a message retrieved from storage to a Proton message"""
    msg = Message()

    msg.ttl = message.get('ttl')
    msg.body = message.get('body')

    # NOTE(vkmc) This won't work for now - there is no 'amqp10' field yet
    if message.get('amqp10'):
        msg.priority = message.get('amqp10').get('priority')
        msg.first_acquirer = message.get('amqp10').get('first_acquirer')
        msg.delivery_count = message.get('amqp10').get('delivery_count')
        msg.id = message.get('amqp10').get('id'),
        msg.user_id = message.get('amqp10').get('user_id')
        msg.address = message.get('amqp10').get('address')
        msg.subject = message.get('amqp10').get('subject')
        msg.reply_to = message.get('amqp10').get('reply_to')
        msg.correlation_id = message.get('amqp10').get('correlation_id')
        msg.content_type = message.get('amqp10').get('content_type')
        msg.content_encoding = message.get('amqp10').get('content_encoding')
        msg.expiry_time = message.get('amqp10').get('expiry_time')
        msg.creation_time = message.get('amqp10').get('creation_time'),
        msg.group_id = message.get('amqp10').get('group_id')
        msg.group_sequence = message.get('amqp10').get('group_sequence')
        msg.reply_to_group_id = message.get('amqp10').get('reply_to_group_id')
        msg.format = message.get('amqp10').get('format')

    return msg