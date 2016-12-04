__author__ = 'blackthorne'

import call
import logging
import cStringIO
import unittest
import datetime


def hexdump(src, length=16, sep='.'):
    FILTER = ''.join([(len(repr(chr(x))) == 3) and chr(x) or sep for x in range(256)])
    lines = []
    for c in xrange(0, len(src), length):
        chars = src[c:c+length]
        hex = ' '.join(["%02x" % ord(x) for x in chars])
        if len(hex) > 24:
            hex = "%s %s" % (hex[:24], hex[24:])
        printable = ''.join(["%s" % ((ord(x) <= 127 and FILTER[ord(x)]) or sep) for x in chars])
        lines.append("%08x:  %-*s  |%s|\n" % (c, length*3, hex, printable))
    print ''.join(lines)


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt='%m-%d %H:%M:%S',)

logger = logging.getLogger(__name__)
logger.debug('tests beginning..')

output = cStringIO.StringIO()
output.write('First line.\n')
print >>output, 'Second line.'

class LibcallTest(unittest.TestCase):

    # calls subprocess without timeout
    def testSubprocessWithoutTimeout(self):
        a = call.Command(['ls','-l','/'],'subprocess', logger=logger)
        b = a.start()
        num_lines = sum(1 for line in a.stdout)
        self.assertEqual(b, 0)
        self.assertEqual(a.stderr, "")
        self.assertTrue(num_lines > 50)


    # calls subprocess without timeout (fail)
    def testSubprocessWithoutTimeoutFail(self):
        a = call.Command(['ls','2222-l','/'],'subprocess', logger=logger)
        b = a.start()
        num_lines = sum(1 for line in a.stdout)
        self.assertIn(b, [1,2])
        self.assertEqual(a.stderr, "ls: 2222-l: No such file or directory\n")
        self.assertTrue(num_lines > 50)

    #
    # c = call.Command(['ls23','-l','/'],'subprocess', logger=logger, )
    # c.start()
    # c.stop()
    # print c.return_code

    # # call subprocess with timeout
    # print '# call subprocess with timeout'
    # d = call.Command(['sleep','40'],'subprocess', logger=logger, timeout=5)
    # print d.status
    # print d.start()
    # print d.stop()
    #

    # python basic call without timeout
    def testPythonCallWithoutTimeout(self):
        print '# python call without timeout'
        d = call.Command('print 2+2','python-basic', logger=logger)
        d.start()
        self.assertEquals(d.stdout, "4\n")
    #
    # code = """
    # print 'hello'
    # print 'world'
    # """
    # d = call.Command(code,'python-basic', logger=logger)
    # print d.status
    # print d.start()
    # print d.stop()
    #
    # d = call.Command('aasdprint "hello"','python-basic', logger=logger)
    # print d.status
    # print d.start()
    # print d.stop()
    #
    #
    # python call with timeout
#     def testPythonCallWithTimeout(self):
#         print '# python call with timeout' # known limitation
#         code = """
# import time
# time.sleep(10)
# print "hello"
# """
#         d = call.Command(code,'python-basic', logger=logger, timeout=2)
#         time_start = datetime.datetime.now()
#         d.start()
#         time_end = datetime.datetime.now()
#         time_diff = time_end - time_start
#         self.assertGreaterEqual(time_diff.seconds, 2)
#         self.assertLess(time_diff.seconds, 9)
#         self.assertNotEqual(d.stdout, "hello\n")

    def testPythonCallBreakLoopWithTimeout(self):
        code = """
import time
while True:
    time.sleep(0.1)
print 'end'
"""
        d = call.Command(code,'python-basic', logger=logger, timeout=2)
        time_start = datetime.datetime.now()
        d.start()
        time_end = datetime.datetime.now()
        time_diff = time_end - time_start
        self.assertGreaterEqual(time_diff.seconds, 2)
        self.assertNotEqual(d.stdout, "end\n")

    #
    # shell call without timeout
    d = call.Command('uname -a','shell-env', logger=logger)
    time_start = datetime.datetime.now()


    def testShellCallBreakSleepWithTimeout(self):
        # shell call with timeout
        print '# shell call with timeout'
        d = call.Command('sleep 50','shell-env', logger=logger, timeout=2)
        time_start = datetime.datetime.now()
        d.start()
        time_end = datetime.datetime.now()
        time_diff = time_end - time_start
        self.assertGreaterEqual(time_diff.seconds, 2)
        self.assertLess(time_diff.seconds, 5)


if __name__ == '__main__':
    unittest.main()
    print 'END OF TESTS'