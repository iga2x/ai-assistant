import asyncio
from assistant.analysis.parsers import parse_step_output
from assistant.analysis.facts import Fact

def test_ip_addr():
    output = """
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether cc:28:aa:86:c1:7d brd ff:ff:ff:ff:ff:ff
    inet 192.168.10.108/24 brd 192.168.10.255 scope global dynamic noprefixroute eth0
       valid_lft 68415sec preferred_lft 68415sec
"""
    facts = parse_step_output("ip addr show", output)
    print(f"IP Addr Facts: {facts}")
    assert any(f.type == "local_ip" and f.value == "192.168.10.108" for f in facts)
    assert any(f.type == "interface" and f.value == "eth0" for f in facts)

def test_ip_route():
    output = "default via 192.168.10.1 dev eth0 proto dhcp src 192.168.10.108 metric 100"
    facts = parse_step_output("ip route", output)
    print(f"IP Route Facts: {facts}")
    assert any(f.type == "gateway" and f.value == "192.168.10.1" for f in facts)

def test_ss():
    output = """
tcp   LISTEN 0      4096       127.0.0.1:11434      0.0.0.0:*    users:(("ollama",pid=916,fd=3))
"""
    facts = parse_step_output("ss -tulnp", output)
    print(f"SS Facts: {facts}")
    assert any(f.type == "listening_port" and f.value == 11434 and f.metadata["process"] == "ollama" for f in facts)

def test_nmap():
    output = """
Nmap scan report for 192.168.10.1
Host is up (0.0016s latency).
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http
"""
    facts = parse_step_output("nmap 192.168.10.1", output)
    print(f"Nmap Facts: {facts}")
    assert any(f.type == "host_discovered" and f.value == "192.168.10.1" for f in facts)
    assert any(f.type == "open_port" and f.value == 22 for f in facts)
    assert any(f.type == "open_port" and f.value == 80 for f in facts)

def test_ip_neigh():
    output = "192.168.10.1 dev eth0 lladdr 00:e0:4e:39:bf:6b REACHABLE"
    facts = parse_step_output("ip neigh", output)
    print(f"IP Neigh Facts: {facts}")
    assert any(f.type == "host_discovered" and f.value == "192.168.10.1" and f.metadata["state"] == "reachable" for f in facts)

def test_failure():
    facts = parse_step_output("ls non_existent", "", "ls: cannot access 'non_existent': No such file or directory", 2)
    print(f"Failure Facts: {facts}")
    assert any(f.type == "command_failure" and f.value == 2 for f in facts)

if __name__ == "__main__":
    test_ip_addr()
    test_ip_route()
    test_ss()
    test_nmap()
    test_ip_neigh()
    test_failure()
    print("All parser tests passed!")
