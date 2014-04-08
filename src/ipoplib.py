#!/usr/bin/env python

import argparse
import binascii
import getpass
import hashlib
import json
import logging
import os
import random
import select
import socket
import sys
import time

# Set default config values
CONFIG = {
    "stun": ["stun.l.google.com:19302", "stun1.l.google.com:19302",
             "stun2.l.google.com:19302", "stun3.l.google.com:19302",
             "stun4.l.google.com:19302"],
    "turn": [],  # Contains dicts with "server", "user", "pass" keys
    "ip4": "172.16.0.1",
    "localhost": "127.0.0.1",
    "ip6_prefix": "fd50:0dbc:41f2:4a3c",
    "localhost6": "::1",
    "ip4_mask": 24,
    "ip6_mask": 64,
    "subnet_mask": 32,
    "svpn_port": 5800,
    "local_uid": "",
    "uid_size": 40,
    "sec": True,
    "wait_time": 15,
    "buf_size": 4096,
    "router_mode": False,
    "on-demand_connection" : False,
    "on-demand_inactive_timeout" : 600,
    "tincan_logging": 1,
    "controller_logging" : "INFO",
    "icc" : False, # Inter-Controller Connection
    "icc_port" : 30000,
    "switchmode" : 0
}

IP_MAP = {}

ipop_ver = "\x02"
<<<<<<< HEAD
control_msg = "\x01"
traffic_msg = "\x02"
null_uid = "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
null_uid += "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
bc_mac = "\xff\xff\xff\xff\xff\xff"

def ip4_a2b(str_ip4):
    bin_ip4 = chr(int(str_ip4.split('.')[0])) + chr(int(str_ip4.split('.')[1]))\
             + chr(int(str_ip4.split('.')[2])) + chr(int(str_ip4.split('.')[3])) 
    return bin_ip4

def ip4_b2a(bin_ip4):
    return str(ord(bin_ip4[0])) + "." + str(ord(bin_ip4[1])) + "." + \
           str(ord(bin_ip4[2])) + "." + str(ord(bin_ip4[3]))
=======
tincan_control = "\x01"
tincan_packet = "\x02"
>>>>>>> upstream/master

def gen_ip4(uid, peer_map, ip4=None):
    ip4 = ip4 or CONFIG["ip4"]
    try:
        return peer_map[uid]
    except KeyError:
        pass

    ips = set(peer_map.itervalues())
    prefix, _ = ip4.rsplit(".", 1)
    # We allocate to *.101 - *.254. This ensures a 3-digit suffix and avoids
    # the broadcast address. *.100 is our IPv4 address.
    for i in range(101, 255):
        peer_map[uid] = "%s.%s" % (prefix, i)
        if peer_map[uid] not in ips:
            return peer_map[uid]
    del peer_map[uid]
    raise OverflowError("Too many peers, out of IPv4 addresses")

def gen_ip6(uid, ip6=None):
    if ip6 is None:
        ip6 = CONFIG["ip6_prefix"]
    for i in range(0, 16, 4): ip6 += ":" + uid[i:i+4]
    return ip6

def gen_uid(ip4):
    return hashlib.sha1(ip4).hexdigest()[:CONFIG["uid_size"]]

def make_call(sock, **params):
    if socket.has_ipv6: dest = (CONFIG["localhost6"], CONFIG["svpn_port"])
    else: dest = (CONFIG["localhost"], CONFIG["svpn_port"])
<<<<<<< HEAD
    return sock.sendto(ipop_ver + control_msg + json.dumps(params), dest)

def make_remote_call(sock, dest_addr, dest_port, m_type, payload, **params):
    dest = (dest_addr, dest_port)
    if m_type == control_msg:
        return sock.sendto(ipop_ver + m_type + json.dumps(params), dest)
    elif m_type == traffic_msg:
        return sock.sendto(ipop_ver + m_type + payload, dest)

def send_packet(sock, msg):
    if socket.has_ipv6: dest = (CONFIG["localhost6"], CONFIG["svpn_port"])
    else: dest = (CONFIG["localhost"], CONFIG["svpn_port"])
    return sock.sendto(ipop_ver + control_msg + msg, dest)

def make_arp(sock, op, src_ip4, target_ip4, src_uid=null_uid,dest_uid=null_uid,\
             dest_mac=bc_mac, src_mac=bc_mac):
          
    arp_msg = ""
    arp_msg += ipop_ver
    arp_msg += traffic_msg
    arp_msg += src_uid
    arp_msg += dest_uid
    arp_msg += dest_mac
    arp_msg += src_mac
    arp_msg += "\x08\x06" #Ether type of ARP
    arp_msg += "\x00\x01" #Hardware Type
    arp_msg += "\x08\x00" #Protocol Type
    arp_msg += "\x06" #Hardware address length
    arp_msg += "\x04" #Protocol address length
    arp_msg += "\x00" #Operation (ARP reply)
    arp_msg += op #Operation (ARP reply)
    arp_msg += src_mac
    arp_msg += src_ip4
    arp_msg += dest_mac
    arp_msg += target_ip4
    if socket.has_ipv6: dest = (CONFIG["localhost6"], CONFIG["svpn_port"])
    else: dest = (CONFIG["localhost"], CONFIG["svpn_port"])
    return sock.sendto(arp_msg, dest)
