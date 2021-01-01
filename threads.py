from PyQt5.QtCore import QThread, pyqtSignal
import serial
import re

class SerialThread(QThread):
    data = pyqtSignal(list)
    ser_exp = pyqtSignal(str, str)
    def __init__(self):
        super(QThread, self).__init__()
        self.options = None
        self.ser_conn = None
        self.ser = None

    def set_options(self, options):
        self.options = options

    def set_ser_conn_false(self):
        self.ser_conn = False
        if self.ser:
            self.ser.close()
    
    def write(self, data):
        if data and self.ser:
            self.ser.write(data)
        
    def run(self):
        try:
            self.ser = serial.Serial(**self.options)

            self.ser_conn = True

            while self.ser_conn: 
                s = [float(i) for i in re.findall('[-\d.]+', str(self.ser.readline()))]
                if s:
                    self.data.emit(s)

        except serial.SerialException as e:
            if 'PermissionError' in str(e):
                msg = 'Can not open {port} port, it might be used in another program.'.format(port = self.options['port'])
                title = 'Serial Port Error'
                self.ser_exp.emit(title, msg)
            else:
                pass
        except Exception:
            pass
