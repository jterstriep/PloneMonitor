#!/usr/bin/python2


"""
argv[0] is name of script
argv[1] location of the plone site
argv[2] access_key
"""

from urlparse import urljoin
from sys import argv
import urllib2
import subprocess, shlex, logging, time, json
from argparse import ArgumentParser

SERVICE_URL = "@@get_next_job"
SERVER_POLL_DELAY = 3 # seconds

# enable logging
logging.basicConfig(level=logging.DEBUG)

def main():
    """ The main function """

    global SERVER_POLL_DELAY
    # parse the command line arguments
    parser = ArgumentParser(description='Execute shell script from plone site')
    parser.add_argument('site_url')
    parser.add_argument('access_key')
    parser.add_argument('--polling_delay', default=SERVER_POLL_DELAY)

    args = vars(parser.parse_args())

    SERVER_POLL_DELAY = args['polling_delay']


    while True:
        response = get_next_job(args['site_url'], args['access_key'])

        logging.info('Got response: %s', response)

        pretty = json.loads(response)
        (status_ok, start_string) = parse_response(pretty)
        if status_ok:
            execute_job(start_string)
        else:
            break
        time.sleep(SERVER_POLL_DELAY)

    logging.error('Could not get next job')
    logging.warning('Shutting down the machine')
    # posssibly shut down the machine here
    return 1

def get_next_job(site_url, access_key):
    """ get the next job from plone """
    if not site_url.startswith('http'):
        site_url = '%s%s' % ('http://', site_url)

    logging.info('siteurl: %s access_key: %s', site_url, access_key)

    endpoint = urljoin(site_url, SERVICE_URL)

    endpoint = urljoin(endpoint, '?hash=', access_key)
    logging.info('endpoint: %s', endpoint)

    request = urllib2.Request(endpoint)

    # add authentication header
    # request.add_header("Authorization", "Basic %s" % userpass)

    try:
        logging.info('Connecting to %s', endpoint)
        response = urllib2.urlopen(request)
        return response.read()

    except urllib2.HTTPError as herror:
        logging.error('Received error code ' + herror.code)
        return 0
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


def execute_job(start_string):
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
    except TypeError:
        logging.error('Invalid arg for starting process')
    else:
        while True:
            returncode = proc.poll()
            if returncode:
                logging.info('The job was finished with return code %s')

                # break the loop
                break
            else:
                # the process is still running
                # sleep
                time.sleep(SERVER_POLL_DELAY)
                # poll the server
                if should_terminate_job(argv[1]):
                    # kill the job and exit from the loop
                    proc.kill()
                    break


def should_terminate_job(location):
    """ TODO Make request to plone and check if the job should be terminated """
    return False

if __name__ == "__main__":
    main()
