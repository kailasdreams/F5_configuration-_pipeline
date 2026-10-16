#!/usr/bin/env python3
# Starter deployer for F5 BIG-IP LTM objects via REST API.
import argparse
import ipaddress
import os
import sys
from urllib.parse import quote
import requests
import yaml

class BigIP:
    def __init__(self, host, username, password, verify_tls=True):
        self.base = f"https://{host}".rstrip("/")
        self.session = requests.Session()
        self.session.verify = verify_tls
        self.session.headers.update({"Content-Type": "application/json"})
        response = self.session.post(
            self.base + "/mgmt/shared/authn/login",
            json={"username": username, "password": password, "loginProviderName": "tmos"},
            timeout=30,
        )
        response.raise_for_status()
        token = response.json().get("token", {}).get("token")
        if not token:
            raise RuntimeError("BIG-IP login succeeded but no auth token was returned.")
        self.session.headers.update({"X-F5-Auth-Token": token})

    @staticmethod
    def obj_path(kind, name):
        return f"/mgmt/tm/ltm/{kind}/~Common~{quote(name, safe='')}"

    def upsert(self, kind, name, payload):
        path = self.obj_path(kind, name)
        check = self.session.get(self.base + path, timeout=30)
        if check.status_code == 200:
            response, action = self.session.put(self.base + path, json=payload, timeout=30), "updated"
        elif check.status_code == 404:
            response, action = self.session.post(
                self.base + f"/mgmt/tm/ltm/{kind}", json=payload, timeout=30
            ), "created"
        else:
            check.raise_for_status()
            raise RuntimeError(f"Unexpected GET status for {kind}/{name}: {check.status_code}")
        response.raise_for_status()
        print(f"{action}: {kind}/{name}")

    def upsert_member(self, pool_name, node_name, port):
        path = (f"/mgmt/tm/ltm/pool/~Common~{quote(pool_name, safe='')}/members/"
                f"~Common~{quote(node_name, safe='')}:{port}")
        check = self.session.get(self.base + path, timeout=30)
        if check.status_code == 200:
            response, action = self.session.put(
                self.base + path, json={"name": f"/Common/{node_name}:{port}"}, timeout=30
            ), "updated"
        elif check.status_code == 404:
            collection = f"/mgmt/tm/ltm/pool/~Common~{quote(pool_name, safe='')}/members"
            response, action = self.session.post(
                self.base + collection, json={"name": f"/Common/{node_name}:{port}"}, timeout=30
            ), "created"
        else:
            check.raise_for_status()
            raise RuntimeError(f"Unexpected GET status for member {pool_name}/{node_name}:{port}")
        response.raise_for_status()
        print(f"{action}: pool-member/{pool_name}/{node_name}:{port}")

    def deploy(self, cfg):
        for node in cfg.get("nodes", []):
            ipaddress.ip_address(node["address"])
            self.upsert("node", node["name"], {
                "name": f"/Common/{node['name']}", "address": node["address"]
            })
        for pool in cfg.get("pools", []):
            payload = {
                "name": f"/Common/{pool['name']}",
                "loadBalancingMode": pool.get("load_balancing_mode", "round-robin"),
            }
            if pool.get("monitor"):
                payload["monitor"] = pool["monitor"]
            self.upsert("pool", pool["name"], payload)
            for member in pool.get("members", []):
                self.upsert_member(pool["name"], member["node"], member["port"])
        for vip in cfg.get("virtual_servers", []):
            address = str(ipaddress.ip_address(vip["destination_address"]))
            port = vip["destination_port"]
            payload = {
                "name": f"/Common/{vip['name']}",
                "destination": f"/Common/{address}:{port}",
                "ipProtocol": vip.get("protocol", "tcp").lower(),
                "sourceAddressTranslation": {"type": "automap"} if vip.get("snat_automap") else {"type": "none"},
            }
            if vip.get("pool"):
                payload["pool"] = f"/Common/{vip['pool']}"
            if vip.get("profiles"):
                payload["profiles"] = [{"name": p, "context": "all"} for p in vip["profiles"]]
            self.upsert("virtual", vip["name"], payload)

def main():
    parser = argparse.ArgumentParser(description="Deploy F5 LTM config from YAML.")
    parser.add_argument("--config", default="config/f5-config.yaml")
    args = parser.parse_args()
    host, username, password = (os.getenv(k, "").strip() for k in ("F5_HOST", "F5_USERNAME", "F5_PASSWORD"))
    if not all((host, username, password)):
        print("Set F5_HOST, F5_USERNAME, and F5_PASSWORD environment variables.", file=sys.stderr)
        return 2
    verify_tls = os.getenv("F5_VERIFY_TLS", "true").lower() not in ("false", "0", "no")
    try:
        with open(args.config, "r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
        for node in cfg.get("nodes", []):
            ipaddress.ip_address(node["address"])
        for vip in cfg.get("virtual_servers", []):
            ipaddress.ip_address(vip["destination_address"])
        client = BigIP(host, username, password, verify_tls=verify_tls)
        client.deploy(cfg)
    except Exception as exc:
        print(f"Deployment failed: {exc}", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
