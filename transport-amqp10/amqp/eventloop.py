# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
"""A simple server that consumes and produces messages."""

import select
import time
import utils
from proton import Message
import pyngus

import zaqar.openstack.common.log as logging

LOG = logging.getLogger(__name__)


class SocketConnection(pyngus.ConnectionEventHandler):
    """Associates a pyngus Connection with a python network socket"""

    def __init__(self, container, socket_, name, properties, controllers):
        """Create a Connection using socket_."""
        self.socket = socket_
        self.connection = container.create_connection(name,
                                                      self,  # handler
                                                      properties)
        self.connection.user_context = self
        self.connection.pn_sasl.mechanisms("ANONYMOUS")
        self.connection.pn_sasl.server()
        self.connection.open()
        self.closed = False

        self.sender_links = set()
        self.receiver_links = set()

        self.controllers = controllers

    def destroy(self):
        self.closed = True
        for link in self.sender_links.copy():
            link.destroy()
        for link in self.receiver_links.copy():
            link.destroy()
        if self.connection:
            self.connection.destroy()
            self.connection = None
        if self.socket:
            self.socket.close()
            self.socket = None

    def fileno(self):
        """Allows use of a SocketConnection in a select() call."""
        return self.socket.fileno()

    def process_input(self):
        """Called when socket is read-ready"""
        try:
            pyngus.read_socket_input(self.connection, self.socket)
        except Exception as e:
            LOG.error("Exception on socket read: %s", str(e))
            # may be redundant if closed cleanly:
            self.connection_closed(self.connection)
            return
        self.connection.process(time.time())

    def send_output(self):
        """Called when socket is write-ready"""
        try:
            pyngus.write_socket_output(self.connection,
                                       self.socket)
        except Exception as e:
            LOG.error("Exception on socket write: %s", str(e))
            # may be redundant if closed cleanly:
            self.connection_closed(self.connection)
            return
        self.connection.process(time.time())

    # ConnectionEventHandler callbacks:

    def connection_remote_closed(self, connection, reason):
        LOG.debug("Connection remote closed")
        # The remote has closed its end of the Connection.  Close my end to
        # complete the close of the Connection:
        self.connection.close()

    def connection_closed(self, connection):
        LOG.debug("Connection closed")
        # main loop will destroy
        self.closed = True

    def connection_failed(self, connection, error):
        LOG.error("Connection failed! error = %s", str(error))
        # No special recovery - just close it:
        self.connection.close()

    def sender_requested(self, connection, link_handle,
                         name, requested_source, properties):
        LOG.debug("Connection sender requested")
        if requested_source is None:
            # the peer has requested us to create a source node.
            # select general queue
            requested_source = 'uncategorized'
        sender = SenderLink(self, link_handle, requested_source, self.controllers)
        self.sender_links.add(sender)

    def receiver_requested(self, connection, link_handle,
                           name, requested_target, properties):
        LOG.debug("Receiver requested callback")
        if requested_target is None:
            # the peer has requested us to create a target node.
            # select general queue
            requested_target = 'uncategorized'
        receiver = ReceiverLink(self, link_handle, requested_target, self.controllers)
        self.receiver_links.add(receiver)

    # SASL callbacks:

    def sasl_step(self, connection, pn_sasl):
        LOG.debug("SASL step callback")
        # Unconditionally accept the client:
        pn_sasl.done(pn_sasl.OK)

    def sasl_done(self, connection, pn_sasl, result):
        LOG.debug("SASL done callback, result = %s", str(result))


class SenderLink(pyngus.SenderEventHandler):
    """Send messages until credit runs out."""
    def __init__(self, socket_conn, handle, src_addr, controllers):
        self.socket_conn = socket_conn
        sl = socket_conn.connection.accept_sender(handle,
                                                  source_override=src_addr,
                                                  event_handler=self)
        self.sender_link = sl
        self.sender_link.open()
        print("New sender link created, name = %s" % sl.name)

        self.controllers = controllers

    def destroy(self):
        print("Sender link destroyed, name = %s" % self.sender_link.name)
        self.socket_conn.sender_links.discard(self)
        self.socket_conn = None
        self.sender_link.destroy()
        self.sender_link = None

    def send_message(self):
        queue = self.sender_link.source_address
        LOG.debug("Sender: Sending messages...")
        message = self.controllers.on_get(queue)

        # if there was a message in the queue
        # destroy the message once consumed
        # else return an empty message
        if message:
            self.controllers.on_delete(queue)
        else:
            message.append(Message())

        # NOTE(vkmc) We return the first message on the list
        # but the idea is to return every message in the queue
        self.sender_link.send(message[0], self)

    # SenderEventHandler callbacks:

    def sender_active(self, sender_link):
        LOG.debug("Sender: Active")
        if sender_link.credit > 0:
            self.send_message()

    def sender_remote_closed(self, sender_link, error):
        LOG.debug("Sender: Remote closed")
        self.sender_link.close()

    def sender_closed(self, sender_link):
        LOG.debug("Sender: Closed")
        # Done with this sender:
        self.destroy()

    def credit_granted(self, sender_link):
        LOG.debug("Sender: Credit granted")
        # Send a single message:
        if sender_link.credit > 0:
            self.send_message()

    # 'message sent' callback:
    def __call__(self, sender, handle, status, error=None):
        print("Message sent on sender link %s, status = %s" %
              (self.sender_link.name, status))
        if self.sender_link.credit > 0:
            # send another message:
            self.send_message()


