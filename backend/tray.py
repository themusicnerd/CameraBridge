"""Native desktop control panel and system tray lifecycle."""
import argparse
import hashlib
import json
import pathlib
import sqlite3
import sys
from contextlib import closing
from PySide6.QtCore import QProcess,QTimer,Qt,QUrl
from PySide6.QtGui import QAction,QColor,QDesktopServices,QIcon,QPainter,QPen,QPixmap
from PySide6.QtNetwork import QLocalServer,QLocalSocket
from PySide6.QtWidgets import (QApplication,QCheckBox,QFileDialog,QFormLayout,QHBoxLayout,QLabel,QLineEdit,
    QMenu,QMessageBox,QPlainTextEdit,QPushButton,QSpinBox,QSystemTrayIcon,QVBoxLayout,QWidget)
from .desktop import DesktopSettings
from .server import Auth,ROOT,default_storage

def camera_icon():
    pixmap=QPixmap(64,64);pixmap.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pixmap);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor('#7433bd'));painter.drawRoundedRect(2,2,60,60,12,12)
    painter.setBrush(QColor('#ffffff'));painter.drawRoundedRect(11,21,34,25,5,5)
    painter.setPen(QPen(QColor('#ffffff'),5));painter.drawLine(47,27,54,23);painter.drawLine(54,23,54,44);painter.drawLine(54,44,47,40)
    painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor('#7433bd'));painter.drawEllipse(22,27,12,12);painter.end()
    return QIcon(pixmap)

