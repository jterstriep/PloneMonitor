#!/usr/bin/python3


"""
argv[1] is name of script
argv[2] location of the plone site
argv[3] (optional) - poll vs responding to request
"""

from urllib.parse import urljoin
import urllib.request
import json
import sys, subprocess, shlex

service_url = "@@get_next_job"

def main():
    arg_count = len(sys.argv)
    if arg_count < 2:
        print("Error: you need to specify location address of the plone site")
        print("Exiting script")
        return 1
    location = sys.argv[1]
    ## using hash value for testing
    ## later hash value needs to be passed in by plone site
    full_url = urljoin(location, service_url + '?hash=12345')
    try:
        response = urllib.request.urlopen(full_url)
        pretty = json.loads(response.read().decode())
        print(pretty)
        (status_ok, start_string) = parse_response(pretty)
        if status_ok:
            args = shlex.split(start_string)
            try:
                p = subprocess.Popen(args)
                p.wait()
                return 0
            except OSError:
                print('Failed while trying to run ' + start_string)

        else:
            print('Status wasn\'t OK. Exiting')
            return 1
    except URLError:
        print ('Could not connect to server')
        return 1

def parse_response(pretty):
    if not 'response' in pretty:
        print('Wrong response from server')
        return (False,'')
    response_status = pretty['response']
    if not response_status == 'OK':
        print('Response is NOTOK')
        return (False,'')
    if not 'start_string' in pretty:
        print('No start string is found')
        return (False,'')
    return (True,pretty['start_string'])

main()
