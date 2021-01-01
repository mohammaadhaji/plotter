from PyQt5 import uic, QtGui
from PyQt5.QtWidgets import QMessageBox, QMainWindow, QApplication, QShortcut, QPlainTextEdit, QAction
from PyQt5.QtGui import QColor, QKeySequence
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from combobox import ComboBox
from threads import SerialThread
import pyqtgraph as pg
import sys, os, pathlib
import numpy as np
import random
import serial.tools.list_ports
import time
import threading
from pynotifier import Notification
import glob
#----------------------------------Get Files Path-------------------------------
UI_file_name = 'main_UI.ui'
current_file_dir = pathlib.Path(__file__).parent.absolute()
UI_dir = os.path.join(current_file_dir, UI_file_name)
# icon_dir = os.path.join(current_file_dir, 'icon.png')


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        #----------------------------------Load the UI Page-------------------------------
        uic.loadUi(UI_dir, self)
        # self.setWindowIcon(QtGui.QIcon(icon_dir))

        #---------------------------Set Connection Modes Activation-----------------------
        self.rdb_serial.setChecked(True)
        self.rdb_ethernet.clicked.connect(self.u_maintenance)
        self.rdb_USB.clicked.connect(self.u_maintenance)
        self.connected = False

        #------------------------------Some Serial Option in Dict-------------------------
        self.s_opt = {'bs5': serial.FIVEBITS, 'bs6': serial.SIXBITS, 'bs7': serial.SEVENBITS,
             'bs8': serial.EIGHTBITS, 'sb1': serial.STOPBITS_ONE, 'sb1.5': serial.STOPBITS_ONE_POINT_FIVE,
             'sb2': serial.STOPBITS_TWO, 'pNone': serial.PARITY_NONE, 'pOdd': serial.PARITY_ODD,
             'pEven': serial.PARITY_EVEN, 'pMark': serial.PARITY_MARK, 'pSpace': serial.PARITY_SPACE,
             }

        #---------------------------------------Threads-----------------------------------
        self.ser_thread = SerialThread()

        #--------------------------------------Get Ports----------------------------------
        self.get_ports()
        self.comb_sPort.arrowClicked.connect(self.get_ports)

        #-------------------------------------Shortcuts-----------------------------------
        self.auto_range_shortcut = QShortcut(QKeySequence("Ctrl+A"), self)
        self.auto_range_shortcut.activated.connect(self.auto_range)
        self.btn_clear_plot.setShortcut('Ctrl+P')
        self.btn_reset_y.setShortcut('Ctrl+R')
        self.btn_send.setShortcut('Ctrl+S')
        self.connectAction = QAction('Toggle connection', self)
        self.connectAction.setShortcut('Ctrl+C')
        self.connectAction.triggered.connect(self.connection)
        self.addAction(self.connectAction)
        self.transmissionAction = QAction('Toggle Show', self)
        self.transmissionAction.setShortcut('Ctrl+D')
        self.transmissionAction.triggered.connect(self.show_transmission)
        self.addAction(self.transmissionAction)

        #--------------------------------Plot Initialization------------------------------
        self.lines = {'line0': [], 'line1': [], 'line2': [],
                      'line3': [], 'line4': []}
        self.x = []
        self.count = 0
        self.graphWidget = pg.PlotWidget()
        self.verticalLayout_5.addWidget(self.graphWidget)
        self.setMouseTracking(True)
        self.graphWidget.scene().sigMouseMoved.connect(self.onMouseMoved)
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.setMouseEnabled(x=True,y=False)  
        self.line0 = self.graphWidget.plot(self.x, self.lines['line0'], pen='b')
        self.line1 = self.graphWidget.plot(self.x, self.lines['line1'], pen='r')
        self.line2 = self.graphWidget.plot(self.x, self.lines['line2'], pen='g')
        self.line3 = self.graphWidget.plot(self.x, self.lines['line3'], pen='w')
        
        #-----------------------------------Plot Settings---------------------------------
        self.dial_ch1.valueChanged.connect(self.set_ch0_y)
        self.dial_ch2.valueChanged.connect(self.set_ch1_y)
        self.dial_ch3.valueChanged.connect(self.set_ch2_y)
        self.dial_ch4.valueChanged.connect(self.set_ch3_y)
        self.btn_reset_y.clicked.connect(self.reset_y)
        self.btn_clear_plot.clicked.connect(self.clear_data)
        self.spinBox_points.valueChanged.connect(self.set_points)
        self.comb_channels.currentTextChanged.connect(self.set_channels)
        self.points = self.spinBox_points.value()
        self.inc_or_dec_ch0 = 0
        self.inc_or_dec_ch1 = 0
        self.inc_or_dec_ch2 = 0
        self.inc_or_dec_ch3 = 0

        self.btn_connection.clicked.connect(self.connection)
        self.header = self.txb_header.text()
        self.txb_header.textChanged.connect(self.set_packet_label)
        self.txb_footer.textChanged.connect(self.set_packet_label)
        self.txb_data.textChanged.connect(self.set_packet_label)
        self.btn_send.clicked.connect(self.send)
        self.msg = QMessageBox()
        self.msg.setIcon(QMessageBox.Information)

    def show_transmission(self):
        if self.chBox_show_data.isChecked():
            self.chBox_show_data.setChecked(False)
        else:
            self.chBox_show_data.setChecked(True)

    def onMouseMoved(self, evt):        
        point =self.graphWidget.plotItem.vb.mapSceneToView(evt)
        self.lbl_coordinate.setText(f"X = {round(point.x(), 2)}\nY = {round(point.y(), 2)}")
         
    def send(self):
        packet = self.set_packet_label().encode('utf-8')
        self.ser_thread.write(packet)
        if packet:
            self.write(str(packet))

    def set_packet_label(self):
        packet = self.txb_header.text().upper() + self.txb_data.text().upper() + self.txb_footer.text().upper()
        self.lbl_packet.setText(f"Packet to Send : {packet}")
        return packet

    def reset_y(self):
        self.dial_ch1.setValue(0)
        self.dial_ch2.setValue(0)
        self.dial_ch3.setValue(0)
        self.dial_ch4.setValue(0)

    def set_ch0_y(self):
        self.inc_or_dec_ch0 = self.dial_ch1.value()
        self.lbl_ch1_y.setText(str(self.inc_or_dec_ch0))

    def set_ch1_y(self):
        self.inc_or_dec_ch1 = self.dial_ch2.value()
        self.lbl_ch2_y.setText(str(self.inc_or_dec_ch1))

    def set_ch2_y(self):
        self.inc_or_dec_ch2 = self.dial_ch3.value()
        self.lbl_ch3_y.setText(str(self.inc_or_dec_ch2))

    def set_ch3_y(self):
        self.inc_or_dec_ch3 = self.dial_ch4.value()
        self.lbl_ch4_y.setText(str(self.inc_or_dec_ch3))
        
    def u_maintenance(self):
        title = 'Under Maintenance...'
        msg = 'This section will be available in future versions.'
        self.message(title, msg)
        self.rdb_serial.setChecked(True)

    def set_channels(self):
        try:
            self.ser_thread.data.disconnect()
            self.clear_data()
        except Exception:
            pass
        channels = self.comb_channels.currentText()
        if channels == '1':
            self.ser_thread.data.connect(self.plot_ch0)
        elif channels == '2':
            self.ser_thread.data.connect(self.plot_ch1)
        elif channels == '3':
            self.ser_thread.data.connect(self.plot_ch2)
        elif channels == '4':
            self.ser_thread.data.connect(self.plot_ch3)
    
    def set_points(self):
        self.points = self.spinBox_points.value()
        
    def auto_range(self):
        self.graphWidget.enableAutoRange("xy", True)

    def get_ports(self):
        self.comb_sPort.clear()
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')

        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass

        for port in result:
            self.comb_sPort.addItem(port)

    def connection(self):
        self.connected = not self.connected
        if self.connected:
            if self.rdb_serial.isChecked():
                options, validation = self.get_serial_options()
                if validation == False:
                    return
                self.ser_thread.set_options(options)
                self.set_channels()
                self.ser_thread.ser_exp.connect(self.message)
                self.ser_thread.start()
                self.btn_connection.setText('Dis&connect')
                
            elif self.rdb_ethernet.isChecked():
                pass
            elif self.rdb_usb.isChecked():
                pass
        else:
            if self.rdb_serial.isChecked():
                self.ser_thread.set_ser_conn_false()
                self.ser_thread.data.disconnect()
                self.btn_connection.setText('&Connect')
            elif self.rdb_ethernet.isChecked():
                pass
            elif self.rdb_usb.isChecked():
                pass

    def read(self, data):
        if self.chBox_show_data.isChecked():
            data = f'<p style="font-size: 16px;">[ R ]> {data[1:-1]}</p>'
            self.ptxtEdit_log.appendHtml(data)
    
    def write(self, data):
        if self.chBox_show_data.isChecked():
            data = f'<p style="color:green;font-size: 16px;">[ S ]> {data}</p>'
            self.ptxtEdit_log.appendHtml(data)

    def plot_ch0(self, data):   
        self.lines['line0'].append(data[0] + (self.inc_or_dec_ch0))
        
        self.x.append(self.count)
        self.count += 1

        if len(self.x) > self.points:
            m = len(self.x) - self.points
            self.x = self.x[m:]
            self.lines['line0'] = self.lines['line0'][m:]

        self.read(str(data))

        self.line0.setData(self.x, self.lines['line0'])

    def plot_ch1(self, data):   
        self.lines['line0'].append(data[0] + (self.inc_or_dec_ch0))
        self.lines['line1'].append(data[1] + (self.inc_or_dec_ch1))
        
        self.x.append(self.count)
        self.count += 1

        if len(self.x) > self.points:
            m = len(self.x) - self.points
            self.x = self.x[m:]
            self.lines['line0'] = self.lines['line0'][m:]
            self.lines['line1'] = self.lines['line1'][m:]

        self.read(str(data))

        self.line0.setData(self.x, self.lines['line0'])
        self.line1.setData(self.x, self.lines['line1'])

    def plot_ch2(self, data):   
        self.lines['line0'].append(data[0] + (self.inc_or_dec_ch0))
        self.lines['line1'].append(data[1] + (self.inc_or_dec_ch1))
        self.lines['line2'].append(data[2] + (self.inc_or_dec_ch2))
        
        self.x.append(self.count)
        self.count += 1

        if len(self.x) > self.points:
            m = len(self.x) - self.points
            self.x = self.x[m:]
            self.lines['line0'] = self.lines['line0'][m:]
            self.lines['line1'] = self.lines['line1'][m:]
            self.lines['line2'] = self.lines['line2'][m:]

        if self.chBox_show_data.isChecked():
            self.read(str(data))

        self.line0.setData(self.x, self.lines['line0'])
        self.line1.setData(self.x, self.lines['line1'])
        self.line2.setData(self.x, self.lines['line2'])

    def plot_ch3(self, data):   
        self.lines['line0'].append(data[0] + (self.inc_or_dec_ch0))
        self.lines['line1'].append(data[1] + (self.inc_or_dec_ch1))
        self.lines['line2'].append(data[2] + (self.inc_or_dec_ch2))
        self.lines['line3'].append(data[3] + (self.inc_or_dec_ch3))
        
        self.x.append(self.count)
        self.count += 1

        if len(self.x) > self.points:
            m = len(self.x) - self.points
            self.x = self.x[m:]
            self.lines['line0'] = self.lines['line0'][m:]
            self.lines['line1'] = self.lines['line1'][m:]
            self.lines['line2'] = self.lines['line2'][m:]
            self.lines['line3'] = self.lines['line3'][m:]

        self.read(str(data))

        self.line0.setData(self.x, self.lines['line0'])
        self.line1.setData(self.x, self.lines['line1'])
        self.line2.setData(self.x, self.lines['line2'])
        self.line3.setData(self.x, self.lines['line3'])

    def get_serial_options(self):
        options = {}
        validation = True
        port = self.comb_sPort.currentText()
        if port == '':
            validation = False
            self.message('Invalid Input...', 'There are no available ports')
        options['port'] = port

        options['baudrate'] = int(self.comb_baudrate.currentText())

        options['bytesize'] = self.s_opt['bs' + self.comb_byteSize.currentText()]

        options['parity'] = self.s_opt['p' + self.comb_parity.currentText()]

        options['stopbits'] = self.s_opt['sb' + self.comb_stopBits.currentText()]

        flow_control = self.comb_flowControl.currentText()
        xonxoff, rtscts, dsrdtr = False, False, False
        if flow_control == 'Xon/Xoff':
            xonxoff = True
        elif flow_control == 'RTS/CTS':
            rtscts = True
        elif flow_control == 'DSR/DTR':
            dsrdtr = True

        options['xonxoff'] = xonxoff
        options['rtscts'] = rtscts
        options['dsrdtr'] = dsrdtr

        timeout = self.txb_rTimeout.text()
        if timeout == '':
            timeout = None
        elif not timeout.isdigit():    
            validation = False
            self.message('Invalid Input...', 'Read timeout must be a float value.')
        else:
            timeout = float(timeout)
        options['timeout'] = timeout

        write_timeout = self.txb_wTimeout.text()
        if write_timeout == '':
            write_timeout = None
        elif not write_timeout.isdigit():
            validation = False
            self.message('Invalid Input...', 'write timeout must be a float value.')
        else:
            write_timeout = float(write_timeout)
        options['write_timeout'] = write_timeout

        inter_byte_timeout = self.txb_ibTimeout.text()
        if inter_byte_timeout == '':
            inter_byte_timeout = None
        elif not inter_byte_timeout.isdigit():
            validation = False
            self.message('Invalid Input...', 'Inter byte timeout must be a float value.')
        else:
            inter_byte_timeout = float(inter_byte_timeout)
        options['inter_byte_timeout'] = inter_byte_timeout

        return options, validation
         
    def message(self, title, discription):
        if 'Serial' in title:
            self.btn_connection.setText('&Connect')
        self.msg.setWindowTitle(title)
        self.msg.setText(discription)
        self.msg.exec_()

    def clear_data(self):
        self.count = 0
        self.x.clear()
        for i in self.lines:
            self.lines[i].clear()

        self.auto_range()
        self.line0.setData(self.x, self.lines['line0'])
        self.line1.setData(self.x, self.lines['line1'])
        self.line2.setData(self.x, self.lines['line2'])
        self.line3.setData(self.x, self.lines['line3'])
        self.ptxtEdit_log.clear()
        
            
def main():
    app = QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())

if __name__ == '__main__':         
    main()