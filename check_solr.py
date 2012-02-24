#!/usr/bin/env python26
'''
check_solr.py - v0.1 -  Chris Ganderton <github@thefraggle.com>

Nagios check script for checking replication issues on solr slaves.

We simply get the index version that the core reports it has, and 
then query the maximum possible index version the master has told the core about.

OPTIONS:

-H : hostname/ip of the solr server we want to query
-p : tcp port solr is listening on
-w : webapp path

EXAMPLE: ./check_solr_rep.py -H localhost -p 8093 -w webapp -r -P

'''
'''
    we could think about using timesFailed, but we need to be sure we can reset this once we know about errors and they're resolved...

    if st.get('timesFailed') != None:
        print "CRIT: replication failure"
    else:
        print "OK: No replication errors"

'''
import urllib, json, sys
from optparse import OptionParser

def listcores():
    status_cmd  = baseurl + core_admin_url + urllib.urlencode({'action':'status','wt':'json'})
    cores       = []

    res         = urllib.urlopen(status_cmd)
    data        = json.loads(res.read())

    core_data   = data['status']

    for core_name in core_data:
        cores.append(core_name)

    return cores

def corerepstatus(core):
    rep_cmd     = baseurl + core + '/replication?' + urllib.urlencode({'command':'details','wt':'json'})
    status_cmd  = baseurl + core_admin_url + urllib.urlencode({'action':'status','wt':'json','core':core})

    ares        = urllib.urlopen(status_cmd)
    adata       = json.loads(ares.read())

    rres        = urllib.urlopen(rep_cmd)
    rdata       = json.loads(rres.read())

    curind      = adata['status'][core]['index'].get('version')
    availind    = rdata['details']['slave']['masterDetails']['master'].get('replicatableIndexVersion')

    if curind == availind:
        status = "Ok"
    else:
        status = "Error"

    return status

def solrping(core):
    ping_cmd = baseurl + core + '/admin/ping?' + urllib.urlencode({'wt':'json'})
    
    res = urllib.urlopen(ping_cmd)
    data = json.loads(res.read())

    status = data.get('status')

    return status

def main():
    ''' ought to put this into it's own func ''' 
    check_replication = False
    check_ping        = False

    cmd_parser = OptionParser(version="%prog 0.1")
    cmd_parser.add_option("-H", "--host", type="string", action="store", dest="solr_server", default="localhost", help="SOLR Server address")
    cmd_parser.add_option("-p", "--port", type="string", action="store", dest="solr_server_port", help="SOLR Server port")
    cmd_parser.add_option("-w", "--webapp", type="string", action="store", dest="solr_server_webapp", help="SOLR Server webapp path")
    cmd_parser.add_option("-P", "--ping", action="store_true", dest="check_ping", help="SOLR Ping")
    cmd_parser.add_option("-r", "--replication", action="store_true", dest="check_replication", help="SOLR Replication check")

    (cmd_options, cmd_args) = cmd_parser.parse_args()

    if not (cmd_options.solr_server and cmd_options.solr_server_port and cmd_options.solr_server_webapp):
        cmd_parser.print_help()
        sys.exit(3)
    
    global baseurl, core_admin_url

    solr_server         = cmd_options.solr_server
    solr_server_port    = cmd_options.solr_server_port
    solr_server_webapp  = cmd_options.solr_server_webapp
    check_ping          = cmd_options.check_ping
    check_replication   = cmd_options.check_replication

    baseurl             = 'http://' + solr_server + ':' + solr_server_port + '/' +  solr_server_webapp + '/'
    core_admin_url      = 'admin/cores?'
    indexerrors         = []
    pingerrors          = []

    try:
        cores = listcores()
    except IOError as (errno, strerror):
        print "CRIT: {0} - {1}".format(errno,strerror)
        sys.exit(-1)
    except ValueError, TypeError:
        print "CRIT: probably couldn't format JSON data, check SOLR is ok"
        sys.exit(-1)
    except:
        print "CRIT: Unknown error"
        sys.exit(-1)

    try:
        for core in cores:
            if check_replication == True:
                if corerepstatus(core) == 'Error':
                    indexerrors.append(core)
            if check_ping == True:
                if solrping(core) != 'OK':
                    pingerrors.append(core)
    except IOError as (errno, strerror):
        print "CRIT: {0} {1} ".format(errno, strerror)
        sys.exit(-1)
    except KeyError as strerror:
        if 'slave' in strerror: 
            print "CRIT: This doesn't seem to be a slave, are you sure you meant to call -r?"
            sys.exit(-1)
        else:
            print "CRIT: unknown error (error string: {0})".format(strerror)
            print strerror
            sys.exit(-1)
    
    if not indexerrors and not pingerrors:
        print "OK: no issues"
        return 0
    elif pingerrors:
        print "CRIT: error pinging core(s) - ",
        print ", ".join(pingerrors)
        return -1
    elif indexerrors:
        print "WARN: replication errors on core(s) -",
        print ", ".join(indexerrors)

if __name__ == '__main__':
    sys.exit(main())
    
