import config
import time
import datetime
import openvpnapi
import sys
import json
import baidussh
import threading
import uuid


class NatGatewayApi(object):
    def __init__(self):
        super(NatGatewayApi, self).__init__()
        self.expire = 0
        self.token = None
        user_name = config.username
        password = config.password
        domain_name = config.vpndomain
        config_file = config.vpnconfig
        self.vpn = openvpnapi.NewConn(user_name, password, domain_name, config_file, True)
        self.ssh = baidussh.ssh(config.host, config.port, config.user, config.passwd)
        self.nat_url = CONF.get_conf('nat_api', 'http://localhost:8055/v1')
        self.nat_url2 = CONF.get_conf('nat_api2', 'http://localhost:8055')
        self.logical_zone = CONF.get_conf('logical_zone', 'cq')

    def _getToken(self):
        """get iam token"""
        now = time.time()
        if now >= self.expire:
            self.token, self.expire = self.keystone.getToken()

        return self.token

    def _get_signature(self, url, method, headers):
        """get Authorize signature"""
        return keystone_api.Keystone.gen_signature(self.ak, self.sk,
                url, method, headers)

    def _gen_headers(self, conn, url, method):
        """get http headers"""
        headers = { 
                 "Host": conn.host,
                 "x-bce-date": datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                 "x-bce-request-id": str(uuid.uuid4()),
                 "Content-Type": "application/json"
                 }

        headers['Authorization'] = self._get_signature(conn.baseurl[:-1] + url, method, headers)
        return headers

    def _getRequestId(self):
        return uuid.uuid4()

    def _getCidr(self):
        self.cidr = '192.168.0.0/16'
        self.subnets = self.neutron.listSubnet(filters={"vpc_id": self.vpc_id})
        if self.subnets:
            self.cidr = self.subnets[0]['cidr']

    def nat_create(self, name, eips=None):
        """create nat gateway"""
        headers = {
            "Content-type": "application/json",
            "X-Auth-Token": self._getToken()
        }

        body = {
            "name": name,
            "vpc_id": self.vpc_id,
            "flavor": "little",
            "description": "NAT gateway create by test case",
            "ha_policy": "none",
            "heartbeat_interval": 30,
            "heartbeat_timeout_times": 3,
        }

        if eips:
            body['eips'] = eips

        status, resp, _ = self.http_conn.access("POST",
                           '/natgateways', body=body,
                           headers=headers)
        if status != 200 and status != 202:
            LOG.error("Create Nat gateway fail, error code %s, content %s" % (status, resp))
            return None

        return json.loads(resp)['natgateway']

    def nat_create_vpc(self, name, eips=None, type='little'):
        """create nat gateway"""
        default_vpc = self.neutron.listVpc(filters={"is_default_vpc": False})
        self.user_vpc_id = default_vpc[0].get('id', None)
        headers = {
            "Content-type": "application/json",
            "X-Auth-Token": self._getToken()
        }

        body = {
            "name": name,
            "vpc_id": self.user_vpc_id,
            "flavor": type,
            "description": "NAT gateway create by test case",
            "ha_policy": "none",
            "heartbeat_interval": 30,
            "heartbeat_timeout_times": 3,
        }

        if eips:
            body['eips'] = eips

        status, resp, _ = self.http_conn.access("POST",
                           '/natgateways', body=body,
                           headers=headers)
        if status != 200 and status != 202:
            LOG.error("Create Nat gateway fail, error code %s, content %s" % (status, resp))
            return None

        return json.loads(resp)['natgateway']

    def nat_curl(self, method, headers, body):
        """curl"""
        status, resp, _ = self.http_conn.access(method,
                           '/natgateways', body=body,
                           headers=headers)
        if status != 200 and status != 202:
            LOG.error("Create Nat gateway fail, error code %s, content %s" % (status, resp))
            return None

        return json.loads(resp).get('natgateway', None)