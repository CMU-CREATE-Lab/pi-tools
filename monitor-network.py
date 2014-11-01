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
        raise Exception('Found %d ip address candidates in ifconfig (expected 1)' % len(ips))

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

for address in addresses:
    proc = subprocess.Popen(['ping', address], 
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    all[address] = {'proc': proc, 'found': False, 'missed': 0}

while True:
    for address in addresses:
        while select.select([all[address]['proc'].stdout], [], [], 0)[0]:
            line = all[address]['proc'].stdout.readline()
            now = datetime.datetime.now().strftime('%H:%M:%S')
            if re.search('bytes from', line):
                all[address]['missed'] = 0
                if not all[address]['found']:
                    all[address]['found'] = True
                    print '%s: Found %s %s' % (now, address, hostinfo(address))
            else:
                all[address]['missed'] += 1
                if all[address]['found'] and all[address]['missed'] == 4:
                    print '%s: Lost %s' % (now, address)
                    all[address]['found'] = False
    time.sleep(0.2)
