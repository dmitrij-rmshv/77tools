#!/usr/bin/env python
'''service program for downloading test files
   v.1.06 jul,30 2021
   author: RDV
   '''
from os import path, mkdir
from time import strftime
from sys import exit, argv, stdout
from sre import match
from ftplib import FTP
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue


def help_view():
    help = "Usage:\n\
%s [-h] [-q[r|z]] [<date>...] [<daterange>...]\n\
  -h  View this help and exit\n\
  -q  (quick/quietly) Execute with default parameters (without user input)\n\
      and without drawing resulting table\n\
  -r or -z Use connection on the primary (-r, 192.168.100.XXX) subnet\n\
      or backup (-z, 192.168.101.XXX) subnet. Default is '-z'\n\
  <date>  6-digit date (YYMMDD) for downloading non-today's files\n\
      It's allowed to omit  major digits of current year or month\n\
  <daterange> Range of two <date>s separeted by a dash.\n\
      It's allowed to omit major digits of current year or month.\n\
      Second <date> can be omitted entirely: then expression is like 'to this day'" % argv[0].split('/')[-1]
    print help
    exit()


def isdate(check_date):
    year, month, day = map(int, [str(check_date)[i * 2:i * 2 + 2]  for i in range(len(str(check_date)) / 2)])
    if month > 12 or month == 0 or day > 31 or day == 0:
        return False
    if day == 31 and month in (2, 4, 6, 9, 11):
        return False
    if month == 2 and day > 29:
        return False
    if year % 4 == 0 and month == 2 and  day > 28:
        return False
    return True


def fulldate(shortdate):
    return int(TODAY[:6 - len(shortdate)] + shortdate)


def nums2dates(nums):
    start_date = fulldate(nums[0])
    try:
        finish_date = fulldate(nums[1]) + 1
        if start_date >= finish_date:
            print "=== incorrect daterange argument:  ===\n\
=== second date earlier than first ==="
            help_view()
    except IndexError:
        finish_date = start_date + 1
    return [str(i) + '_' for i in range(start_date, finish_date) if isdate(i)]


def rmo_ping(ip_addr, lvs):
    cmnd_ping = "ping -c2 -l2 -i0.2 -q " + "192.168." + lvs + ".10" + ip_addr
    pg = Popen(cmnd_ping, shell=True, stdout=PIPE)
    out = pg.stdout.read()
    if "100% packet loss" in out:
        q.put({ip_addr: "not available now"})
    else:
        out_string = "      --" + ip_addr + "--      "
	q.put({ip_addr: out_string})


def argparse():
    options = []
    arg_date = []
    quiet = False
    subnet = DEFAULT_SUBNET
    for arg in argv[1:]:
        if arg.startswith('-'):
            for letter in arg[1:]:
                options.append(letter)
        elif match('\d{1,6}(-\d{0,6})?$', arg):
            arg_date.extend(nums2dates(arg.split('-')))
	else:
	    print "=== incorrect arguments ==="
	    help_view()
    for option in options:
        if option == 'q':
	    quiet = True
	elif option == 'r':
	    subnet = '100'
	elif option == 'z':
	    subnet = '101'
	else:
	    help_view()
    if 'r' in options and 'z' in options:
        print "=== incorrect arguments (-r and -z together) ==="
	help_view()

    return arg_date, quiet, subnet


