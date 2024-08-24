import os
import subprocess
import sys
from datetime import datetime

volume_grafana = 'docker-compose_grafana-storage'
volume_influxdb = 'docker-compose_influxdb-storage'
volume_jenkins = 'jenkins_jenkins-home'

grafana_container = "docker-compose-grafana-1"
influx_container = "docker-compose-influxdb-1"
jenkins_container = "jenkins"


backup_dir_grafana = "path-to-backup"
backup_dir_influxdb = "path-to-backup"
backup_dir_jenkins = "path-to-backup"

restore_grafana_file = f"grafana_backup_20240824.tar.gz"
restore_influxdb_file = f"influxdb_backup_20240824.tar.gz"

def stop_container(container_id):
    subprocess.run(["docker", "stop", container_id], check=True)

def start_container(container_id):
    subprocess.run(["docker", "start", container_id], check=True)

def restore_backup(volume_name, backup_dir, backup_file):
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{volume_name}:/volume",
        "-v", f"{backup_dir}:/backup",
        "alpine",
        "sh", "-c", f"cd /volume && tar -xzf /backup/{backup_file}"
    ]
    subprocess.run(cmd, check=True)
    print(f"Backup restaurado de: {backup_file}")

# ---------------------------------------------- #
#            Get values from command line        #
# ---------------------------------------------- #
def get_values_in_command_line():
    global backup_dir_grafana, backup_dir_influxdb, backup_dir_jenkins, restore_influxdb_file, restore_grafana_file

    if len(sys.argv) == 6:
        backup_dir_grafana = sys.argv[1]
        print(f'Grafana Backup: {backup_dir_grafana}')
        backup_dir_influxdb = sys.argv[2]
        print(f'Influx DB Backup: {backup_dir_influxdb}')
        backup_dir_jenkins = sys.argv[3]
        print(f'Jenkins Backup: {backup_dir_jenkins}')
        restore_influxdb_file = f"influx_backup_{sys.argv[4]}.tar.gz"
        print(f'Influx Backup: {restore_influxdb_file}')
        restore_grafana_file = f"grafana_backup_{sys.argv[5]}.tar.gz"
        print(f'Grafana Backup: {restore_grafana_file}')
    else:
        print("Not enough arguments provided.")

if __name__ == "__main__":
    get_values_in_command_line()
    
    stop_container(grafana_container)
    restore_backup(volume_grafana, backup_dir_grafana, restore_grafana_file)
    start_container(grafana_container)
    
    # stop_container(influx_container)
    # restore_backup(volume_influxdb, backup_dir_influxdb, restore_influxdb_file)
    # start_container(influx_container)