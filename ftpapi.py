from ftplib import FTP
import ftplib
import sys
import os
from common import log as logging

LOG = logging.getLogger(__name__) 
CONST_BUFFER_SIZE = 8192


class MyException(Exception):
    """
    self define exception class
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FtpClient(object):
    """
    FtpClient class
    """
    def __init__(self, srv_ip, srv_user, srv_pwd):
        self.ftp_ip = srv_ip
        self.ftp_user = srv_user
        self.ftp_pwd = srv_pwd
        self._connect()

    def _connect(self):
        try:
            self.conn = FTP(self.ftp_ip)
            self.conn.login(self.ftp_user, self.ftp_pwd)
        #except socket.error, socket.gaierror as e:
        except Exception as e:
            LOG.error("FTP: %s is unreachbal, error: %s, \
                check ip, user, pwd!" % (self.ftp_ip, e))
            raise MyException('FTP unreachbal: %s' % e)

    def _disconnect(self):
        self.conn.quit()

    def upload(self, file):
        """
        upload file to ftp server
        """
        try:
            fp = open(file, "rb")
        except Exception as e:
            LOG.error("open file: %s error: %s" % (file, e))
            raise MyException('open file error: %s' % e)

        file_name = os.path.split(file)[-1]
        try:
            self.conn.storbinary("STOE %s" % file_name, CONST_BUFFER_SIZE)
        except ftplib.error_perm:
            LOG.error("upload file: %s error: %s" % (file, e))
            raise MyException('upload file error: %s' % e)

    def download(self, file_name):
        """
        dowmload file from ftp server
        """
        try:
            fp = open(file_name, "wb")
        except Exception as e:
            LOG.error("open file: %s error: %s" % (file_name, e))
            raise MyException('open file error: %s' % e)

        try:
            self.conn.retrbinary("RETR %s" % file_name, fp.write, CONST_BUFFER_SIZE)
        except ftplib.error_perm as e:
            LOG.error("dowmload file: %s error: %s" % (file_name, e))
            raise MyException('dowmload file error: %s' % e)

