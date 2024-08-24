import os
import subprocess
import sys
from datetime import datetime

grafana_dir = '/backup/grafana'
influxdb_dir = '/backup/influxdb'
jenkins_dir = '/backup/jenkins'

volume_grafana = 'docker-compose_grafana-storage'
volume_influxdb = 'docker-compose_influxdb-storage'
volume_jenkins = 'jenkins_jenkins-home'

grafana_container = "docker-compose-grafana-1"
influx_container = "docker-compose-influxdb-1"
jenkins_container = "jenkins"

backup_dir_grafana = "path-to-backup"
backup_dir_influxdb = "path-to-backup"
backup_dir_jenkins = "path-to-backup"

backup_grafana = f"grafana_backup_{datetime.now().strftime('%Y%m%d')}.tar.gz"
backup_influxdb = f"influxdb_backup_{datetime.now().strftime('%Y%m%d')}.tar.gz"
backup_jenkins = f"jenkins_backup_{datetime.now().strftime('%Y%m%d')}.tar.gz"

def stop_container(container_id):
    subprocess.run(["docker", "stop", container_id], check=True)

def start_container(container_id):
    subprocess.run(["docker", "start", container_id], check=True)

def create_backup(volume_name, backup_dir, backup_file):
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{volume_name}:/volume",
        "-v", f"{backup_dir}:/backup",
        "alpine",
        "sh", "-c", f"cd /volume && tar -czf /backup/{backup_file} ."
    ]
    subprocess.run(cmd, check=True)
    print(f"Backup criado em: {backup_file}")

# ---------------------------------------------- #
#            Get values from command line        #
# ---------------------------------------------- #
def get_values_in_command_line():
    global backup_dir_grafana, backup_dir_influxdb, backup_dir_jenkins
    if len(sys.argv) == 3:
        backup_dir_grafana = sys.argv[1]
        print(f'Grafana Backup: {backup_dir_grafana}')
        backup_dir_influxdb = sys.argv[2]
        print(f'Influx DB Backup: {backup_dir_influxdb}')
        backup_dir_jenkins = sys.argv[3]
        print(f'Jenkins Backup: {backup_dir_jenkins}')
    else:
        print("Not enough arguments provided.")
    

if __name__ == "__main__":
    stop_container(grafana_container)
    create_backup(volume_grafana, backup_dir_grafana, backup_grafana)
    start_container(grafana_container)
    
    stop_container(influx_container)
    create_backup(volume_influxdb, backup_dir_influxdb, backup_influxdb)
    start_container(influx_container)

    #stop_container(jenkins_container)
    #create_backup(volume_jenkins, backup_dir_jenkins, backup_jenkins)
    #start_container(jenkins_container)