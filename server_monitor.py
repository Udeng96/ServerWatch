#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, json, os
from datetime import datetime
import paramiko
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QFrame, QMessageBox, QStatusBar, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout,
    QTabWidget, QMenu
)
from PyQt5.QtCore  import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui   import QFont, QColor, QPalette

C = {
    "bg":"#0D1117","surface":"#161B22","surface2":"#1C2128",
    "border":"#2D333B","border2":"#373E47",
    "primary":"#58A6FF","primary_d":"#1F6FEB",
    "success":"#3FB950","warning":"#D29922","danger":"#F85149",
    "text":"#E6EDF3","text2":"#8B949E","text3":"#484F58","green":"#98c379",
}
SS = """
QMainWindow,QWidget{background:#0D1117;color:#E6EDF3;font-family:'Consolas','Noto Sans KR',monospace;font-size:13px;}
QFrame#card{background:#161B22;border:1px solid #2D333B;border-radius:8px;}
QLineEdit{background:#1C2128;border:1px solid #2D333B;border-radius:6px;padding:8px 12px;color:#E6EDF3;font-size:13px;}
QLineEdit:focus{border:1px solid #58A6FF;background:#0D1117;}
QPushButton{background:#1C2128;border:1px solid #2D333B;border-radius:6px;padding:8px 16px;color:#E6EDF3;font-weight:600;font-size:13px;}
QPushButton:hover{background:#2D333B;}
QPushButton:pressed{background:#0D1117;}
QPushButton#primary{background:#1F6FEB;border-color:#58A6FF;color:#fff;}
QPushButton#primary:hover{background:#58A6FF;}
QPushButton#primary:disabled{background:#2D333B;color:#484F58;border-color:#2D333B;}
QPushButton#danger{background:transparent;border-color:#F85149;color:#F85149;}
QPushButton#danger:hover{background:#F85149;color:white;}
QPushButton#success{background:transparent;border-color:#3FB950;color:#3FB950;}
QPushButton#success:hover{background:#3FB950;color:white;}
QListWidget{background:#161B22;border:1px solid #2D333B;border-radius:6px;outline:0;padding:4px;}
QListWidget::item{border-radius:4px;padding:10px 12px;margin:1px 2px;}
QListWidget::item:hover{background:#1C2128;}
QListWidget::item:selected{background:#1F6FEB;color:white;}
QTabWidget::pane{border:1px solid #2D333B;border-radius:6px;background:#161B22;}
QTabBar::tab{background:#1C2128;border:1px solid #2D333B;border-bottom:none;padding:8px 18px;margin-right:2px;border-top-left-radius:6px;border-top-right-radius:6px;color:#8B949E;font-weight:600;}
QTabBar::tab:selected{background:#161B22;color:#58A6FF;}
QTabBar::tab:hover:!selected{background:#2D333B;color:#E6EDF3;}
QTextEdit{background:#0a0e14;border:1px solid #2D333B;border-radius:6px;color:#98c379;font-family:'Consolas','Courier New',monospace;font-size:12px;padding:8px;}
QTableWidget{background:#161B22;border:1px solid #2D333B;border-radius:6px;gridline-color:#2D333B;outline:0;}
QTableWidget::item{padding:6px 12px;color:#E6EDF3;}
QTableWidget::item:selected{background:#1F6FEB;color:white;}
QHeaderView::section{background:#1C2128;border:none;border-bottom:1px solid #2D333B;padding:7px 12px;color:#8B949E;font-weight:700;font-size:11px;}
QScrollBar:vertical{background:transparent;width:6px;}
QScrollBar::handle:vertical{background:#373E47;border-radius:3px;min-height:20px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}
QScrollBar:horizontal{background:transparent;height:6px;}
QScrollBar::handle:horizontal{background:#373E47;border-radius:3px;}
QStatusBar{background:#161B22;border-top:1px solid #2D333B;color:#8B949E;font-size:12px;padding:0 8px;}
QProgressBar{background:#1C2128;border:1px solid #2D333B;border-radius:3px;height:8px;text-align:center;color:transparent;}
QProgressBar::chunk{background:#58A6FF;border-radius:3px;}
QFrame[frameShape="4"],QFrame[frameShape="5"]{color:#2D333B;}
"""
SAVE_FILE = os.path.expanduser("~/.server_monitor_hosts.json")