class ReceiverLink(pyngus.ReceiverEventHandler):
    """Receive messages, and drop them."""
    def __init__(self, socket_conn, handle, rx_addr, controllers):
        self.socket_conn = socket_conn
        rl = socket_conn.connection.accept_receiver(handle,
                                                    target_override=rx_addr,
                                                    event_handler=self)
        self.receiver_link = rl
        self.receiver_link.open()
        self.receiver_link.add_capacity(1)

        print("New receiver link created, name = %s" % rl.name)

        self.controllers = controllers

    def destroy(self):
        print("Receiver link destroyed, name = %s" % self.receiver_link.name)
        self.socket_conn.receiver_links.discard(self)
        self.socket_conn = None
        self.receiver_link.destroy()
        self.receiver_link = None

    # ReceiverEventHandler callbacks:

    def receiver_active(self, receiver_link):
        LOG.debug("Receiver: Active")

    def receiver_remote_closed(self, receiver_link, error):
        LOG.debug("Receiver: Remote closed")
        self.receiver_link.close()

    def receiver_closed(self, receiver_link):
        LOG.debug("Receiver: Closed")
        # Done with this Receiver:
        self.destroy()

    def message_received(self, receiver_link, message, handle):
        self.receiver_link.message_accepted(handle)
        print("Message received on receiver link %s, message = %s"
              % (self.receiver_link.name, str(message)))
        if receiver_link.capacity < 1:
            receiver_link.add_capacity(1)
        queue = receiver_link.target_address
        self.controllers.on_post(message, queue)


def run(opts, controllers):

    # Create a socket for inbound connections
    # For now the address is the only opt
    host, port = utils.get_host_port(opts)
    s = utils.server_socket(host, port)

    # Create an AMQP container that will provide the server service
    container = pyngus.Container("Marconi")
    socket_connections = set()

    # Main loop: process I/O and timer events
    while True:
        readers, writers, timers = container.need_processing()

        # Map pyngus Connections back to my SocketConnections:
        readfd = [c.user_context for c in readers]
        writefd = [c.user_context for c in writers]

        timeout = None
        if timers:
            deadline = timers[0].next_tick  # [0] == next expiring timer
            now = time.time()
            timeout = 0 if deadline <= now else deadline - now

        LOG.debug("select() start (t=%s)", str(timeout))
        readfd.append(s)
        readable, writable, ignore = select.select(readfd, writefd,
                                                   [], timeout)
        LOG.debug("select() returned")

        worked = set()
        for r in readable:
            if r is s:
                # new inbound connection request received
                # create a new SocketConnection for it:
                client_socket, client_address = s.accept()
                name = str(client_address)
                conn_properties = {}
                sconn = SocketConnection(container,
                                         client_socket,
                                         name,
                                         conn_properties,
                                         controllers)
                socket_connections.add(sconn)
                LOG.debug("new connection created name=%s", name)

            else:
                assert isinstance(r, SocketConnection)
                r.process_input()
                worked.add(r)

        for t in timers:
            now = time.time()
            if t.next_tick > now:
                break
            t.process(now)
            sc = t.user_context
            assert isinstance(sc, SocketConnection)
            worked.add(sc)

        for w in writable:
            assert isinstance(w, SocketConnection)
            w.send_output()
            worked.add(w)

        # nuke any completed connections:
        closed = False
        while worked:
            sc = worked.pop()
            if sc.closed:
                socket_connections.discard(sc)
                sc.destroy()
                closed = True
        if closed:
            LOG.debug("%d active connections present", len(socket_connections))

    return 0
