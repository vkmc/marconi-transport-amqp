POC AMQP 1.0 transport driver for Marconi
=========================================

Based on the cool cookiecutter template by flaper87


Features
========

This basic implementation allows Marconi to send and receive messages with AMQP clients following the producer/consumer pattern.

How to install
==============

This driver requires Apache qpid proton to be preinstalled. It's not in pypi yet, so you will have to install it from source. To do this, please follow the directions in http://qpid.apache.org/releases/qpid-proton-0.7/.

Since this is an experimental driver, it would be advisable to deploy it in a virtualenv::

  $ virtualenv ./env
  $ source ./env/bin/activate
  $ pip install -r requirements.txt
  $ pip install -e .

How to use
==========

Configure Marconi to use AMQP

* Find [drivers] section in ``~/.marconi/marconi.conf`` and specify to use amqp transport::
transport = amqp
* Add a ``[drivers:transport:amqp]`` section and select the host configuration::
[drivers:transport:amqp]
host=amqp:127.0.0.1:8888 (default)

Run marconi-server::

  $ marconi-server -v

Use the examples provided in /examples to send and receive messages to and from the Marconi server::

  $ ./send.py -a amqp://127.0.0.1:8888 --target 'myqueue' 'message'
  $ ./recv.py -a amqp://127.0.0.1:8888 --source 'myqueue' 'message'