class SSHWorker(QThread):
    check_done = pyqtSignal(dict)
    cmd_done   = pyqtSignal(str)
    error      = pyqtSignal(str)
    def __init__(self, host, port, user, pwd, action="check", cmd=None):
        super().__init__()
        self.host=host; self.port=port; self.user=user; self.pwd=pwd
        self.action=action; self.cmd=cmd
    def run(self):
        try:
            cl = paramiko.SSHClient()
            cl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cl.connect(self.host, port=self.port, username=self.user,
                       password=self.pwd, timeout=10, allow_agent=False, look_for_keys=False)
            if self.action=="check": self._checks(cl)
            elif self.action=="cmd":
                out=self._exec(cl,self.cmd); cl.close(); self.cmd_done.emit(out)
        except Exception as e: self.error.emit(str(e))
    def _exec(self,cl,cmd):
        _,o,e=cl.exec_command(cmd,timeout=15)
        out=o.read().decode("utf-8",errors="replace").strip()
        err=e.read().decode("utf-8",errors="replace").strip()
        return out or err
    def _checks(self, cl):
        r={}
        r["hostname"]     = self._exec(cl,"hostname")
        r["ip"]           = self._exec(cl,"hostname -I | awk '{print $1}'")
        r["os"]           = self._exec(cl,"cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d= -f2 | tr -d '\"'")
        r["kernel"]       = self._exec(cl,"uname -r")
        # ① UPTIME
        r["uptime_pretty"]= self._exec(cl,"uptime -p 2>/dev/null || uptime")
        r["uptime_raw"]   = self._exec(cl,"uptime")
        r["load_1"]       = self._exec(cl,"cat /proc/loadavg | awk '{print $1}'")
        r["load_5"]       = self._exec(cl,"cat /proc/loadavg | awk '{print $2}'")
        r["load_15"]      = self._exec(cl,"cat /proc/loadavg | awk '{print $3}'")
        r["last_boot"]    = self._exec(cl,"who -b 2>/dev/null | awk '{print $3, $4}'")
        # ② TOP / CPU
        r["cpu_cores"]    = self._exec(cl,"nproc")
        r["cpu_model"]    = self._exec(cl,"cat /proc/cpuinfo 2>/dev/null | grep 'model name' | head -1 | cut -d: -f2 | xargs")
        r["top_output"]   = self._exec(cl,"top -bn1 2>/dev/null | head -25")
        idle=self._exec(cl,"top -bn1 2>/dev/null | grep -iE '%?Cpu' | head -1 | grep -oP '[0-9]+\\.?[0-9]*(?=\\s*id)' | head -1")
        try: r["cpu_usage"]=str(round(100-float(idle),1))
        except: r["cpu_usage"]="0"
        # ③ FREE -h
        r["free_output"]  = self._exec(cl,"free -h")
        r["mem_total_mb"] = self._exec(cl,"free -m | awk '/^Mem:/{print $2}'")
        r["mem_used_mb"]  = self._exec(cl,"free -m | awk '/^Mem:/{print $3}'")
        r["swap_total"]   = self._exec(cl,"free -h | awk '/^Swap:/{print $2}'")
        r["swap_used"]    = self._exec(cl,"free -h | awk '/^Swap:/{print $3}'")
        # ④ DF -h
        r["df_output"]    = self._exec(cl,"df -h")
        r["df_parsed"]    = self._exec(cl,"df -h | awk 'NR>1 && $1!=\"tmpfs\" && $1!=\"devtmpfs\" && $1!=\"udev\" && $6!=\"/dev\" && $6!=\"/sys\" && $6!=\"/proc\" {print $1\"|\"$2\"|\"$3\"|\"$4\"|\"$5\"|\"$6}'")
        # ⑤ ese@ 서비스 목록
        r["ese_services"] = self._exec(cl,
            "systemctl list-units 'ese@*' --no-pager --no-legend 2>/dev/null | awk '{print $1}' | sed 's/.service$//' "
            "|| systemctl list-unit-files 'ese@*' --no-pager --no-legend 2>/dev/null | awk '{print $1}' | sed 's/.service$//'"
        )
        # ⑥ postgresql 상세
        r["pg_status"]     = self._exec(cl, "systemctl is-active postgresql 2>/dev/null || systemctl is-active $(systemctl list-units 'postgresql*' --no-legend 2>/dev/null | awk '{print $1}' | head -1) 2>/dev/null || echo 'not-found'")
        r["pg_detail"]     = self._exec(cl, "systemctl status postgresql --no-pager 2>/dev/null || systemctl status $(systemctl list-units 'postgresql*' --no-legend 2>/dev/null | awk '{print $1}' | head -1) --no-pager 2>/dev/null | head -20 || echo ''")
        r["pg_version"]    = self._exec(cl, "psql --version 2>/dev/null | head -1 || echo ''")
        r["pg_path"]       = self._exec(cl, "which psql 2>/dev/null || find /usr /opt -name 'psql' -type f 2>/dev/null | head -1 || echo ''")
        r["pg_datadir"]    = self._exec(cl, "psql -U postgres -tAc 'SHOW data_directory;' 2>/dev/null || cat /etc/postgresql/*/main/postgresql.conf 2>/dev/null | grep '^data_directory' | head -1 || echo ''")
        r["pg_port"]       = self._exec(cl, "psql -U postgres -tAc 'SHOW port;' 2>/dev/null || grep '^port' /etc/postgresql/*/main/postgresql.conf 2>/dev/null | head -1 | awk '{print $3}' || echo '5432'")
        r["pg_confdir"]    = self._exec(cl, "find /etc/postgresql -name 'postgresql.conf' 2>/dev/null | head -1 || echo ''")
        # ⑦ nginx 상세
        r["nginx_status"]  = self._exec(cl, "systemctl is-active nginx 2>/dev/null || echo 'not-found'")
        r["nginx_detail"]  = self._exec(cl, "systemctl status nginx --no-pager 2>/dev/null | head -20 || echo ''")
        r["nginx_version"] = self._exec(cl, "nginx -v 2>&1 | head -1 || echo ''")
        r["nginx_path"]    = self._exec(cl, "which nginx 2>/dev/null || find /usr /opt /sbin -name 'nginx' -type f 2>/dev/null | head -1 || echo ''")
        r["nginx_confdir"] = self._exec(cl, "nginx -t 2>&1 | grep 'configuration file' | awk '{print $4}' || echo '/etc/nginx/nginx.conf'")
        r["nginx_webroot"] = self._exec(cl, "grep -r 'root ' /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ /etc/nginx/nginx.conf 2>/dev/null | grep -v '#' | head -3 | awk '{print $2}' | tr '\n' ' ' | sed 's/;//g' || echo ''")
        cl.close(); self.check_done.emit(r)

class GaugeCard(QFrame):
    def __init__(self, icon, title, cmd_hint=""):
        super().__init__(); self.setObjectName("card")
        lay=QVBoxLayout(self); lay.setContentsMargins(18,14,18,14); lay.setSpacing(8)
        hdr=QHBoxLayout()
        li=QLabel(icon); li.setStyleSheet("font-size:18px;")
        lt=QLabel(title); lt.setFont(QFont("Consolas",11,QFont.Bold)); lt.setStyleSheet("color:#8B949E;letter-spacing:1px;")
        lc=QLabel(cmd_hint); lc.setStyleSheet("color:#484F58;font-size:10px;font-family:Consolas;")
        hdr.addWidget(li); hdr.addWidget(lt); hdr.addStretch(); hdr.addWidget(lc); lay.addLayout(hdr)
        self.lbl_val=QLabel("─"); self.lbl_val.setFont(QFont("Consolas",30,QFont.Bold)); self.lbl_val.setStyleSheet("color:#58A6FF;")
        lay.addWidget(self.lbl_val)
        self.bar=QProgressBar(); self.bar.setRange(0,100); self.bar.setValue(0); self.bar.setFixedHeight(6); self.bar.setTextVisible(False)
        lay.addWidget(self.bar)
        self.lbl_sub=QLabel("─"); self.lbl_sub.setStyleSheet("color:#8B949E;font-size:11px;"); self.lbl_sub.setWordWrap(True)
        lay.addWidget(self.lbl_sub)
    def _color(self,pct): return "#3FB950" if pct<70 else ("#D29922" if pct<90 else "#F85149")
    def set_value(self, pct, main, sub=""):
        self.lbl_val.setText(main); c=self._color(pct); self.lbl_val.setStyleSheet(f"color:{c};")
        self.bar.setValue(pct)
        self.bar.setStyleSheet(f"QProgressBar{{background:#1C2128;border:1px solid #2D333B;border-radius:3px;}}QProgressBar::chunk{{background:{c};border-radius:3px;}}")
        self.lbl_sub.setText(sub)
    def set_uptime(self, pretty, load, last_boot):
        txt=pretty.replace("up ","").strip() or pretty
        self.lbl_val.setText(txt); self.lbl_val.setStyleSheet("color:#3FB950;")
        self.bar.setVisible(False)
        self.lbl_sub.setText(f"로드 평균: {load}  |  마지막 부팅: {last_boot}")