=======
    return sock.sendto(ipop_ver + tincan_control + json.dumps(params), dest)
>>>>>>> upstream/master

def do_send_msg(sock, method, overlay_id, uid, data):
    return make_call(sock, m=method, overlay_id=overlay_id, uid=uid, data=data)

def do_set_cb_endpoint(sock, addr):
    return make_call(sock, m="set_cb_endpoint", ip=addr[0], port=addr[1])

def do_register_service(sock, username, password, host):
    return make_call(sock, m="register_svc", username=username,
                     password=password, host=host)

def do_create_link(sock, uid, fpr, overlay_id, sec, cas, stun=None, turn=None):
    if stun is None:
        stun = random.choice(CONFIG["stun"])
    if turn is None:
        if CONFIG["turn"]:
            turn = random.choice(CONFIG["turn"])
        else:
            turn = {"server": "", "user": "", "pass": ""}
    return make_call(sock, m="create_link", uid=uid, fpr=fpr,
                     overlay_id=overlay_id, stun=stun, turn=turn["server"],
                     turn_user=turn["user"],
                     turn_pass=turn["pass"], sec=sec, cas=cas)

def do_trim_link(sock, uid):
    return make_call(sock, m="trim_link", uid=uid)

def do_set_local_ip(sock, uid, ip4, ip6, ip4_mask, ip6_mask, subnet_mask):
    return make_call(sock, m="set_local_ip", uid=uid, ip4=ip4, ip6=ip6,
                     ip4_mask=ip4_mask, ip6_mask=ip6_mask,
                     subnet_mask=subnet_mask)

def do_set_remote_ip(sock, uid, ip4, ip6):
    return make_call(sock, m="set_remote_ip", uid=uid, ip4=ip4, ip6=ip6)

def do_get_state(sock):
    return make_call(sock, m="get_state", stats=True)

def do_set_logging(sock, logging):
    return make_call(sock, m="set_logging", logging=logging)

def do_set_translation(sock, translate):
    return make_call(sock, m="set_translation", translate=translate)

def do_set_switchmode(sock, switchmode):
    return make_call(sock, m="set_switchmode", switchmode=switchmode)

