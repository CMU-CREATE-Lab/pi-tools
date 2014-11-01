#!/usr/bin/python

import datetime, json, re, resource, select, subprocess, time, urllib2

file_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
resource.setrlimit(resource.RLIMIT_NOFILE, (1024, file_limit[1]))

def find_my_ip():
    ips = [m.groups()[0] for m in re.finditer(r'inet (\d+.\d+.\d+.\d+)', subprocess.check_output(['ifconfig']))]
    ips = list((set(ips) - set(['127.0.0.1'])))
    if len(ips) == 1:
        return ips[0]
    else:
        raise Exception('Trying to discover my IP address with ifconfig, but found %d ip address candidates (expected 1)' % len(ips))

def hostinfo(address):
    try:
        arp = subprocess.check_output(['arp', address])
    except subprocess.CalledProcessError:
        return None
    match = re.search(r'(\w\w?:\w\w?:\w\w?:\w\w?:\w\w?:\w\w?)', arp)
    if not match:
        return None
    mac = match.groups()[0]
    mac = ':'.join(['%02X' % int(x, 16) for x in mac.split(':')])
    try:
        company = json.loads(urllib2.urlopen('http://www.macvendorlookup.com/api/v2/%s' % mac).read())[0]['company']
        return '%s (%s)' % (mac, company)
    except:
        return mac

# TODO(rsargent):  cope with non /24 networks

my_ip = find_my_ip()

addresses = []
for i in range(1, 255):
    address = '.'.join(find_my_ip().split('.')[0:3] + [str(i)])
    if address != my_ip:
        addresses.append(address)

all = {}

# After 5 seconds of no ping returns, consider device lost
timeout = 5

for address in addresses:
    proc = subprocess.Popen(['ping', address], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all[address] = {'proc': proc, 'found': False, 'missed': 0}

while True:
    for address in addresses:
        for inp in [all[address]['proc'].stdout, all[address]['proc'].stderr]:
            while select.select([inp], [], [], 0)[0]:
                line = inp.readline()
                now = datetime.datetime.now().strftime('%H:%M:%S')
                if re.search('bytes from', line):
                    if not all[address]['found']:
                        print '%s: Found %s %s' % (now, address, hostinfo(address))
                    all[address]['found'] = time.time()
        if all[address]['found'] and (time.time() - all[address]['found']) > timeout:
            all[address]['found'] = False
            print '%s: Lost %s' % (now, address)
    time.sleep(0.2)