class ConnectPanel(QFrame):
    do_connect=pyqtSignal(dict)
    def __init__(self):
        super().__init__(); self.setObjectName("card"); self._build()
    def _build(self):
        lay=QVBoxLayout(self); lay.setContentsMargins(20,20,20,20); lay.setSpacing(14)
        hdr=QHBoxLayout(); icon=QLabel("⚡"); icon.setStyleSheet("font-size:20px;")
        title=QLabel("SSH 연결"); title.setFont(QFont("Consolas",14,QFont.Bold))
        hdr.addWidget(icon); hdr.addWidget(title); hdr.addStretch(); lay.addLayout(hdr)
        sep=QFrame(); sep.setFrameShape(QFrame.HLine); lay.addWidget(sep)
        def mk(lbl,ph,pwd=False):
            l=QLabel(lbl); l.setFont(QFont("Consolas",10,QFont.Bold)); l.setStyleSheet("color:#8B949E;letter-spacing:1px;")
            f=QLineEdit(); f.setPlaceholderText(ph); f.setFixedHeight(38)
            if pwd: f.setEchoMode(QLineEdit.Password)
            return l,f
        l,self.f_name=mk("서버 이름 (별칭)","예: web-prod-01"); lay.addWidget(l); lay.addWidget(self.f_name)
        row=QHBoxLayout(); row.setSpacing(8)
        iv=QVBoxLayout(); iv.setSpacing(4)
        li=QLabel("IP 주소"); li.setFont(QFont("Consolas",10,QFont.Bold)); li.setStyleSheet("color:#8B949E;")
        self.f_ip=QLineEdit(); self.f_ip.setPlaceholderText("198.51.100.1"); self.f_ip.setFixedHeight(38)
        iv.addWidget(li); iv.addWidget(self.f_ip)
        pv=QVBoxLayout(); pv.setSpacing(4)
        lp=QLabel("포트"); lp.setFont(QFont("Consolas",10,QFont.Bold)); lp.setStyleSheet("color:#8B949E;")
        self.f_port=QLineEdit(); self.f_port.setText("22"); self.f_port.setFixedHeight(38); self.f_port.setFixedWidth(72)
        pv.addWidget(lp); pv.addWidget(self.f_port)
        row.addLayout(iv); row.addLayout(pv); lay.addLayout(row)
        l,self.f_user=mk("사용자명","root"); lay.addWidget(l); lay.addWidget(self.f_user)
        lp2,self.f_pwd=mk("비밀번호","••••••••",pwd=True)
        pr=QHBoxLayout(); pr.setSpacing(6); pr.addWidget(self.f_pwd)
        self.btn_eye=QPushButton("👁"); self.btn_eye.setFixedSize(38,38); self.btn_eye.clicked.connect(self._toggle)
        pr.addWidget(self.btn_eye); lay.addWidget(lp2); lay.addLayout(pr)
        lay.addSpacing(4)
        self.btn_c=QPushButton("  🔌  연 결"); self.btn_c.setObjectName("primary"); self.btn_c.setFixedHeight(44)
        self.btn_c.setFont(QFont("Consolas",13,QFont.Bold)); self.btn_c.clicked.connect(self._go); self.btn_c.setShortcut("Return")
        lay.addWidget(self.btn_c)
        self.lbl_msg=QLabel(""); self.lbl_msg.setAlignment(Qt.AlignCenter); self.lbl_msg.setWordWrap(True)
        lay.addWidget(self.lbl_msg); lay.addStretch()
    def _toggle(self):
        if self.f_pwd.echoMode()==QLineEdit.Password: self.f_pwd.setEchoMode(QLineEdit.Normal); self.btn_eye.setText("🔒")
        else: self.f_pwd.setEchoMode(QLineEdit.Password); self.btn_eye.setText("👁")
    def _go(self):
        host=self.f_ip.text().strip(); user=self.f_user.text().strip()
        pwd=self.f_pwd.text(); name=self.f_name.text().strip() or host
        try: port=int(self.f_port.text())
        except: self._msg("포트가 올바르지 않습니다.","err"); return
        if not host: self._msg("IP를 입력하세요.","err"); return
        if not user: self._msg("사용자명을 입력하세요.","err"); return
        if not pwd:  self._msg("비밀번호를 입력하세요.","err"); return
        self.btn_c.setEnabled(False); self.btn_c.setText("  ⏳  연결 중..."); self._msg("연결 중...","info")
        self.do_connect.emit({"name":name,"host":host,"port":port,"user":user,"pwd":pwd})
    def set_done(self,ok,msg=""):
        self.btn_c.setEnabled(True); self.btn_c.setText("  🔌  연 결"); self._msg(msg,"ok" if ok else "err")
    def _msg(self,t,lv):
        col={"ok":"#3FB950","err":"#F85149","info":"#8B949E"}.get(lv,"#8B949E")
        self.lbl_msg.setText(t); self.lbl_msg.setStyleSheet(f"color:{col};font-size:12px;")
    def fill(self,d):
        self.f_name.setText(d.get("name","")); self.f_ip.setText(d.get("host",""))
        self.f_port.setText(str(d.get("port",22))); self.f_user.setText(d.get("user","")); self.f_pwd.setText(d.get("pwd",""))

