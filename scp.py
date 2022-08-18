import locale
import os
import re
from socket import timeout as SocketTimeout
import collections

class SCPClient(object):
    def __init__(self, transport, buff_size=16384, socket_timeout=5.0,
                 progress=None, sanitize=None):
        self.transport = transport
        self.buff_size = buff_size
        self.socket_timeout = socket_timeout
        self.channel = None
        self.preserve_times = False
        self._progress = progress
        self._recv_dir = b''
        self._rename = False
        self._utime = None
        self.sanitize = sanitize if sanitize else _sh_quote
        self._dirtimes = {}

    def __enter__(self):
        self.channel = self._open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def _open(self):
        """open a scp channel"""
        if self.channel is None:
            self.channel = self.transport.open_session()

        return self.channel

    def close(self):
        """close scp channel"""
        if self.channel is not None:
            self.channel.close()
            self.channel = None

    def _recv_file(self, cmd):
        chan = self.channel
        parts = cmd.strip().split(b' ', 2)

        try:
            mode = int(parts[0], 8)
            size = int(parts[1])
            if self._rename:
                path = self._recv_dir
                self._rename = False
            elif os.name == 'nt':
                path = os.path.join(asunicode_win(self._recv_dir),
                                    parts[2].decode('utf-8'))
            else:
                path = os.path.join(asbytes(self._recv_dir),
                                    parts[2])
        except:
            chan.send('\x01')
            chan.close()
            raise SCPException('Bad file format')

        try:
            file_hdl = open(path, 'wb')
        except IOError as e:
            chan.send(b'\x01' + str(e).encode('utf-8'))
            chan.close()
            raise e

        if self._progress:
            if size == 0:
                # avoid divide-by-zero
                self._progress(path, 1, 1)
            else:
                self._progress(path, size, 0)
        buff_size = self.buff_size
        pos = 0
        chan.send(b'\x00')
        try:
            while pos < size:
                # we have to make sure we don't read the final byte
                if size - pos <= buff_size:
                    buff_size = size - pos
                file_hdl.write(chan.recv(buff_size))
                pos = file_hdl.tell()
                if self._progress:
                    self._progress(path, size, pos)

            msg = chan.recv(512)
            if msg and msg[0:1] != b'\x00':
                raise SCPException(asunicode(msg[1:]))
        except SocketTimeout:
            chan.close()
            raise SCPException('Error receiving, socket.timeout')

        file_hdl.truncate()
        try:
            os.utime(path, self._utime)
            self._utime = None
            os.chmod(path, mode)
            # should we notify the other end?
        finally:
            file_hdl.close()
        # '\x00' confirmation sent in _recv_all

    def _recv_pushd(self, cmd):
        parts = cmd.split(b' ', 2)
        try:
            mode = int(parts[0], 8)
            if self._rename:
                path = self._recv_dir
                self._rename = False
            elif os.name == 'nt':
                path = os.path.join(asunicode_win(self._recv_dir),
                                    parts[2].decode('utf-8'))
            else:
                path = os.path.join(asbytes(self._recv_dir),
                                    parts[2])
        except:
            self.channel.send(b'\x01')
            raise SCPException('Bad directory format')
        try:
            if not os.path.exists(path):
                os.mkdir(path, mode)
            elif os.path.isdir(path):
                os.chmod(path, mode)
            else:
                raise SCPException('%s: Not a directory' % path)
            self._dirtimes[path] = (self._utime)
            self._utime = None
            self._recv_dir = path
        except (OSError, SCPException) as e:
            self.channel.send(b'\x01' + asbytes(str(e)))
            raise e

    def _recv_popd(self, *cmd):
        self._recv_dir = os.path.split(self._recv_dir)[0]

    def _set_dirtimes(self):
        try:
            for d in self._dirtimes:
                os.utime(d, self._dirtimes[d])
        finally:
            self._dirtimes = {}


class SCPException(Exception):
    """SCP exception class"""
    pass