def table_draw(ip_addr, FL, t_files):  # drawing and filling the resulting table
    HL = max(map(lambda x: len(x), TEST_SET))  # 1-st table column width
    WL = HL + 2 * FL + 2  # total table width
    IP_hd, TXT_hd, PIC_hd = "files from " + ip_addr + " :", "HTML", "BMP"  # table columns headers
    print chr(130) + chr(128) * WL + chr(131)
    print chr(129) + ' ' * ((WL - len(IP_hd)) // 2) + IP_hd + ' ' * (((WL - len(IP_hd)) // 2) + ((WL - len(IP_hd)) % 2)) + chr(129)
    print chr(134) + chr(128) * HL + chr(136) + chr(128) * FL + chr(136) + chr(128) * FL + chr(135)
    htm_pre = (FL - len(TXT_hd))//2  # number of spaces before TXT_hd
    htm_post = htm_pre + (FL - len(TXT_hd))%2  # number of spaces after TXT_hd
    bmp_pre = (FL - len(PIC_hd))//2  # number of spaces before PIC_hd
    bmp_post = bmp_pre + (FL - len(PIC_hd))%2  # number of spaces after PIC_hd
    print chr(129) + ' ' * HL + chr(129) + ' ' * htm_pre + TXT_hd + ' ' * htm_post + chr(129) + ' ' * bmp_pre + PIC_hd + ' ' * bmp_post + chr(129)

    for test in TEST_SET:
        print chr(134) + chr(128) * HL + chr(138) + chr(128) * FL + chr(138) + chr(128) * FL + chr(135)
        for line in range(max((len(t_files[test]['html']), len(t_files[test]['bmp']), 1))):
            if len(t_files[test]['html']) > line:
                file_htm = t_files[test]['html'][line]
            else:
                file_htm = '-' * FL
            if len(t_files[test]['bmp']) > line:
                file_bmp = t_files[test]['bmp'][line]
            else:
                file_bmp = '-' * FL
            if line == 0:
                print chr(129) + ' ' * ((HL - len(test)) // 2) + test + ' ' * ((HL - len(test)) // 2 + (HL - len(test)) % 2) + \
chr(129) + '%s' % file_htm + ' ' * (FL - len(file_htm)) + chr(129) + '%s' % file_bmp + ' ' * (FL - len(file_bmp)) + chr(129)
            else:
                print chr(129) + ' ' * HL + chr(129) + '%s' % file_htm + ' ' * (FL - len(file_htm)) + chr(129) + '%s' % file_bmp + ' ' * (FL - len(file_bmp)) + chr(129)

    print chr(132) + chr(128) * HL + chr(137) + chr(128) * FL + chr(137) + chr(128) * FL + chr(133)

    if t_files['other']:
        print 'other %s files: ' % (len(t_files['other']))
        for oth_file in t_files['other']:
            print ' ' * 6 + '%s' % (oth_file)
    
    return


def ftp_search(ip_addr, input_date, out_path, quiet):
    
    t_files = dict()  # initialization of infostructure listing found test files
    for test in TEST_SET:
        t_files[test] = {"html": [], "bmp": []}
    t_files['other'] = []

    file_cnt = 0  # initialization of the counter of found test files
    filename_lenght = 0
    
    try:
        ftp = FTP(ip_addr)
        ftp.login(user="user", passwd="user")
    except Exception:
        print "%s : FTP connection error!" % ip_addr
	return
	
    ftp.cwd("fpo/exec77ya6/lib/tmp")
    
    for date_match in input_date:  # iterating over list of dates
        for filename in ftp.nlst():     # iterating over the target directory
            if date_match in filename:  # to find date_match's test files

                dest_file = open(path.join(out_path, filename), 'wb')
                ftp.retrbinary('RETR ' + filename, dest_file.write)  # download target files
                dest_file.close()
	    
                if len(filename) > filename_lenght:
                    filename_lenght = len(filename)

                file_cnt += 1
	    	
                for test in TEST_SET:  # filling the infostructure t_files{} with the names of the found files
                    if test in filename or 'A' + test[1:] in filename:
                        if "htm" in filename:
                            t_files[test]['html'].append(filename)
                            break
                        elif "bmp" in filename:
                            t_files[test]['bmp'].append(filename)
                            break
                else:
                    t_files['other'].append(filename)

                stdout.write('.')  # output dotline
                stdout.flush()
	    
    stdout.write('\n')

    if not file_cnt:
        print "No test files found on", ip_addr, '\n'
	ftp.close()
	return
    elif not quiet:
        table_draw(ip_addr, filename_lenght, t_files)
    
    print "Total %s file(s) copied from %s to %s\n" % (file_cnt, ip_addr, out_path)
    ftp.close()


def main():
    
    input_date, quiet_mode, subnet = argparse()
    if not input_date:
        input_date.append(TODAY)

    if quiet_mode:
        ftp_search("192.168." + DEFAULT_SUBNET + DEFAULT_RMO[-4:], input_date, DEFAULT_OUTPUT, quiet_mode)
	
    else:  # (verbose mode)
# check connectivity to all RMO:
        rmo_live = {}
        for ip_addr in RMO_LIST:
            t = Thread(target=rmo_ping, args=(ip_addr, subnet))
            t.daemon = True
            t.start()
        for _ in range(len(RMO_LIST)):
            rmo_live.update(q.get())
        rmo_live_list = [r for r in RMO_LIST if rmo_live[r] != "not available now"]
# draw welcome table:
        print '\n' + chr(130) + chr(128) * 7 + \
" Welcome to copying test files script " + chr(128) * 8 + chr(131)
        print chr(129) + " Select the computer on which tests were performed:  " + chr(129)
        print chr(134) + chr(128) * 17 + chr(136) + chr(128) * 17 + chr(136) + chr(128) * 17 + chr(135)
        print chr(129) + "      SPKDS:     "\
	    + chr(129) + "       KDS:      "\
	    + chr(129) + "      DEGI:      " + chr(129)
        print chr(129) + rmo_live['3'] + chr(129) + rmo_live['2'] + chr(129) + rmo_live['4'] + chr(129)
        print chr(132) + chr(128) * 8 + chr(136) + chr(128) * 8 + chr(137) + chr(128) * 8 + chr(136)\
                       + chr(128) * 8 + chr(137) + chr(128) * 8 + chr(136) + chr(128) * 8 + chr(133)
        print ' ' * 9 + chr(129) + "    Commander:   " + chr(129) + "   Staff chief:  " + chr(129)
        print ' ' * 9 + chr(129) + rmo_live['5'] + chr(129) + rmo_live['6'] + chr(129)
        print ' ' * 9 + chr(132) + chr(128) * 17 + chr(137) + chr(128) * 17 + chr(133)
        rmo_live.clear()
# receive user input:
        fake_input_count = 0
        while fake_input_count < 3:
            if DEFAULT_RMO[-1] in rmo_live_list:
                rmo = raw_input("please, enter corresponding number(s)=>(%s) " % DEFAULT_RMO[-1]) or DEFAULT_RMO[-1]
            else:
                rmo = raw_input("please, enter corresponding number(s)=> ")
            for vk in rmo:
                if not vk in rmo_live_list:
                    fake_input_count += 1
                    print "== Only numbers %s are valid ==" % rmo_live_list
                    break
            else:
                break
        else:
            print "=============== Fuck you! ==============="
            exit()
    
        print "==Default destination directory is: %s==" % DEFAULT_OUTPUT
        while fake_input_count < 4:
            destination_directory = raw_input("type another, if necessary (Enter): ") or DEFAULT_OUTPUT
            if path.exists(destination_directory + '/'):
                break
            else:
                print "== dir %s doesn't exists ! ==" % destination_directory
                answr = raw_input("do you want to create it? (y/n): ")
                if answr.lower() in ('y', 'yes', 'd', 'da', 'ok'):
                    mkdir(destination_directory)
		    break
                else:
                    fake_input_count += 1
        else:
            print "=============== Fuck you! ==============="
            exit()
# start REALY_MAIN function(s):
        for vk in rmo:
            ftp_search("192.168." + subnet + ".10" + vk, input_date, destination_directory, quiet_mode)


if __name__ == '__main__':

    TEST_SET = ('T730', 'T735', 'T733')  # list of tests: possible addition or deletion
    DEFAULT_RMO = "192.168.101.105"  # only the last 4 character of the string realy in use
    RMO_LIST = ('2', '3', '4', '5', '6')
    DEFAULT_OUTPUT = "/root/tests"  #/mnt/flash"
    DEFAULT_SUBNET = "101"
    TODAY = strftime('%y%m%d')
    q = Queue(5)
    
    main()
