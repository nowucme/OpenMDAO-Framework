##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

This is a modified version of the bootstrap.py file from Zope Corp.
It creates a bin/buildout script that is isolated from the system level
installed packages.

$Id$
"""

import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

try:
    import pkg_resources
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set
assert os.spawnle(
    os.P_WAIT, sys.executable, quote (sys.executable),
    '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout',
    dict(os.environ,
         PYTHONPATH=
         ws.find(pkg_resources.Requirement.parse('setuptools')).location
         ),
    ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout')
import zc.buildout.buildout

zc.buildout.buildout.main(sys.argv[1:] + ['bootstrap'])
shutil.rmtree(tmpeggs)

# now modify the bin/buildout script to isolate it

old_sp = 'import zc.buildout.buildout'
new_sp = """
import zc.buildout.buildout
import os.path
prefx = os.path.join(sys.prefix,'lib','python'+sys.version[0:3])
sys.path[:] = [  prefx+'.zip',
                 prefx,
                 os.path.join(prefx,'lib-dynload'),
                 os.path.join(prefx,'plat-'+sys.platform),
              ]+sys.path[0:2]
"""
new_sp_win = """
import zc.buildout.buildout
import os.path
prefx = os.path.join(sys.prefix,'Lib')
sys.path[:] = [  prefx,
                 os.path.join(sys.prefix,'DLLs'),
              ]+sys.path[0:2]
"""

if sys.platform == 'win32':
    new_sp = new_sp_win

try:
    f = open('bin/buildout','r')
    old = f.read()
finally:
    f.close()

try:    
    newf = open('bin/buildout','w')
    newf.write(old.replace(old_sp, new_sp))
finally:
    newf.close()
    