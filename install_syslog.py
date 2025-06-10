#!/opt/splunk/bin/python

import os
import socket
import subprocess
import shutil

def run(cmd, check=True):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=check)

def write_file(path, content, mode=0o644):
    print(f"Writing: {path}")
    with open(path, "w") as f:
        f.write(content)
    os.chmod(path, mode)

def is_package_installed(package_name):
    return shutil.which(package_name) is not None

def main():
    syslog_server_name = socket.gethostname()
    syslog_base_dir = f"/opt/syslog/{syslog_server_name}"

    # 1. Check if rsyslog is installed
    if not is_package_installed("rsyslogd"):
        print("rsyslog not found, installing...")
        run("apt update")
        run("apt install -y rsyslog")
    else:
        print("rsyslog already installed.")

    # 2. Enable and start rsyslog
    run("systemctl enable rsyslog")
    run("systemctl start rsyslog")

    # 3. Write rsyslog config
    rsyslog_conf_path = "/etc/rsyslog.d/99-custom-palo.conf"
    rsyslog_conf = f"""
module(load="imudp")
module(load="imtcp")
input(type="imudp" port="1515")
input(type="imudp" port="1516")
input(type="imtcp" port="1515")
input(type="imtcp" port="1516")

template(name="PaloAltoLogs" type="string" string="{syslog_base_dir}/%PROGRAMNAME%.log")

if ($inputname == "imtcp" or $inputname == "imudp") and ($syslogfacility-text == "local0") then {{
    action(type="omfile" dynaFile="PaloAltoLogs")
    stop
}}
"""
    write_file(rsyslog_conf_path, rsyslog_conf)

    # 4. Create syslog directory
    os.makedirs(syslog_base_dir, exist_ok=True)
    run("chown syslog:adm /opt/syslog")
    run("chmod 750 /opt/syslog")

    # 5. Configure logrotate
    logrotate_path = "/etc/logrotate.d/rsyslog-opt-syslog"
    logrotate_conf = f"""
{syslog_base_dir}/*.log {{
    daily
    missingok
    rotate 3
    compress
    delaycompress
    notifempty
    create 640 syslog adm
    dateext
}}
"""
    write_file(logrotate_path, logrotate_conf)

    # 6. Restart rsyslog to apply changes
    run("systemctl restart rsyslog")

if __name__ == "__main__":
    main()
