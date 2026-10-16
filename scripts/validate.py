#!/usr/bin/env python3
import argparse
import sys
import yaml

def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)

def main():
    parser = argparse.ArgumentParser(description="Validate F5 LTM YAML configuration.")
    parser.add_argument("--config", default="config/f5-config.yaml")
    args = parser.parse_args()
    try:
        with open(args.config, "r", encoding="utf-8") as handle:
            cfg = yaml.safe_load(handle) or {}
    except (OSError, yaml.YAMLError) as exc:
        fail(f"Cannot read YAML: {exc}")
    if not isinstance(cfg, dict):
        fail("Top-level YAML must be a mapping.")
    nodes, pools, vips = cfg.get("nodes", []), cfg.get("pools", []), cfg.get("virtual_servers", [])
    for key, value in (("nodes", nodes), ("pools", pools), ("virtual_servers", vips)):
        if not isinstance(value, list):
            fail(f"'{key}' must be a list.")
    node_names = set()
    for node in nodes:
        if not isinstance(node, dict) or not node.get("name") or not node.get("address"):
            fail("Each node needs 'name' and 'address'.")
        if node["name"] in node_names:
            fail(f"Duplicate node name: {node['name']}")
        node_names.add(node["name"])
    pool_names = set()
    for pool in pools:
        if not isinstance(pool, dict) or not pool.get("name"):
            fail("Each pool needs a 'name'.")
        if pool["name"] in pool_names:
            fail(f"Duplicate pool name: {pool['name']}")
        pool_names.add(pool["name"])
        if not isinstance(pool.get("members", []), list):
            fail(f"Pool '{pool['name']}' members must be a list.")
        for member in pool.get("members", []):
            if member.get("node") not in node_names:
                fail(f"Pool '{pool['name']}' references unknown node '{member.get('node')}'.")
            if not isinstance(member.get("port"), int) or not 1 <= member["port"] <= 65535:
                fail(f"Pool '{pool['name']}' has an invalid member port.")
    vip_names = set()
    for vip in vips:
        if not isinstance(vip, dict) or not vip.get("name"):
            fail("Each virtual server needs a 'name'.")
        if vip["name"] in vip_names:
            fail(f"Duplicate virtual server name: {vip['name']}")
        vip_names.add(vip["name"])
        if vip.get("pool") and vip["pool"] not in pool_names:
            fail(f"Virtual server '{vip['name']}' references unknown pool '{vip.get('pool')}'.")
        if not isinstance(vip.get("destination_port"), int) or not 1 <= vip["destination_port"] <= 65535:
            fail(f"Virtual server '{vip['name']}' has an invalid destination_port.")
        if vip.get("protocol", "tcp").lower() not in ("tcp", "udp"):
            fail(f"Virtual server '{vip['name']}' protocol must be tcp or udp.")
    print(f"Validation passed: {len(nodes)} node(s), {len(pools)} pool(s), {len(vips)} virtual server(s).")

if __name__ == "__main__":
    main()
