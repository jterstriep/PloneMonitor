#!/usr/bin/python2


"""
argv[0] is name of script
argv[1] location of the plone site
argv[2] username
argv[3] password
"""

from urlparse import urljoin
from sys import argv
import urllib2, base64
import subprocess, shlex, logging, time, json

service_url = "@@get_next_job"
server_poll_delay = 3.0 # seconds

# enable logging
logging.basicConfig(level=logging.DEBUG)

def main():
    arg_count = len(argv)
    if arg_count < 4:
        print 'Usage: python', argv[0], 'site_url username password'
        print "Exiting script"
        return 1


    while True:
        response = get_next_job(argv[1], argv[2], argv[3])

        logging.info('Got response: %s', response)

        pretty = json.loads(response)
        (status_ok, start_string) = parse_response(pretty)
        if status_ok:
            execute_job(start_string)
        else:
            break

    logging.error('Could not get next job')
    logging.warning('Shutting down the machine')
    # posssibly shut down the machine here
    return 1

def get_next_job(site_url, username, password):

    if not site_url.startswith('http'):
        site_url = '%s%s' % ('http://', site_url)

    logging.info('siteurl: %s username: %s password: %s', site_url, username, password)

    endpoint = urljoin(site_url, service_url)
    userpass= base64.encodestring('%s:%s' % (username, password)).replace('\n', '')

    #delete this later, current implementation requires HASH
    endpoint = urljoin(endpoint, '?hash=12345')
    logging.info('endpoint: %s', endpoint)

    request = urllib2.Request(endpoint)
    # add authentication header
    request.add_header("Authorization", "Basic %s" % userpass)  
    try:
        logging.info('Connecting to %s', endpoint)
        response = urllib2.urlopen(request)
        return response.read()

    except Exception:
        logging.error('Could not connect to server')
        return None


def parse_response(pretty):
    if not 'response' in pretty:
        print 'Wrong response from server'
        return (False,'')
    response_status = pretty['response']
    if not response_status == 'OK':
        print 'Response is NOTOK'
        return (False,'')
    if not 'start_string' in pretty:
        print 'No start string is found'
        return (False,'')
    return (True,pretty['start_string'])


def execute_job(start_string):
    try:
        args = shlex.split(start_string)
        logging.info('Splitted start_string is: %s', str(args))
        p = subprocess.Popen(args)
    except OSError:
        logging.error('Could not start: %s', start_string)
    else:
        while True:
            returncode = p.poll()
            if returncode:
                logging.info('The job was finished with return code %s')

                # break the loop
                break
            else:
                # the process is still running
                # sleep
                time.sleep(server_poll_delay)
                # poll the server
                if should_terminate_job(argv[1]):
                    # kill the job and exit from the loop
                    p.kill()
                    break

                
def should_terminate_job(location):
    # TODO
    # make request to plone and check if the job should be terminated
    return False


main()