class UdpServer(object):
    def __init__(self, user, password, host, ip4):
        self.state = {}
        self.peers = {}
        self.conn_stat = {}
        if socket.has_ipv6:
            self.sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        else:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 0))
        self.sock_list = [ self.sock ]

    def inter_controller_conn(self):

        self.cc_sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)

        while True:
            try:
                time.sleep(3)
                self.cc_sock.bind((gen_ip6(self.uid), CONFIG["icc_port"]))
            except Exception as e:
                logging.debug("Wait till ipop tap up")
                continue
            else:
                break

        self.sock_list.append(self.cc_sock)

    def trigger_conn_request(self, peer):
        if "fpr" not in peer and peer["xmpp_time"] < CONFIG["wait_time"] * 8:
            self.conn_stat[peer["uid"]] = "req_sent"
            do_send_msg(self.sock, "con_req", 1, peer["uid"],
                        self.state["_fpr"]);

    def check_collision(self, msg_type, uid):
        if msg_type == "con_req" and \
           self.conn_stat.get(uid, None) == "req_sent":
            if uid > self.state["_uid"]:
                do_trim_link(self.sock, uid)
                self.conn_stat.pop(uid, None)
                return False
        elif msg_type == "con_resp":
            self.conn_stat[uid] = "resp_recv"
            return False
        else:
            return True

    def arp_handle(self, data):
        if data[63] == "\x01": #ARP Request message
            in_peer = False
            target_ip4 = ip4_b2a(data[80:84])
            logging.debug("ARP request message looking for {0}, arp_table:{1}"\
                          .format(target_ip4, self.arp_table))
            for k, v in self.peers.iteritems():
                if v["status"] == "online" and v["ip4"] == dest_ip4:
                    in_peer = True
                    break

            if in_peer:
                logging.debug("{0} is associated with ipop router peers ({1} ro"
                              "uter:{2})".format(target_ip4, self.arp_table, \
                              in_peer))
                make_arp(self.sock, src_mac=data[48:54], op="\x02", 
                         src_ip4=data[80:84], target_ip4=data[70:74])
                return

            if target_ip4 in self.arp_table:
                if not self.arp_table == "local":
                    make_arp(self.sock, src_mac=data[48:54], op="\x02", 
                         src_ip4=data[80:84], target_ip4=data[70:74])
                return

            # Not found, broadcast ARP request message
            for k, v in self.peers.iteritems():
                if v["status"] == "online" and v["ip4"] == dest_ip4:
                    make_remote_call(self.cc_sock, dest_addr=dest, dest_port=\
                      CONFIG["icc_port"], m_type=control_msg, msg_type=\
                      "arp_request", target_ip4=target_ip4)

        elif data[63] == "\x02": #ARP Reply message
            logging.debug("ARP reply message")
            target_ip4 = ip4_b2a(data[80:84])
            self.arp_table["target_ip4"] = "local"
            for k, v in self.peers.iteritems():
                if v["status"] == "online" and v["ip4"] == dest_ip4:
                    make_remote_call(self.cc_sock, dest_addr=dest, dest_port=\
                       CONFIG["icc_port"], m_type=control_msg, msg_type=\
                       "arp_reply", target_ip4=target_ip4, \
                       uid=self.state["_uid"], ip6=self.state["_ip6"])

        else:
            logging.error("Unknown ARP message operation")
            sys.exit()

    def packet_handle(self, data):
        ip4 = ip4_b2a(data[72:76])
        if ip4 in self.arp_table:
            make_remote_call(self.cc_sock,dest_addr=self.arp_table[ip4]["ip6"],\
              dest_port=CONFIG["icc_port"], m_type=traffic_msg, 
              payload=data[42:])
        logging.debug("packet_handle {0} in {1}".format(ip4, self.arp_table))
         

    def icc_packet_handle(self, data):
        if data[1] == control_msg:
            if data[0] != ipop_ver:
                #TODO change it to raising exception
                logging.debug("ipop version mismatch: tincan:{0} contro\
                               ller:{1}".format(data[0], ipop_ver))
                sys.exit()
            msg = json.loads(data[2:])
            logging.debug("recv %s %s" % (addr, data[2:]))
            msg_type = msg.get("type", None)
            if msg_type == "arp_request":
                target_ip4 = msg["target_ip4"]

                if target_ip4 in self.arp_table:
                    make_remote_call(self.cc_sock, dest, CONFIG["icc_port"], \
                       control_msg, msg_type="arp_reply",target_ip4=target_ip4,\
                       uid=self.state["_uid"], ip6=self.state["_ip6"])
                    return

                make_arp(self.sock, op="\x01", \
                  src_ip4=ip4_a2b(self.state["_ip4"]),\
                  target_ip4=ip4_a2b(target_ip4))

            elif msg_type == "arp_reply":
                self.arp_table[msg["target_ip4"]] = msg
                make_arp(self.sock, op="\x02", \
                  src_ip4=ip4_a2b(self.state["_ip4"]),\
                  target_ip4=ip4_a2b(msg["target_ip4"]))


        elif data[1] == traffic_msg:
            send_packet(self.sock, data[42:])


def setup_config(config):
    """Validate config and set default value here. Return ``True`` if config is
    changed.
    """
    if not config["local_uid"]:
        uid = binascii.b2a_hex(os.urandom(CONFIG["uid_size"] / 2))
        config["local_uid"] = uid
        return True # modified
    return False

def load_peer_ip_config(ip_config):
    with open(ip_config) as f:
        ip_cfg = json.load(f)

    for peer_ip in ip_cfg:
        uid = peer_ip["uid"]
        ip = peer_ip["ipv4"]
        IP_MAP[uid] = ip
        logging.debug("MAP %s -> %s" % (ip, uid))

def parse_config():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", help="load configuration from a file",
                        dest="config_file", metavar="config_file")
    parser.add_argument("-u", help="update configuration file if needed",
                        dest="update_config", action="store_true")
    parser.add_argument("-p", help="load remote ip configuration file",
                        dest="ip_config", metavar="ip_config")

    args = parser.parse_args()

    if args.config_file:
        # Load the config file
        with open(args.config_file) as f:
            loaded_config = json.load(f)
        CONFIG.update(loaded_config)

    need_save = setup_config(CONFIG)
    if need_save and args.config_file and args.update_config:
        with open(args.config_file, "w") as f:
            json.dump(CONFIG, f, indent=4, sort_keys=True)

    if not ("xmpp_username" in CONFIG and "xmpp_host" in CONFIG):
        raise ValueError("At least 'xmpp_username' and 'xmpp_host' must be "
                         "specified in config file")

    if "xmpp_password" not in CONFIG:
        prompt = "\nPassword for %s: " % CONFIG["xmpp_username"]
        CONFIG["xmpp_password"] = getpass.getpass(prompt)

    if "controller_logging" in CONFIG:
        level = getattr(logging, CONFIG["controller_logging"])
        logging.basicConfig(level=level)

    if args.ip_config:
        load_peer_ip_config(args.ip_config)