class ResultPanel(QFrame):
    do_recheck=pyqtSignal(); do_cmd=pyqtSignal(str); do_disconnect=pyqtSignal(); do_ese_check=pyqtSignal(list)
    def __init__(self):
        super().__init__(); self.setObjectName("card"); self._build()
    def _build(self):
        lay=QVBoxLayout(self); lay.setContentsMargins(20,18,20,18); lay.setSpacing(14)
        hdr=QHBoxLayout()
        self.lbl_svr=QLabel("서버를 선택하세요"); self.lbl_svr.setFont(QFont("Consolas",15,QFont.Bold))
        self.badge=QLabel("OFFLINE"); self._badge(False)
        self.lbl_inf=QLabel(""); self.lbl_inf.setStyleSheet("color:#484F58;font-size:11px;")
        hdr.addWidget(self.lbl_svr); hdr.addSpacing(8); hdr.addWidget(self.badge)
        hdr.addSpacing(12); hdr.addWidget(self.lbl_inf); hdr.addStretch()
        br=QPushButton("🔄 재점검"); br.clicked.connect(self.do_recheck.emit)
        bd=QPushButton("연결 해제"); bd.setObjectName("danger"); bd.clicked.connect(self.do_disconnect.emit)
        hdr.addWidget(br); hdr.addWidget(bd); lay.addLayout(hdr)
        sep=QFrame(); sep.setFrameShape(QFrame.HLine); lay.addWidget(sep)
        tabs=QTabWidget(); lay.addWidget(tabs)
        # 대시보드
        dash=QWidget(); tabs.addTab(dash,"  대시보드")
        dl=QVBoxLayout(dash); dl.setContentsMargins(12,12,12,12); dl.setSpacing(12)
        grid=QGridLayout(); grid.setSpacing(12)
        self.card_up  =GaugeCard("⏱","UPTIME","uptime")
        self.card_cpu =GaugeCard("🔥","CPU","top -bn1")
        self.card_mem =GaugeCard("🧠","MEMORY","free -h")
        self.card_disk=GaugeCard("💾","DISK  /","df -h")
        grid.addWidget(self.card_up,0,0); grid.addWidget(self.card_cpu,0,1)
        grid.addWidget(self.card_mem,1,0); grid.addWidget(self.card_disk,1,1)
        dl.addLayout(grid)
        # 원본 출력
        raw=QWidget(); tabs.addTab(raw,"  원본 출력")
        rl=QVBoxLayout(raw); rl.setContentsMargins(12,12,12,12)
        rt=QTabWidget(); rl.addWidget(rt)
        self.txt_up=self._term(); self.txt_top=self._term()
        self.txt_free=self._term(); self.txt_df=self._term()
        for n,w in [("uptime",self.txt_up),("top -bn1",self.txt_top),("free -h",self.txt_free),("df -h",self.txt_df)]:
            wg=QWidget(); wl=QVBoxLayout(wg); wl.setContentsMargins(0,8,0,0); wl.addWidget(w); rt.addTab(wg,n)
        # 디스크 상세
        dt=QWidget(); tabs.addTab(dt,"  디스크 상세")
        dtl=QVBoxLayout(dt); dtl.setContentsMargins(12,12,12,12)
        self.disk_tbl=QTableWidget(0,6)
        self.disk_tbl.setHorizontalHeaderLabels(["파일시스템","전체","사용","여유","사용%","마운트"])
        self.disk_tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disk_tbl.verticalHeader().setVisible(False)
        self.disk_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.disk_tbl.setSelectionBehavior(QTableWidget.SelectRows); self.disk_tbl.setShowGrid(False)
        dtl.addWidget(self.disk_tbl)

        # 서비스 상태
        sv=QWidget(); tabs.addTab(sv,"  서비스 상태")
        svl=QVBoxLayout(sv); svl.setContentsMargins(12,12,12,12); svl.setSpacing(8)
        # ese@ 서비스 자동 조회 배너
        ese_banner=QHBoxLayout(); ese_banner.setSpacing(8)
        ese_icon=QLabel("⚙️"); ese_icon.setStyleSheet("font-size:16px;")
        ese_lbl=QLabel("ese@ 서비스"); ese_lbl.setFont(QFont("Consolas",11,QFont.Bold)); ese_lbl.setStyleSheet("color:#58A6FF;")
        ese_sub=QLabel("연결 시 자동으로 감지됩니다"); ese_sub.setStyleSheet("color:#484F58;font-size:11px;")
        self.btn_ese=QPushButton("🔄 ese@ 전체 점검"); self.btn_ese.setObjectName("primary"); self.btn_ese.setFixedHeight(34)
        self.btn_ese.clicked.connect(self._check_ese_all)
        self.btn_clr_tbl=QPushButton("테이블 초기화"); self.btn_clr_tbl.setFixedHeight(34)
        self.btn_clr_tbl.clicked.connect(lambda: self.svc_tbl.setRowCount(0))
        ese_banner.addWidget(ese_icon); ese_banner.addWidget(ese_lbl); ese_banner.addWidget(ese_sub)
        ese_banner.addStretch(); ese_banner.addWidget(self.btn_ese); ese_banner.addWidget(self.btn_clr_tbl)
        svl.addLayout(ese_banner)
        sep_ese=QFrame(); sep_ese.setFrameShape(QFrame.HLine); svl.addWidget(sep_ese)
        sc=QHBoxLayout(); sc.setSpacing(8)
        self.svc_in=QLineEdit(); self.svc_in.setPlaceholderText("예: nginx  apache2  mysql  sshd  docker ..."); self.svc_in.setFixedHeight(36)
        self.svc_in.returnPressed.connect(self._check_svc)
        sb2=QPushButton("🔍 확인"); sb2.setObjectName("primary"); sb2.setFixedHeight(36); sb2.clicked.connect(self._check_svc)
        sb3=QPushButton("실행중 전체"); sb3.setFixedHeight(36)
        sb3.clicked.connect(lambda: self.do_cmd.emit("systemctl list-units --type=service --state=running --no-pager 2>/dev/null || service --status-all 2>&1"))
        sb4=QPushButton("실패 서비스"); sb4.setObjectName("danger"); sb4.setFixedHeight(36)
        sb4.clicked.connect(lambda: self.do_cmd.emit("systemctl --failed --no-pager 2>/dev/null"))
        sc.addWidget(self.svc_in); sc.addWidget(sb2); sc.addWidget(sb3); sc.addWidget(sb4)
        svl.addLayout(sc)
        ql2=QLabel("자주 쓰는 서비스"); ql2.setFont(QFont("Consolas",10,QFont.Bold)); ql2.setStyleSheet("color:#8B949E;"); svl.addWidget(ql2)
        qr2=QHBoxLayout(); qr2.setSpacing(6)
        for sn in ["nginx","postgresql"]:
            b=QPushButton(sn); b.setFixedHeight(28)
            b.setStyleSheet("QPushButton{background:#1C2128;border:1px solid #373E47;border-radius:4px;color:#8B949E;font-size:11px;padding:0 10px;}QPushButton:hover{color:#E6EDF3;border-color:#58A6FF;}")
            b.clicked.connect(lambda _,s=sn:(self.svc_in.setText(s),self._check_svc()))
            qr2.addWidget(b)
        qr2.addStretch(); svl.addLayout(qr2)
        sep_sv=QFrame(); sep_sv.setFrameShape(QFrame.HLine); svl.addWidget(sep_sv)
        rl2=QLabel("결과"); rl2.setFont(QFont("Consolas",10,QFont.Bold)); rl2.setStyleSheet("color:#8B949E;"); svl.addWidget(rl2)
        self.svc_tbl=QTableWidget(0,3)
        self.svc_tbl.setHorizontalHeaderLabels(["서비스","상태","상세"])
        self.svc_tbl.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeToContents)
        self.svc_tbl.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeToContents)
        self.svc_tbl.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)
        self.svc_tbl.verticalHeader().setVisible(False)
        self.svc_tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.svc_tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.svc_tbl.setShowGrid(False)
        svl.addWidget(self.svc_tbl,1)
        rl3=QLabel("원본 출력"); rl3.setFont(QFont("Consolas",10,QFont.Bold)); rl3.setStyleSheet("color:#8B949E;"); svl.addWidget(rl3)
        self.svc_out=self._term(); self.svc_out.setMaximumHeight(160); svl.addWidget(self.svc_out)
        # 명령 실행
        ct=QWidget(); tabs.addTab(ct,"  명령 실행")
        cl=QVBoxLayout(ct); cl.setContentsMargins(12,12,12,12); cl.setSpacing(8)
        lc=QLabel("명령어"); lc.setFont(QFont("Consolas",10,QFont.Bold)); lc.setStyleSheet("color:#8B949E;"); cl.addWidget(lc)
        cr=QHBoxLayout(); cr.setSpacing(8)
        self.cmd_in=QLineEdit(); self.cmd_in.setPlaceholderText("명령어 입력..."); self.cmd_in.setFixedHeight(38)
        br2=QPushButton("▶  실행"); br2.setObjectName("success"); br2.setFixedHeight(38)
        br2.clicked.connect(self._run); self.cmd_in.returnPressed.connect(self._run)
        cr.addWidget(self.cmd_in); cr.addWidget(br2); cl.addLayout(cr)
        ql=QLabel("빠른 명령"); ql.setFont(QFont("Consolas",10,QFont.Bold)); ql.setStyleSheet("color:#8B949E;"); cl.addWidget(ql)
        qr=QHBoxLayout(); qr.setSpacing(6)
        quick=[("⏱ uptime","uptime"),("🔥 top (1회)","top -bn1 | head -20"),
               ("🧠 free -h","free -h"),("💾 df -h","df -h"),
               ("🔍 ps (메모리순)","ps aux --sort=-%mem | head -15"),("🌐 netstat","ss -tlnp")]
        for nm,cmd in quick:
            b=QPushButton(nm); b.setFixedHeight(30)
            b.setStyleSheet("QPushButton{background:#1C2128;border:1px solid #373E47;border-radius:4px;color:#8B949E;font-size:11px;padding:0 10px;}QPushButton:hover{color:#E6EDF3;border-color:#58A6FF;}")
            b.clicked.connect(lambda _,c=cmd:(self.cmd_in.setText(c),self._run()))
            qr.addWidget(b)
        qr.addStretch(); cl.addLayout(qr)
        ol=QLabel("출력"); ol.setFont(QFont("Consolas",10,QFont.Bold)); ol.setStyleSheet("color:#8B949E;"); cl.addWidget(ol)
        self.cmd_out=self._term(); cl.addWidget(self.cmd_out)
        clr=QHBoxLayout(); clr.addStretch(); bc=QPushButton("지우기"); bc.setFixedHeight(28); bc.clicked.connect(self.cmd_out.clear); clr.addWidget(bc); cl.addLayout(clr)
    def _term(self): t=QTextEdit(); t.setReadOnly(True); return t
    def _badge(self, online):
        if online:
            self.badge.setText("ONLINE"); self.badge.setStyleSheet("color:#3FB950;background:rgba(63,185,80,0.12);border:1px solid rgba(63,185,80,0.4);border-radius:10px;padding:2px 10px;font-size:11px;font-weight:700;")
        else:
            self.badge.setText("OFFLINE"); self.badge.setStyleSheet("color:#F85149;background:rgba(248,81,73,0.12);border:1px solid rgba(248,81,73,0.4);border-radius:10px;padding:2px 10px;font-size:11px;font-weight:700;")
    def set_online(self,name,info=""): self.lbl_svr.setText(name); self._badge(True); self.lbl_inf.setText(info)
    def set_offline(self): self._badge(False)
    def update_data(self, d):
        up=d.get("uptime_pretty","─").replace("up ","").strip() or d.get("uptime_raw","─")
        load=f"{d.get('load_1','?')} / {d.get('load_5','?')} / {d.get('load_15','?')}"
        self.card_up.set_uptime(up,load,d.get("last_boot","─"))
        self.txt_up.setPlainText(f"$ uptime\n{d.get('uptime_raw','─')}\n\nLoad Average (1m/5m/15m): {load}")
        try: cpu_pct=round(float(d.get("cpu_usage","0") or "0"))
        except: cpu_pct=0
        self.card_cpu.set_value(cpu_pct,f"{cpu_pct}%",f"코어: {d.get('cpu_cores','─')}  |  {d.get('cpu_model','─')}")
        self.txt_top.setPlainText(f"$ top -bn1\n{d.get('top_output','─')}")
        try:
            mt=int(d.get("mem_total_mb","0") or "0"); mu=int(d.get("mem_used_mb","0") or "0")
            mem_pct=int(mu/mt*100) if mt else 0
        except: mem_pct=0
        fh=d.get("free_output","─")
        try: ml=[l for l in fh.splitlines() if l.startswith("Mem:")][0].split(); mem_disp=f"{ml[2]} / {ml[1]}"
        except: mem_disp=f"{d.get('mem_used_mb','?')}MB / {d.get('mem_total_mb','?')}MB"
        self.card_mem.set_value(mem_pct,f"{mem_pct}%",f"사용: {mem_disp}  |  Swap: {d.get('swap_used','─')} / {d.get('swap_total','─')}")
        self.txt_free.setPlainText(f"$ free -h\n{fh}")
        df_raw=d.get("df_parsed",""); root_pct=0; root_sub="─"
        for line in df_raw.splitlines():
            pts=line.split("|")
            if len(pts)==6 and pts[5].strip()=="/":
                try: root_pct=int(pts[4].replace("%","").strip())
                except: root_pct=0
                root_sub=f"사용: {pts[2].strip()} / {pts[1].strip()}  |  여유: {pts[3].strip()}"; break
        self.card_disk.set_value(root_pct,f"{root_pct}%",root_sub)
        self.txt_df.setPlainText(f"$ df -h\n{d.get('df_output','─')}")
        rows=[l.split("|") for l in df_raw.splitlines() if l.count("|")==5]
        self.disk_tbl.setRowCount(len(rows))
        for i,cols in enumerate(rows):
            for j,val in enumerate(cols):
                item=QTableWidgetItem(val.strip()); item.setTextAlignment(Qt.AlignCenter)
                if j==4:
                    try:
                        p=int(val.replace("%","").strip())
                        col="#3FB950" if p<70 else ("#D29922" if p<90 else "#F85149")
                        item.setForeground(QColor(col)); item.setFont(QFont("Consolas",12,QFont.Bold))
                    except: pass
                self.disk_tbl.setItem(i,j,item)
            self.disk_tbl.setRowHeight(i,34)

    def set_common_services(self, d: dict):
        """postgresql / nginx 상태를 테이블 상단에 고정 표시 + 상세 정보 패널"""
        # 기존 common 행 제거
        for row in reversed(range(self.svc_tbl.rowCount())):
            item = self.svc_tbl.item(row, 0)
            if item and item.text().strip() in ("postgresql", "nginx"):
                self.svc_tbl.removeRow(row)

        services = [
            {
                "name":    "postgresql",
                "status":  d.get("pg_status", "").strip(),
                "version": d.get("pg_version", ""),
                "path":    d.get("pg_path", ""),
                "extra":   [
                    ("포트",       d.get("pg_port",    "")),
                    ("설정 파일",  d.get("pg_confdir", "")),
                    ("데이터 경로",d.get("pg_datadir", "")),
                ],
                "detail":  d.get("pg_detail", ""),
            },
            {
                "name":    "nginx",
                "status":  d.get("nginx_status", "").strip(),
                "version": d.get("nginx_version", ""),
                "path":    d.get("nginx_path", ""),
                "extra":   [
                    ("설정 파일",  d.get("nginx_confdir", "")),
                    ("웹 루트",   d.get("nginx_webroot",  "")),
                ],
                "detail":  d.get("nginx_detail", ""),
            },
        ]

        for idx, svc in enumerate(services):
            name   = svc["name"]
            status = svc["status"].lower() if svc["status"] else "not-found"
            ver    = svc["version"].strip()
            path   = svc["path"].strip()

            # ── 서비스명 열
            ni = QTableWidgetItem(f"  {name}")
            ni.setFont(QFont("Consolas", 11, QFont.Bold))

            # ── 상태 열
            if status in ("", "not-found", "not installed"):
                label = "서비스 없음"
                color = "#484F58"
            elif status == "active":
                label = "RUNNING"; color = "#3FB950"
            elif status in ("exited", "reloading"):
                label = "EXITED";  color = "#D29922"
            elif status == "inactive":
                label = "INACTIVE"; color = "#8B949E"
            elif status == "failed":
                label = "FAILED";  color = "#F85149"
            else:
                label = status.upper(); color = "#8B949E"

            si = QTableWidgetItem(label)
            si.setForeground(QColor(color))
            si.setFont(QFont("Consolas", 11, QFont.Bold))

            # ── 상세 열: 버전 + 경로
            parts = []
            if ver:   parts.append(ver)
            if path:  parts.append(f"경로: {path}")
            for k, v in svc["extra"]:
                if v and v.strip(): parts.append(f"{k}: {v.strip()}")
            sub = "  │  ".join(parts) if parts else ("설치되지 않음" if label == "서비스 없음" else "")

            di = QTableWidgetItem(sub)
            di.setForeground(QColor("#8B949E"))

            self.svc_tbl.insertRow(idx)
            self.svc_tbl.setItem(idx, 0, ni)
            self.svc_tbl.setItem(idx, 1, si)
            self.svc_tbl.setItem(idx, 2, di)
            self.svc_tbl.setRowHeight(idx, 36)

            # 원본 상세 출력
            if svc["detail"]:
                self.svc_out.append(
                    f"\n─── {name} ────────────────────────\n{svc['detail']}"
                )
    def _check_ese_all(self):
        names = getattr(self, "_ese_names", [])
        if not names:
            self.do_cmd.emit("systemctl list-units 'ese@*' --no-pager 2>/dev/null")
            return
        self.do_ese_check.emit(names)
    def _check_svc(self):
        svc = self.svc_in.text().strip()
        if not svc: return
        self.do_cmd.emit(f"systemctl status {svc} --no-pager 2>/dev/null || service {svc} status 2>&1")
        # 테이블에 즉시 반영 (상태는 cmd_done 으로 별도 파싱)
        # worker 가 끝나면 update_svc_table 호출됨
        self._pending_svc = svc
    def update_svc_table(self, svc: str, raw: str):
        """systemctl status 출력을 파싱해서 테이블에 추가"""
        active = "unknown"; sub = ""
        for line in raw.splitlines():
            ll = line.strip().lower()
            if "active:" in ll:
                rest = line.split(":",1)[1].strip() if ":" in line else line
                if "active (running)" in ll:   active = "running"
                elif "active (exited)" in ll:  active = "exited"
                elif "inactive" in ll:          active = "inactive"
                elif "failed" in ll:            active = "failed"
                sub = rest[:80]
                break
        row = self.svc_tbl.rowCount(); self.svc_tbl.insertRow(row)
        ni = QTableWidgetItem(svc); ni.setFont(QFont("Consolas",11,QFont.Bold))
        si = QTableWidgetItem(active.upper())
        color = {"running":"#3FB950","exited":"#D29922","inactive":"#8B949E","failed":"#F85149"}.get(active,"#8B949E")
        si.setForeground(QColor(color)); si.setFont(QFont("Consolas",11,QFont.Bold))
        di = QTableWidgetItem(sub); di.setForeground(QColor("#8B949E"))
        self.svc_tbl.setItem(row,0,ni); self.svc_tbl.setItem(row,1,si); self.svc_tbl.setItem(row,2,di)
        self.svc_tbl.setRowHeight(row,34)
        self.svc_out.setPlainText(f"$ systemctl status {svc}\n{raw}")
    def set_ese_services(self, ese_raw: str):
        """연결 직후 ese@ 서비스 목록을 받아 테이블에 표시"""
        names = [n.strip() for n in ese_raw.splitlines() if n.strip() and "ese@" in n.strip()]
        if not names:
            return
        self.svc_tbl.setRowCount(0)
        self._ese_names = names
        self.btn_ese.setText(f"🔄 ese@ 전체 점검 ({len(names)}개)")
        # 이름만 먼저 채워놓기 (상태는 점검 시 갱신)
        for nm in names:
            row = self.svc_tbl.rowCount(); self.svc_tbl.insertRow(row)
            ni = QTableWidgetItem(nm); ni.setFont(QFont("Consolas",11,QFont.Bold))
            si = QTableWidgetItem("─"); si.setForeground(QColor("#484F58")); si.setFont(QFont("Consolas",11,QFont.Bold))
            di = QTableWidgetItem("점검 전")
            self.svc_tbl.setItem(row,0,ni); self.svc_tbl.setItem(row,1,si); self.svc_tbl.setItem(row,2,di)
            self.svc_tbl.setRowHeight(row,34)

    def _run(self):
        cmd=self.cmd_in.text().strip()
        if cmd: self.do_cmd.emit(cmd)
    def append_cmd(self,text):
        ts=datetime.now().strftime("%H:%M:%S")
        self.cmd_out.append(f"<span style='color:#484F58'>[{ts}]</span>")
        self.cmd_out.append(f"<span style='color:#98c379'>{text}</span><br>")

