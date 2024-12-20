

# CallAllFunction.py
import subprocess
import os
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler

def execute_python_script(script_name):
    """Execute a Python script."""
    command = ["python", script_name]
    subprocess.run(command, check=True)

def main_scripts():
    """Execute main scripts."""
    logging.info("Starting the execution of main scripts.")

    # Execute swagger-scraper.py
    execute_python_script("/project/ApicScripts/swagger-scraper.py")

    # Execute catalog.py
    execute_python_script("/project/ApicScripts/catalog.py")

    logging.info("Execution of main scripts completed successfully.")

def schedule_job():
    """Schedule periodic execution of scripts."""
    logging.info("Scheduler initialized and task is running.")

    scheduler = BackgroundScheduler()
    scheduler.add_job(main_scripts, "interval", seconds=86400)  # Schedule every 24 hours
    scheduler.start()

    try:
        while True:
            time.sleep(86400)  # Keep the script running
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logging.info("Scheduler shutdown.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    schedule_job()

# config.py
class Config:
    """Configuration class for environment variables and constants."""
    SCRIPTS_DIR = "/project/ApicScripts"

    # Cluster-specific configurations
    CLUSTERS = {
        "cluster1": {
            "ENV": "dev",
            "USERNAME": "admin1",
            "PASSWORD": "password1",
            "OUTPUT_DIR": "/tmp/output_cluster1",
            "CATALOG": "central",
            "SPACE": "cs1"
        },
        "cluster2": {
            "ENV": "prod",
            "USERNAME": "admin2",
            "PASSWORD": "password2",
            "OUTPUT_DIR": "/tmp/output_cluster2",
            "CATALOG": "enterprise",
            "SPACE": "cs2"
        }
    }

    # Default cluster selection
    DEFAULT_CLUSTER = "cluster1"

    # Dynamically fetch configurations based on the selected cluster
    ENV = CLUSTERS[DEFAULT_CLUSTER]["ENV"]
    USERNAME = CLUSTERS[DEFAULT_CLUSTER]["USERNAME"]
    PASSWORD = CLUSTERS[DEFAULT_CLUSTER]["PASSWORD"]
    OUTPUT_DIR = CLUSTERS[DEFAULT_CLUSTER]["OUTPUT_DIR"]
    CATALOG = CLUSTERS[DEFAULT_CLUSTER]["CATALOG"]
    SPACE = CLUSTERS[DEFAULT_CLUSTER]["SPACE"]