class ControlPanel(QWidget):
    def __init__(self,storage,auto_start=True,create_tray=True):
        super().__init__();self.storage=pathlib.Path(storage);self.storage.mkdir(parents=True,exist_ok=True)
        self.settings=DesktopSettings.load(storage);self.quitting=False;self.restart_pending=False;self.tray=None;self.calibration_workstation=None
        self.running_settings=None;self.service=QProcess(self);self.service.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.service.readyReadStandardOutput.connect(self.read_log);self.service.finished.connect(self.service_finished)
        self.stop_timer=QTimer(self);self.stop_timer.setSingleShot(True);self.stop_timer.setInterval(20000);self.stop_timer.timeout.connect(self.force_stop)
        self.service.errorOccurred.connect(lambda error:self.message.setText('Service error: '+self.service.errorString()))
        self.setWindowTitle('CameraBridge Control Panel');self.setWindowIcon(camera_icon());self.resize(620,690)
        layout=QVBoxLayout(self);title=QLabel('CameraBridge');title.setStyleSheet('font-size:24px;font-weight:bold');layout.addWidget(title)
        self.message=QLabel('Stopped. Close this window to keep CameraBridge in the tray.');self.message.setWordWrap(True);layout.addWidget(self.message)
        form=QFormLayout();self.address=QLineEdit(self.settings.bind);form.addRow('Listen Address',self.address)
        self.port=QSpinBox();self.port.setRange(1024,65535);self.port.setValue(self.settings.port);form.addRow('HTTP Port',self.port)
        self.networks=QLineEdit(self.settings.trusted_hosts);form.addRow('Allowed Client Networks',self.networks)
        self.config=QLineEdit(self.settings.config_path or str(ROOT/'config.example.json'))
        config_row=QHBoxLayout();config_row.addWidget(self.config);browse=QPushButton('Browse');browse.clicked.connect(self.choose_config);config_row.addWidget(browse);form.addRow('Camera Configuration',config_row)
        layout.addLayout(form)
        self.lab=QCheckBox('Use camera simulators');self.lab.setChecked(self.settings.lab);self.lab.hide()
        self.visca=QCheckBox('Enable local VISCA lab');self.visca.setChecked(self.settings.visca);self.visca.hide()
        self.store=QCheckBox('Allow remote simulator shot stores');self.store.setChecked(self.settings.allow_store);self.store.hide()
        self.auto=QCheckBox('Start the service when CameraBridge opens');self.auto.setChecked(self.settings.auto_start);layout.addWidget(self.auto)
        actions=QHBoxLayout()
        for text,callback in [('Save and Restart',self.apply),('Start',self.start_service),('Stop',self.stop_service),('Open Setup Page',self.open_web)]:
            b=QPushButton(text);b.setMinimumHeight(36);b.clicked.connect(callback);actions.addWidget(b)
        layout.addLayout(actions)
        calibration_button=QPushButton('Open Video Calibration');calibration_button.clicked.connect(self.open_calibration);layout.addWidget(calibration_button)
        pending_button=QPushButton('Apply Saved Camera Setup');pending_button.clicked.connect(self.apply_pending);layout.addWidget(pending_button)
        account=QFormLayout();self.username=QLineEdit('admin');account.addRow('Local account',self.username)
        self.password=QLineEdit();self.password.setEchoMode(QLineEdit.EchoMode.Password);account.addRow('New password',self.password)
        self.repeat=QLineEdit();self.repeat.setEchoMode(QLineEdit.EchoMode.Password);account.addRow('Repeat password',self.repeat)
        layout.addLayout(account);save_account=QPushButton('Create or replace administrator account');save_account.clicked.connect(self.create_account);layout.addWidget(save_account)
        layout.addWidget(QLabel('Data: '+str(self.storage)))
        self.log=QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(200);layout.addWidget(self.log,1)
        quit_button=QPushButton('Quit CameraBridge');quit_button.clicked.connect(self.quit_app);layout.addWidget(quit_button)
        if create_tray:
            self.tray=QSystemTrayIcon(camera_icon(),self);self.tray.setToolTip('CameraBridge - stopped')
            menu=QMenu(self)
            for text,callback in [('Control Panel',self.show_panel),('Open Setup Page',self.open_web),('Open Video Calibration',self.open_calibration),('Start Service',self.start_service),('Stop Service',self.stop_service)]:
                action=QAction(text,self);action.triggered.connect(callback);menu.addAction(action)
            menu.addSeparator();action=QAction('Quit',self);action.triggered.connect(self.quit_app);menu.addAction(action)
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(lambda reason:self.show_panel() if reason in (QSystemTrayIcon.ActivationReason.Trigger,QSystemTrayIcon.ActivationReason.DoubleClick) else None)
            self.tray.show()
        if auto_start and self.settings.auto_start:QTimer.singleShot(0,self.start_service)
        self.config_timer=QTimer(self);self.config_timer.setInterval(500);self.config_timer.timeout.connect(self.check_restart_request);self.config_timer.start()

    def check_restart_request(self):
        request=self.storage/'desktop-restart.json'
        if request.exists():
            request.unlink();self.apply_pending()

    def apply_pending(self):
        import json
        pending=self.storage/'config.pending.json'
        try:
            from .server import validate_config
            config=validate_config(json.loads(pending.read_text(encoding='utf-8')))
            self.config.setText(str(pending));self.lab.setChecked(all(c.get('simulator') for c in config['cameras'] if c.get('enabled',True)))
            if not self.lab.isChecked() or config.get('pivotcam',{}).get('enabled'):self.visca.setChecked(False);self.store.setChecked(False)
            self.apply()
        except (ValueError,OSError) as error:self.message.setText('Cannot apply saved setup: '+str(error))

    def show_panel(self):
        # Reset Qt visibility when Windows initially launched the tray hidden.
        self.hide()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        screen=QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        if screen is not None:
            available=screen.availableGeometry()
            if not available.intersects(self.frameGeometry()) or not self.isVisible():
                self.move(available.center()-self.rect().center())
        self.show();self.showNormal();self.raise_();self.activateWindow()
        if self.windowHandle() is not None:self.windowHandle().requestActivate()
        QTimer.singleShot(100,self.raise_)

    def closeEvent(self,event):
        if self.tray and QSystemTrayIcon.isSystemTrayAvailable() and not self.quitting:self.hide();event.ignore()
        elif not self.quitting:event.ignore();self.quit_app()
        else:event.accept()

    def choose_config(self):
        path,_=QFileDialog.getOpenFileName(self,'Select camera configuration',self.config.text(),'JSON files (*.json)')
        if path:self.config.setText(path)

    def save_settings(self):
        settings=DesktopSettings(port=self.port.value(),bind=self.address.text().strip(),trusted_hosts=self.networks.text().strip(),
            lab=self.lab.isChecked(),visca=self.visca.isChecked(),allow_store=self.store.isChecked(),auto_start=self.auto.isChecked(),config_path=self.config.text())
        settings.prepare(self.storage);self.settings=settings;self.config.setText(settings.config_path)

    def apply(self):
        try:self.save_settings()
        except (ValueError,OSError) as error:self.message.setText(str(error));return
        self.restart_pending=True
        if self.service.state()!=QProcess.ProcessState.NotRunning:self.stop_service()
        else:self.restart_pending=False;self.start_service()

    def has_account(self):
        path=self.storage/'credentials.sqlite'
        if not path.exists():return False
        with closing(sqlite3.connect(path)) as db:return bool(db.execute('SELECT COUNT(*) FROM users').fetchone()[0])

    def start_service(self):
        if self.service.state()!=QProcess.ProcessState.NotRunning:return
        try:
            self.save_settings()
            if json.loads(pathlib.Path(self.settings.config_path).read_text(encoding='utf-8')).get('authentication_enabled',True) and not self.has_account():self.message.setText('Create a local administrator account before starting the service.');self.show_panel();return
        except (ValueError,OSError,sqlite3.Error) as error:self.message.setText(str(error));return
        if getattr(sys,'frozen',False):
            executable=pathlib.Path(sys.executable).with_name('CameraBridge-cli.exe' if sys.platform=='win32' else 'CameraBridge-cli')
            args=self.settings.service_args(self.storage)
        else:executable=pathlib.Path(sys.executable);args=[str(ROOT/'camerabridge.py')]+self.settings.service_args(self.storage)
        self.running_settings=DesktopSettings(**vars(self.settings))
        self.service.setProgram(str(executable));self.service.setArguments(args);self.service.start()
        self.message.setText('Starting '+self.running_settings.web_url())

    def read_log(self):
        text=bytes(self.service.readAllStandardOutput()).decode('utf-8',errors='replace').strip()
        if text:self.log.appendPlainText(text)
        if 'CameraBridge: http' in text:
            self.message.setText('Running at '+self.running_settings.web_url()+'. Close this panel to keep the service running.')
            if self.tray:self.tray.setToolTip('CameraBridge - '+self.running_settings.web_url())

    def stop_service(self):
        if self.service.state()==QProcess.ProcessState.NotRunning:return
        self.message.setText('Stopping the owned service and sending camera stop commands…')
        self.service.write(b'quit\n');self.service.closeWriteChannel()
        self.stop_timer.start()

    def force_stop(self):
        if self.service.state()!=QProcess.ProcessState.NotRunning:
            self.log.appendPlainText('Graceful stop timed out. Physical camera stop is unknown.');self.service.kill()

    def service_finished(self,*args):
        self.stop_timer.stop()
        self.read_log();self.message.setText('Stopped.')
        if self.tray:self.tray.setToolTip('CameraBridge - stopped')
        self.running_settings=None
        if self.quitting:
            if self.tray:self.tray.hide()
            QApplication.instance().quit()
        elif self.restart_pending:self.restart_pending=False;self.start_service()

    def open_web(self):
        settings=self.running_settings or self.settings
        if not QDesktopServices.openUrl(QUrl(settings.web_url())):self.message.setText('Open this address manually: '+settings.web_url())

    def open_calibration(self):
        try:
            if self.calibration_workstation is None:
                from .calibration_workstation import start
                self.calibration_workstation=start()
            url='http://127.0.0.1:'+str(self.calibration_workstation.server_address[1])+'/'
            if not QDesktopServices.openUrl(QUrl(url)):self.message.setText('Open calibration at '+url)
        except Exception as exc:self.message.setText('Cannot open video calibration: '+str(exc))

    def create_account(self):
        name=self.username.text().strip();password=self.password.text()
        if not name or not password or password!=self.repeat.text():self.message.setText('Enter an account name and matching non-empty passwords.');return
        auth=Auth(self.storage/'credentials.sqlite')
        with closing(sqlite3.connect(auth.path)) as db:exists=db.execute('SELECT 1 FROM users WHERE name=?',(name,)).fetchone()
        if exists and QMessageBox.question(self,'Replace account','Replace this administrator account?')!=QMessageBox.StandardButton.Yes:return
        auth.add(name,password,'admin');self.password.clear();self.repeat.clear();self.message.setText('Account saved. Start the service when ready.')

    def quit_app(self):
        if self.calibration_workstation is not None:
            try:self.calibration_workstation.close()
            except Exception:pass
            self.calibration_workstation=None
        self.quitting=True;self.restart_pending=False
        if self.service.state()!=QProcess.ProcessState.NotRunning:self.stop_service()
        else:
            if self.tray:self.tray.hide()
            QApplication.instance().quit()