class ServerItem(QWidget):
    def __init__(self,name,host):
        super().__init__()
        lay=QHBoxLayout(self); lay.setContentsMargins(4,2,4,2); lay.setSpacing(10)
        self.dot=QLabel("●"); self.dot.setFixedWidth(14); self.set_status("offline")
        col=QVBoxLayout(); col.setSpacing(1)
        n=QLabel(name); n.setFont(QFont("Consolas",12,QFont.Bold))
        h=QLabel(host); h.setStyleSheet("color:#484F58;font-size:11px;")
        col.addWidget(n); col.addWidget(h)
        lay.addWidget(self.dot); lay.addLayout(col); lay.addStretch()
    def set_status(self,s):
        col={"online":"#3FB950","offline":"#484F58","error":"#F85149"}.get(s,"#484F58")
        self.dot.setStyleSheet(f"color:{col};font-size:10px;")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.servers=[]; self.active_info=None
        self._load(); self._ui(); self._refresh_list()
    def _load(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE) as f: self.servers=json.load(f)
            except: pass
    def _save(self):
        with open(SAVE_FILE,"w",encoding="utf-8") as f: json.dump(self.servers,f,ensure_ascii=False,indent=2)
    def _ui(self):
        self.setWindowTitle("서버 점검 도구"); self.setMinimumSize(1200,750); self.resize(1440,860)
        cw=QWidget(); self.setCentralWidget(cw)
        root=QHBoxLayout(cw); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sb=QFrame(); sb.setFixedWidth(260); sb.setStyleSheet("QFrame{background:#161B22;border-right:1px solid #2D333B;}")
        sl=QVBoxLayout(sb); sl.setContentsMargins(14,16,14,16); sl.setSpacing(12)
        lr=QHBoxLayout(); li=QLabel("🖥️"); li.setStyleSheet("font-size:22px;")
        lt=QLabel("ServerWatch"); lt.setFont(QFont("Consolas",14,QFont.Bold)); lt.setStyleSheet("color:#58A6FF;")
        lr.addWidget(li); lr.addWidget(lt); lr.addStretch(); sl.addLayout(lr)
        sub=QLabel("내부망 SSH 점검 도구"); sub.setStyleSheet("color:#484F58;font-size:11px;"); sl.addWidget(sub)
        s1=QFrame(); s1.setFrameShape(QFrame.HLine); sl.addWidget(s1)
        lh=QHBoxLayout()
        ll=QLabel("서버 목록"); ll.setFont(QFont("Consolas",10,QFont.Bold)); ll.setStyleSheet("color:#8B949E;letter-spacing:1px;")
        ba=QPushButton("+"); ba.setFixedSize(26,26); ba.clicked.connect(self._new)
        lh.addWidget(ll); lh.addStretch(); lh.addWidget(ba); sl.addLayout(lh)
        self.srv_list=QListWidget()
        self.srv_list.itemClicked.connect(self._select)
        self.srv_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.srv_list.customContextMenuRequested.connect(self._ctx)
        sl.addWidget(self.srv_list,1)
        s2=QFrame(); s2.setFrameShape(QFrame.HLine); sl.addWidget(s2)
        self.lbl_clk=QLabel(); self.lbl_clk.setAlignment(Qt.AlignCenter); self.lbl_clk.setStyleSheet("color:#484F58;font-size:11px;font-family:Consolas;")
        sl.addWidget(self.lbl_clk)
        t=QTimer(self); t.timeout.connect(self._tick); t.start(1000); self._tick()
        root.addWidget(sb)
        ma=QWidget(); ml=QHBoxLayout(ma); ml.setContentsMargins(16,16,16,16); ml.setSpacing(16)
        self.conn=ConnectPanel(); self.conn.setFixedWidth(320); self.conn.do_connect.connect(self._connect); ml.addWidget(self.conn)
        self.res=ResultPanel()
        self.res.do_recheck.connect(self._recheck); self.res.do_cmd.connect(self._run_cmd); self.res.do_disconnect.connect(self._disconnect)
        self.res.do_ese_check.connect(self._check_ese_services)
        ml.addWidget(self.res,1); root.addWidget(ma,1)
        self.statusBar().showMessage("준비 완료 — 서버에 연결하세요.")
    def _tick(self): self.lbl_clk.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
    def _refresh_list(self):
        self.srv_list.clear()
        for s in self.servers:
            item=QListWidgetItem(); w=ServerItem(s["name"],f"{s['host']}:{s['port']}")
            item.setSizeHint(QSize(0,54)); self.srv_list.addItem(item); self.srv_list.setItemWidget(item,w)
    def _new(self):
        for f in [self.conn.f_name,self.conn.f_ip,self.conn.f_user,self.conn.f_pwd]: f.clear()
        self.conn.f_port.setText("22"); self.active_info=None; self.srv_list.clearSelection()
    def _select(self,item):
        idx=self.srv_list.row(item)
        if 0<=idx<len(self.servers): self.conn.fill(self.servers[idx])
    def _ctx(self,pos):
        item=self.srv_list.itemAt(pos)
        if not item: return
        idx=self.srv_list.row(item)
        m=QMenu(self)
        m.setStyleSheet("QMenu{background:#1C2128;border:1px solid #2D333B;border-radius:6px;padding:4px;color:#E6EDF3;}QMenu::item{padding:6px 20px;border-radius:4px;}QMenu::item:selected{background:#1F6FEB;}")
        ac=m.addAction("🔌 연결 & 점검"); m.addSeparator(); ad=m.addAction("🗑 삭제")
        act=m.exec_(self.srv_list.viewport().mapToGlobal(pos))
        if act==ad: self.servers.pop(idx); self._save(); self._refresh_list()
        elif act==ac: self._select(item); self.conn._go()
    def _connect(self,info):
        self.active_info=info; self.statusBar().showMessage(f"[{info['host']}] 연결 중...")
        w=SSHWorker(info["host"],info["port"],info["user"],info["pwd"],"check")
        w.check_done.connect(lambda d:self._done(d,info)); w.error.connect(lambda e:self._err(e,info))
        w.start(); self._worker=w
    def _done(self,d,info):
        self.conn.set_done(True,f"✓ 연결 성공 — {info['host']}")
        self.res.set_online(info["name"],f"{d.get('os','─')}  |  {d.get('ip','─')}  |  kernel {d.get('kernel','─')}")
        self.res.update_data(d)
        # ese@ 서비스 자동 표시
        if d.get("ese_services","").strip():
            self.res.set_ese_services(d["ese_services"])
        # postgresql / nginx 자동 표시
        self.res.set_common_services(d)
        self.statusBar().showMessage(f"[{info['name']}]  🔥 CPU {d.get('cpu_usage','?')}%  |  🧠 MEM {d.get('mem_used_mb','?')}/{d.get('mem_total_mb','?')}MB  |  ⏱ {d.get('uptime_pretty','─')}")
        if info["host"] not in [s["host"] for s in self.servers]:
            self.servers.append(dict(info)); self._save(); self._refresh_list()
        for i,s in enumerate(self.servers):
            if s["host"]==info["host"]:
                w=self.srv_list.itemWidget(self.srv_list.item(i))
                if w: w.set_status("online")
    def _err(self,e,info):
        self.conn.set_done(False,f"✗ {e}"); self.res.set_offline()
        self.statusBar().showMessage(f"[{info['host']}] 오류: {e}")
        for i,s in enumerate(self.servers):
            if s["host"]==info["host"]:
                w=self.srv_list.itemWidget(self.srv_list.item(i))
                if w: w.set_status("error")
    def _recheck(self):
        if self.active_info: self.conn._go()
    def _disconnect(self): self.active_info=None; self.res.set_offline(); self.statusBar().showMessage("연결 해제됨.")
    def _check_ese_services(self, names: list):
        """ese@ 서비스 목록을 순차적으로 점검해 테이블 갱신"""
        if not self.active_info: return
        self._ese_queue = list(names)
        self._ese_results = {}
        self._run_next_ese()
    def _run_next_ese(self):
        if not self._ese_queue: return
        svc = self._ese_queue.pop(0)
        i = self.active_info
        cmd = f"systemctl status {svc} --no-pager 2>/dev/null || service {svc} status 2>&1"
        w = SSHWorker(i["host"], i["port"], i["user"], i["pwd"], "cmd", cmd)
        def on_result(out, s=svc):
            # 파싱
            active = "unknown"; sub = ""
            for line in out.splitlines():
                ll = line.strip().lower()
                if "active:" in ll:
                    if   "active (running)" in ll: active = "running"
                    elif "active (exited)"  in ll: active = "exited"
                    elif "inactive"         in ll: active = "inactive"
                    elif "failed"           in ll: active = "failed"
                    sub = line.split(":",1)[1].strip()[:80] if ":" in line else line
                    break
            # 테이블에서 해당 서비스 행 찾아 갱신
            tbl = self.res.svc_tbl
            for row in range(tbl.rowCount()):
                if tbl.item(row, 0) and tbl.item(row, 0).text() == s:
                    color = {"running":"#3FB950","exited":"#D29922","inactive":"#8B949E","failed":"#F85149"}.get(active,"#8B949E")
                    si = QTableWidgetItem(active.upper())
                    si.setForeground(QColor(color)); si.setFont(QFont("Consolas",11,QFont.Bold))
                    di = QTableWidgetItem(sub)
                    tbl.setItem(row, 1, si); tbl.setItem(row, 2, di)
                    break
            self.statusBar().showMessage(f"ese@ 점검 중... {s} → {active.upper()}")
            self._run_next_ese()  # 다음 서비스
        w.cmd_done.connect(on_result)
        w.error.connect(lambda e: on_result(f"error: {e}"))
        w.start(); self._ese_worker = w
    def _run_cmd(self,cmd):
        if not self.active_info: QMessageBox.warning(self,"알림","먼저 서버에 연결하세요."); return
        self.res.cmd_out.append(f"<span style='color:#D29922'>$ {cmd}</span>")
        i=self.active_info
        w=SSHWorker(i["host"],i["port"],i["user"],i["pwd"],"cmd",cmd)
        def on_done(out, cmd=cmd):
            self.res.append_cmd(out)
            # 서비스 상태 점검이었으면 테이블도 갱신
            pending = getattr(self.res, '_pending_svc', None)
            if pending and ('systemctl status' in cmd or 'service' in cmd and 'status' in cmd):
                self.res.update_svc_table(pending, out)
                self.res._pending_svc = None
        w.cmd_done.connect(on_done); w.error.connect(lambda e:self.res.append_cmd(f"ERROR: {e}"))
        w.start(); self._cw=w

def main():
    app=QApplication(sys.argv); app.setApplicationName("서버 점검 도구"); app.setStyleSheet(SS)
    pal=QPalette(); pal.setColor(QPalette.Window,QColor("#0D1117")); pal.setColor(QPalette.WindowText,QColor("#E6EDF3"))
    pal.setColor(QPalette.Base,QColor("#161B22")); pal.setColor(QPalette.Text,QColor("#E6EDF3")); app.setPalette(pal)
    w=MainWindow(); w.show(); sys.exit(app.exec_())

if __name__=="__main__": main()
