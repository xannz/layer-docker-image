#!/usr/bin/env python3
# Copyright (C) 2017  Ghent University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import sys
from time import sleep
from uuid import uuid4
import requests
import os

from charmhelpers.core import hookenv, unitdata
from charmhelpers.core.hookenv import status_set, log

from charms.reactive import when, when_not, set_state, remove_state
from charms.reactive.helpers import data_changed


@when_not('dockerhost.available')
def no_host_connected():
    # Reset so that `data_changed` will return "yes" at next relation joined.
    data_changed('image', None)
    remove_state('docker-image.ready')
    status_set(
        'blocked',
        'Please connect the application to a docker host.')


@when('dockerhost.available')
def host_connected(dh_relation):
    conf = hookenv.config()
    if conf.get('image') == "":
        status_set(
            'blocked',
            'Please provide the docker image.')
        remove_state('docker-image.ready')
        return
    if not data_changed('image', conf.get('image')):
        print("Same, skipping")
        return
    print("Different")
    remove_state('docker-image.ready')
    log('config.changed.image, generating new UUID')
    uuid = str(uuid4())
    container_request = {
        'image': conf.get('image'),
        'unit': os.environ['JUJU_UNIT_NAME'] 
    }
    log(container_request)
    username = conf.get('username')
    secret = conf.get('secret')
    if username != '' or secret != '':
        if username == '':
            status_set('blocked', 'If you provide a secret, you should also specify the username.')
            return
        if secret == '':
            status_set('blocked', 'If you provide a username, you should also set the secret.')
            return
        container_request.username = username
        container_request.secret = secret

    unitdata.kv().set('image', container_request)
    dh_relation.send_container_requests({uuid: container_request})
    status_set('waiting', 'Waiting for docker to spin up image ({}).'.format(conf.get('image')))


@when('dockerhost.available')
@when_not('docker-image.ready')
def image_running(dh_relation):
    conf = hookenv.config()
    containers = dh_relation.get_running_containers()
    if containers:
        status_set('active', 'Ready ({})'.format(conf.get('image')))
        set_state('docker-image.ready')