def main():
    p=argparse.ArgumentParser(description='CameraBridge desktop tray application.');p.add_argument('--storage',default=str(default_storage()));p.add_argument('--open-calibration',action='store_true');a=p.parse_args(sys.argv[2:] if len(sys.argv)>1 and sys.argv[1]=='--tray' else sys.argv[1:])
    app=QApplication(sys.argv);app.setApplicationName('CameraBridge');app.setQuitOnLastWindowClosed(False)
    name='CameraBridge-'+hashlib.sha256(str(pathlib.Path(a.storage).resolve()).encode()).hexdigest()[:20]
    socket=QLocalSocket();socket.connectToServer(name)
    if socket.waitForConnected(300):socket.write(b'calibration' if a.open_calibration else b'show');socket.flush();socket.waitForBytesWritten(300);return
    server=QLocalServer();server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption);QLocalServer.removeServer(name)
    if not server.listen(name):raise SystemExit('Cannot create the desktop control socket.')
    panel=ControlPanel(a.storage)
    def activate():
        connection=server.nextPendingConnection()
        command=b''
        if connection:
            if not connection.bytesAvailable():connection.waitForReadyRead(300)
            command=bytes(connection.readAll());connection.close();connection.deleteLater()
        if command==b'calibration':panel.open_calibration()
        else:panel.show_panel()
    server.newConnection.connect(activate);panel.show_panel()
    if a.open_calibration:QTimer.singleShot(0,panel.open_calibration)
    app.exec();server.close()

if __name__=='__main__':main()
