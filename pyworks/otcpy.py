#!/usr/bin/env python
'''service program for downloading test files
v.3.0.4b sep,17 2021
lang: Python2.4.
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


TODAY = strftime('%y%m%d')  # user CONSTs see in the end of this file
# set of graphic symbols for table drawing:
L, L1, L2, L3 = chr(132), chr(130), chr(131), chr(133)
T, T1, T2, T3 = chr(136), chr(135), chr(137), chr(134)
V, H, X = chr(129), chr(128), chr(138)


def help_view():
    help = "Usage:\n\
%s [-h] [-q] [-(r|z)] [-<days>] [<date>...] [<daterange>...]\n\
  -h  View this help and exit\n\
  -q  (quick/quietly) Run with default parameters (no user input)\n\
      and no resulting table view\n\
  -r or -z Use a connection on the primary (-r, 192.168.100.XXX) subnet\n\
      or backup (-z, 192.168.101.XXX) subnet. Default is '-z'\n\
  -days   number of days ago (-1 is yesterday)\n\
  <date>  6-digit date (YYMMDD) for downloading non-today's files\n\
      It's allowed to omit major digits of current year or month\n\
  <daterange> Range of two <date>s separated by a dash.\n\
      It's allowed to omit major digits of current year or month.\n\
      The second <date> can be omitted entirely: then the expression \n\
      should be understood as 'to this day'" % argv[0].split('/')[-1]
    print help
    exit()


def argparse():
    options = ''
    arg_date = []
    quiet = False
    subnet = DEFAULT_NET
    for arg in argv[1:]:
        if arg.startswith('-'):
            for letter in arg[1:]:
                options += letter
        elif match('\d{1,6}(-\d{0,6})?$', arg):
            arg_date.extend(nums2dates(arg.split('-')))
	else:
	    print " incorrect arguments ".center(WRN_LEN, '=')
	    help_view()
    for option in options:
        if option == 'q':
            quiet = True
        elif option == 'r':
            subnet = '192.168.100.10'
        elif option == 'z':
            subnet = '192.168.101.10'
        elif option.isdigit():
            day_ago = int(option)
            date_ = int(TODAY)
            while day_ago > 0:
                date_ -=1
                if isdate(date_):
                    day_ago -= 1
            arg_date.append(str(date_) + '_')
        else:
            help_view()
    if 'r' in options and 'z' in options:
        print " incorrect arguments (-r and -z together) ".center(WRN_LEN, '=')
        help_view()
    if not arg_date:  # user don't set any date
        arg_date.append(TODAY + '_')  # set default date: TODAY_
    else:
        arg_date = sorted(set(arg_date))

    return quiet, arg_date, subnet


def isdate(check_date):
    year, month, day = map(int, [str(check_date)[i * 2:i * 2 + 2]\
                        for i in range(3)])
    if month > 12 or month == 0 or day > 31 or day == 0:
        return False
    if day == 31 and month in (2, 4, 6, 9, 11):
        return False
    if month == 2 and day > 29:
        return False
    if year % 4 and month == 2 and  day > 28:
        return False
    return True


def nums2dates(period_borders):

    def fulldate(shortdate):
        result = int(TODAY[:6 - len(shortdate)] + shortdate)
        if isdate(result):
            return result
        else:
            print " not existing date in argument! ".center(WRN_LEN, '=')
            help_view()

    # add leading '0' to one-digit monthday or month:
    prd_brds = map(lambda x: '0' * (len(x) % 2) + x, period_borders)
    try:
        left_border, right_border = prd_brds
    except ValueError:
        start_date = fulldate(prd_brds[0])
        finish_date = start_date + 1
    else:
        right_border = right_border or TODAY  # (for case YYMMDD- arg)
        if len(right_border) <= len(left_border)\
 and int(right_border) > int(left_border[-len(right_border):]):
            right_border = left_border[:-len(right_border)] + right_border
        start_date = fulldate(left_border)
        finish_date = fulldate(right_border) + 1
        if start_date >= finish_date:
            print " incorrect daterange argument: ".center(WRN_LEN, '='), '\n',\
            " the second date is earlier than the first! ".center(WRN_LEN, '=')
            help_view()
    return [str(i) + '_' for i in range(start_date, finish_date) if isdate(i)]


class TestFinder(object):

    def __init__(self, script_args):
        self.dates, self.net_ = script_args
        self.rmo = DEFAULT_RMO
        self.out_dir = DEFAULT_OUTPUT

    def run_search(self):
        for vk in self.rmo:  # launch download procedure(s)
            searched_ip = self.net_ + vk
            self.file_transfer(searched_ip)
            if self.target_files:
                print "DONE: total %s file(s) copied from %s to %s\n" \
                    % (len(self.target_files), searched_ip, self.out_dir)
            else:
                print (" NO test files found on %s " \
                    % searched_ip).center(WRN_LEN, '=') , '\n'

    def file_transfer(self, ip_addr):
        try:
            ftp = FTP(ip_addr)
            ftp.login(user="user", passwd="user")
        except Exception:
            print (" %s : FTP connection error! " \
                % ip_addr).center(WRN_LEN, '=')
            return
	
        ftp.cwd("fpo/exec77ya6/lib/tmp")
        ftp_nlst = ftp.nlst()
        self.target_files = [f for d in self.dates for f in ftp_nlst if d in f]

        for filename in self.target_files:
            dest_file = open(path.join(self.out_dir, filename), 'wb')
            ftp.retrbinary('RETR ' + filename, dest_file.write)  # download target files
            dest_file.close()

            stdout.write('.')  # output dotline
            stdout.flush()
        stdout.write('\n')

        ftp.close()


class VerboseTestFinder(TestFinder):

    def __init__(self, script_args):
        super(VerboseTestFinder, self).__init__(script_args)
        self.t_files = dict()  # initialization of infostructure\
        for test in TEST_SET:  # listing found test files
            self.t_files[test] = {"html": [], "bmp": []}
        self.t_files['other'] = []
        self.max_file_length = 0
        self.rmo_live = dict()
        self.q = Queue(5)
        self.user_interact()

    def user_interact(self):

        def ping_rmo(ip_addr):
            cmnd_ping = "ping -c2 -l2 -i0.2 -q " + ip_addr
            pg = Popen(cmnd_ping, shell=True, stdout=PIPE)
            out = pg.stdout.read()
            self.q.put({ip_addr: not "100% packet loss" in out})

        # prepare for drawing welcome table:
        for ip_addr in RMO_LIST:  # check accessibility of all RMO
            ipa = self.net_ + ip_addr
            t = Thread(target=ping_rmo, args=(ipa,))
            t.Daemon = True
            t.start()

        for _ in RMO_LIST:  # ... and store checking results
            self.rmo_live.update(self.q.get())

        # drawing the welcome table:
        self.draw_welcome()

        # request for choose the download host and the output folder
        self.user_input()  

    def _fuck_you():
        print " Fuck you! ".center(WRN_LEN, '=')
        exit()

    def draw_welcome(self):
        rs = dict()  # special (unlike of self.rmo_live) RMO status
        # translating self.rmo_live -> rs :
        for ip in self.rmo_live:
            key = ip[-1]
            if self.rmo_live[ip]:
                choise_string = key.center(5, '-').center(17)
            else:
                choise_string = "not available now"
                RMO_LIST.remove(key)
            rs.update({key: choise_string})

        print '\n' + L1 + H * 7 + \
            " Welcome to copying test files script " + H * 8 + L2
        print V + " Select the computer on which tests were performed:  " + V
        print T3 + H * 17 + T + H * 17 + T + H * 17 + T1
        print V + "      SPKDS:     " + V + "       KDS:      "\
            + V + "      DEGI:      " + V
        print V + rs['3'] + V + rs['2'] + V + rs['4'] + V
        print L + H*8 + T + H*8 + T2 + H*8 + T + H*8 + T2 + H*8 + T + H*8 + L3
        print ' ' * 9 + V + "    Commander:   " + V + "   Staff chief:  " + V
        print ' ' * 9 + V + rs['5'] + V + rs['6'] + V
        print ' ' * 9 + L + H * 17 + T2 + H * 17 + L3
        rs.clear()
        self.rmo_live.clear()

    def user_input(self):
        fake_input_count = 0
        def fuck_you():
            print " Fuck you! ".center(WRN_LEN, '=')
            exit()
        while fake_input_count < 3:
            stdout.write("please, enter corresponding number(s)=> ")
            stdout.flush()
            if DEFAULT_RMO in RMO_LIST:
                self.rmo = raw_input("(%s) " % DEFAULT_RMO) or DEFAULT_RMO
            else:
                self.rmo = raw_input()
            for vk in self.rmo:
                if not vk in RMO_LIST:
                    fake_input_count += 1
                    print (" Only numbers %s are valid " \
                        % sorted(RMO_LIST)).center(WRN_LEN, '=')
                    break
            else:
                break
        else:
            fuck_you()
    
        print (" Default destination directory is: %s " \
            % DEFAULT_OUTPUT).center(WRN_LEN, '=')
        while fake_input_count < 4:
            self.out_dir = raw_input("type another, if necessary (Enter): ")\
                    or DEFAULT_OUTPUT
            if path.exists(self.out_dir + '/'):
                break
            else:
                print (" dir %s doesn't exists ! " \
                    % self.out_dir).center(WRN_LEN, '=')
                answr = raw_input("do you want to create it? (y/n): ")
                if answr.lower() in ('y', 'yes', 'd', 'da', 'ok'):
                    mkdir(self.out_dir)
                    break
                else:
                    fake_input_count += 1
        else:
            fuck_you()

    def file_transfer(self, ip_addr):
        super(VerboseTestFinder, self).file_transfer(ip_addr)
        if not self.target_files:
            return
        for filename in self.target_files:
            for test in TEST_SET:  # filling the infostructure t_files{} 
                        # with the names of the found files
                if filename.find(test) == 1:
                    if filename.endswith('htm'):
                        self.t_files[test]['html'].append(filename)
                        break
                    elif filename.endswith('bmp'):
                        self.t_files[test]['bmp'].append(filename)
                        break
            else:
                self.t_files['other'].append(filename)

        self.table_draw(ip_addr, max(map(len, self.target_files)))

    def table_draw(self, addr, FL):  # drawing and filling the resulting table

        HW = max(map(lambda x: len(x), TEST_SET))  # 1-st table column width
        TW = HW + 2 * FL + 2  # total table width
        IP_hd, TXT_hd, PIC_hd = "files from " + addr + " :", "HTML", "BMP"  # table columns headers
        print L1 + H * TW + L2
        print V + IP_hd.center(TW) + V
        print T3 + H * HW + T + H * FL + T + H * FL + T1
        print V + ' ' * HW + V + TXT_hd.center(FL) + V + PIC_hd.center(FL) + V

        for test in TEST_SET:
            print T3 + H * HW + X + H * FL + X + H * FL + T1
            for line in range(max((len(self.t_files[test]['html']), \
	            len(self.t_files[test]['bmp']), 1))):
                try:
                    file_htm = self.t_files[test]['html'][line]
                except IndexError:
                    file_htm = '-' * FL
                try:
                    file_bmp = self.t_files[test]['bmp'][line]
                except IndexError:
                    file_bmp = '-' * FL
                if line == 0:
                    HT = test.center(HW) 
		else:
                    HT = ' ' * HW
                print V + HT + V + file_htm.ljust(FL) + V + file_bmp.ljust(FL) + V

        print L + H * HW + T2 + H * FL + T2 + H * FL + L3

        if self.t_files['other']:
            print 'other %s files: ' % (len(self.t_files['other']))
            for oth_file in self.t_files['other']:
                print ' ' * 6 + '%s' % (oth_file)
    

def choose_mod(quiet, arg_date, subnet):
    if quiet:
        return TestFinder((arg_date, subnet))
    else:
        return VerboseTestFinder((arg_date, subnet))


if __name__ == '__main__':

    TEST_SET = ('730', '735', '733')  # list of tests: possible addition or deletion
    RMO_LIST = set('23456')
    DEFAULT_OUTPUT = "/root/tests"  #/mnt/flash"
    DEFAULT_NET = '192.168.101.10'
    DEFAULT_RMO = '5'
    WRN_LEN = 55  # warning string length
    tf = choose_mod(*argparse())
    tf.run_search()
