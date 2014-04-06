#!/usr/bin/python2


"""
argv[0] is name of script
argv[1] location of the vm
argv[2] access_key
"""

from urlparse import urljoin
import urllib2
import urllib
import subprocess
import shlex
import logging
import time
import json
from argparse import ArgumentParser

NEXT_JOB_SERVICE_URL = 'get_next_job'
GET_STATUS_URL = 'provide_status'
UPDATE_STATUS_URL = 'update_status'
SERVER_POLL_DELAY = 3   # seconds

# enable logging
logging.basicConfig(level=logging.DEBUG)


def main():
    """ The main function """

    global SERVER_POLL_DELAY
    # parse the command line arguments
    parser = ArgumentParser(description='Execute shell script from plone site')
    parser.add_argument('vm_url')
    parser.add_argument('access_key')
    parser.add_argument('--polling_delay', default=SERVER_POLL_DELAY)

    args = vars(parser.parse_args())
    vm_url = args['vm_url']
    if not vm_url.startswith('http'):
        vm_url = '%s%s' % ('http://', vm_url)
    SERVER_POLL_DELAY = args['polling_delay']

    while True:
        response = make_request(vm_url, NEXT_JOB_SERVICE_URL, args['access_key'])

        logging.info('Got response: %s', response)

        pretty = json.loads(response)
        (status_ok, start_string) = parse_response(pretty)
        if status_ok:
            execute_job(start_string, args['vm_url'], args['access_key'])
        else:
            break
        time.sleep(SERVER_POLL_DELAY)

    logging.error('Could not get next job')
    logging.warning('Shutting down the machine')
    # posssibly shut down the machine here

    shutdown_cmd = shlex.split('shutdown -h now')
    logging.info('shutdown cmd is: %s', str(shutdown_cmd))
    logging.info('shuttting down machine in 3 mins')
    time.sleep(180)
    logging.info('shutting down the machine now')
    subprocess.Popen(shutdown_cmd)
    return 1


def make_request(vm_url, service_url, access_key, params=None):
    """ get the next job from plone """

    if vm_url[len(vm_url) - 1] != '/':
        vm_url += '/'
    logging.info('siteurl: %s access_key: %s', vm_url, access_key)

    endpoint = urljoin(vm_url, service_url)

    endpoint = urljoin(endpoint, '?hash=%s' % access_key)
    logging.info('endpoint: %s', endpoint)

    request = urllib2.Request(endpoint)
    if params:
        request.add_data(urllib.urlencode(params))
    # add authentication header
    # request.add_header("Authorization", "Basic %s" % userpass)

    try:
        logging.info('Connecting to %s', endpoint)
        response = urllib2.urlopen(request)
        return response.read()

    except urllib2.HTTPError as herror:
        logging.error('Received error code ' + str(herror.code))
        return None
    except urllib2.URLError:
        logging.error('Could not connect to server')
        return None


def parse_response(pretty):
    """ Parse the server response
        Returns a tuple with (True, start_string) on success
                        and (False, '') on failure
    """
    if not 'response' in pretty:
        print 'Wrong response from server'
        return (False, '')
    response_status = pretty['response']
    if not response_status == 'OK':
        print 'Response is NOTOK'
        return (False, '')
    if not 'start_string' in pretty:
        print 'No start string is found'
        return (False, '')
    return (True, pretty['start_string'])


def execute_job(start_string, vm_url, access_key):
    """ Run the specified shell command
        in a new process.
        Polls the plone site about the state of the job
        from the main thread
    """
    try:
        arr_start = shlex.split(start_string)
        logging.info('Splitted start_string is: %s', str(arr_start))
        proc = subprocess.Popen(arr_start)
    except OSError:
        logging.error('Could not start: %s', start_string)
        update_job_status(vm_url, access_key,
                          {'new_status': 'Failed', 'message': 'OSError'})
    except TypeError:
        logging.error('Invalid arg for starting process')
        update_job_status(vm_url, access_key,
                          {'new_status': 'Failed', 'message': 'TypeError'})
    else:
        while True:
            returncode = proc.poll()
            if returncode != None:
                logging.info('The job was finished with return code %s')

                update_job_status(vm_url, access_key,
                                  {'new_status': 'Finished' if returncode == 0 else 'Failed'})
                # break the loop
                break
            else:
                # the process is still running
                # sleep
                time.sleep(SERVER_POLL_DELAY)
                # poll the server
                if should_terminate_job(vm_url, access_key):
                    # kill the job and exit from the loop
                    proc.kill()
                    break


def should_terminate_job(vm_url, access_key):

    response = make_request(vm_url, GET_STATUS_URL, access_key)
    if not response:
        logging.error('Was not able to retrieve job status')
        return False
    else:
        pretty = json.loads(response)
        if pretty.get('message', None):
            logging.info('response[message]: ' + pretty['message'])
            return pretty.get('message' != 'Running')
        else:
            logging.error('response did not contain field "message"')
            return False
        return False


def update_job_status(vm_url, access_key, params):

    response = make_request(vm_url, UPDATE_STATUS_URL, access_key, params)
    pretty = json.loads(response)

    if pretty.get('response', None):
        logging.info('update_job_status response is ' + str(pretty['response']))
        return pretty['response'] == 'success'
    else:
        logging.info('Did not get a valid response from update_job_status')
        return False

if __name__ == "__main__":
    main()
