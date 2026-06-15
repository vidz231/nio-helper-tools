#!/usr/bin/env python3
"""
Generate fake fixed-broadband (FBB) IPDR data files in ncore schema 15109 format.

Schema 15109 (ipdr.cib_fixed):
    user:string, client_ip:ip, client_port:uint16, server_ip:ip, server_port:uint16,
    domain:string, appid:uint32, first_seen:uint64, last_seen:uint64,
    vol_in:uint64, vol_out:uint64, pkt_in:uint64, pkt_out:uint64, ipproto:uint8

Usage:
    python3 generate_fake_fixed_ottcall.py [--output-dir DIR] [--intervals N] [--records-per-interval N] [--start-time EPOCH]

The generated files can be copied to a pocket host:
    scp ipdr_cib_fixed.log.* pocket-ath-munp1:/var/opt/nio/log/raw/
"""

import argparse
import os
import random
import time

# Common appid values for web/OTT traffic
APPS = [
    ("facebook.com", 3480),
    ("whatsapp.com", 42552),
    ("web.telegram.org", 63498),
    ("line.me", 36498),
    ("www.imo.im", 1409),
    ("viber.com", 1482),
    ("facetime.apple.com", 29442),
    ("web.wechat.com", 53498),
    ("www.youtube.com", 8804),
    ("www.netflix.com", 9498),
    ("www.google.com", 1000),
    ("www.instagram.com", 3481),
    ("tiktok.com", 62100),
    ("twitter.com", 5765),
    ("zoom.us", 61050),
]

# Fake fixed-broadband subscriber accounts (RADIUS-style user IDs)
FIXED_USERS = [
    "user001@twm.com.tw",
    "user002@twm.com.tw",
    "user003@twm.com.tw",
    "sub_10042@broadband.tw",
    "sub_10099@broadband.tw",
    "sub_20015@broadband.tw",
    "sub_20078@broadband.tw",
    "hinet_a1001@hinet.net",
    "hinet_a1002@hinet.net",
    "hinet_a1003@hinet.net",
    "fbb_30001",
    "fbb_30002",
    "fbb_30003",
    "fbb_30004",
    "fbb_30005",
    "192.168.1.101",
    "192.168.1.102",
    "192.168.1.103",
    "10.0.0.50",
    "10.0.0.51",
]

# Typical server IPs
SERVER_IPS = [
    "157.240.16.51", "157.240.25.48",
    "185.60.216.48", "185.60.216.51",
    "31.13.78.54", "31.13.85.36",
    "149.154.175.50", "149.154.167.91",
    "203.104.128.100", "203.104.128.101",
    "103.208.254.195", "185.155.136.58",
    "104.45.18.183", "104.45.19.58",
    "17.252.156.253", "17.252.156.254",
    "101.32.104.58", "101.91.18.13",
    "142.250.185.78", "172.217.14.110",
]

# Client IPs for fixed broadband (private ranges typical for FBB)
CLIENT_IP_PREFIXES = [
    "192.168.1.", "192.168.0.", "10.0.1.", "10.0.2.",
    "172.16.0.", "172.16.1.", "100.64.0.", "100.64.1.",
]

# IP protocols: 6=TCP, 17=UDP
IP_PROTOS = [6, 6, 6, 6, 17]  # weighted toward TCP


def random_client_ip():
    prefix = random.choice(CLIENT_IP_PREFIXES)
    return f"{prefix}{random.randint(2, 254)}"


def generate_record(timestamp):
    """Generate one IPDR record in schema 15109 format for fixed broadband."""
    user = random.choice(FIXED_USERS)
    client_ip = random_client_ip()
    client_port = random.randint(1024, 65000)
    server_ip = random.choice(SERVER_IPS)
    server_port = random.choice([80, 443, 443, 443, 8080, 3478, 40001])
    domain, appid = random.choice(APPS)
    ipproto = random.choice(IP_PROTOS)

    # Flow timestamps: first_seen within the interval, last_seen after
    first_seen = timestamp + random.randint(0, 60)
    duration = random.randint(1, 1200)  # 1s to 20min
    last_seen = first_seen + duration

    # Traffic volumes
    vol_in = random.randint(500, 5000000)
    vol_out = random.randint(200, 2000000)
    pkt_in = random.randint(5, 5000)
    pkt_out = random.randint(5, 3000)

    # Schema 15109 fields (after timestamp + schema_id):
    # user:string, client_ip:ip, client_port:uint16, server_ip:ip, server_port:uint16,
    # domain:string, appid:uint32, first_seen:uint64, last_seen:uint64,
    # vol_in:uint64, vol_out:uint64, pkt_in:uint64, pkt_out:uint64, ipproto:uint8
    fields = [
        str(timestamp), "15109",
        f'"{user}"', f'"{client_ip}"', str(client_port),
        f'"{server_ip}"', str(server_port),
        f'"{domain}"', str(appid),
        str(first_seen), str(last_seen),
        str(vol_in), str(vol_out),
        str(pkt_in), str(pkt_out),
        str(ipproto),
    ]

    return "[" + ",".join(fields) + "]"


def generate_file(output_dir, interval_start, num_records):
    """Generate one IPDR log file for a 30-minute interval."""
    filename = f"ipdr_cib_fixed.log.{interval_start}"
    filepath = os.path.join(output_dir, filename)

    records = []
    for _ in range(num_records):
        # Random timestamp within the 30-minute interval
        ts = interval_start + random.randint(0, 1799)
        records.append((ts, generate_record(ts)))

    # Sort by timestamp
    records.sort(key=lambda x: x[0])

    with open(filepath, 'w') as f:
        for _, record in records:
            f.write(record + "\n")

    print(f"  {filepath} ({num_records} records)")
    return filepath


def main():
    parser = argparse.ArgumentParser(
        description="Generate fake fixed-broadband IPDR data files (schema 15109)"
    )
    parser.add_argument(
        "--output-dir", default="./fake_fixed_ipdr",
        help="Output directory (default: ./fake_fixed_ipdr)"
    )
    parser.add_argument(
        "--intervals", type=int, default=4,
        help="Number of 30-min intervals to generate (default: 4 = 2 hours)"
    )
    parser.add_argument(
        "--records-per-interval", type=int, default=200,
        help="Records per interval (default: 200)"
    )
    parser.add_argument(
        "--start-time", type=int, default=None,
        help="Start epoch time (default: most recent 30-min boundary)"
    )
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.start_time is None:
        now = int(time.time())
        # Align to 30-min boundary, go back a few intervals
        args.start_time = (now // 1800) * 1800 - (args.intervals * 1800)

    print(f"Generating {args.intervals} intervals of fixed-broadband IPDR data (schema 15109):")
    print(f"  Start: {args.start_time} ({time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(args.start_time))} UTC)")
    print(f"  Records per interval: {args.records_per_interval}")
    print()

    files = []
    for i in range(args.intervals):
        interval_start = args.start_time + (i * 1800)
        f = generate_file(args.output_dir, interval_start, args.records_per_interval)
        files.append(f)

    print(f"\nDone! {len(files)} files in {args.output_dir}/")
    print(f"\nTo copy to pocket-ath-munp1:")
    print(f"  scp {args.output_dir}/ipdr_cib_fixed.log.* pocket-ath-munp1:/var/opt/nio/log/raw/")


if __name__ == "__main__":
    main()
