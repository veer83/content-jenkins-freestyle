import json
import subprocess
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to execute oc commands and capture output
def run_oc_command(command: list) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running command {command}: {e}")
        return None

# Fetch a single build config
def get_build_config(project_name: str, build_config_name: str):
    logging.info(f"Fetching BuildConfig '{build_config_name}' in project '{project_name}'")
    output = run_oc_command(["oc", "get", "bc", build_config_name, "-n", project_name, "-o", "json"])
    return json.loads(output) if output else None

# Fetch all build configs in a namespace
def get_all_build_configs(project_name: str):
    logging.info(f"Fetching all BuildConfigs in project '{project_name}'")
    output = run_oc_command(["oc", "get", "bc", "-n", project_name, "-o", "json"])
    return json.loads(output).get("items", []) if output else []

# Check if a build config matches the criteria
def matches_criteria(bc: dict) -> bool:
    source = bc.get("spec", {}).get("source", {})
    context_dir = source.get("contextDir", "")
    git = source.get("git", {})
    uri = git.get("uri", "")
    ref = git.get("ref", "")

    return (
        context_dir == "ingboot" and
        uri == "ht" and
        ref == "c"
    )

# Update a build config
def update_build_config(project_name: str, build_config_name: str) -> None:
    logging.info(f"Updating BuildConfig: {build_config_name} in project '{project_name}'")
    patch_data = {
        "spec": {
            "strategy": {
                "dockerStrategy": {
                    "pullSecrets": [
                        {"name": "as"}
                    ]
                }
            },
            "output": {
                "pushSecret": {
                    "name": "as"
                }
            },
            "secrets": [
                {"secret": {"name": "s"}}
            ]
        }
    }

    patch_data_json = json.dumps(patch_data)
    command = [
        "oc", "patch", "bc", build_config_name,
        "-n", project_name,
        "--type", "merge",
        "-p", patch_data_json
    ]
    result = run_oc_command(command)
    if result:
        logging.info(f"Successfully updated BuildConfig: {build_config_name}")
    else:
        logging.error(f"Failed to update BuildConfig: {build_config_name}")

# Update multiple build configs in a namespace
def update_multiple_build_configs(project_name: str, build_configs: list):
    for build_config_name in build_configs:
        bc = get_build_config(project_name, build_config_name)
        if bc and matches_criteria(bc):
            update_build_config(project_name, build_config_name)
        else:
            logging.warning(f"BuildConfig '{build_config_name}' does not match the criteria or was not found.")

# Update all matching build configs in a namespace
def update_all_build_configs_in_namespace(project_name: str):
    build_configs = get_all_build_configs(project_name)
    if not build_configs:
        logging.warning(f"No BuildConfigs found in namespace '{project_name}'")
        return

    for bc in build_configs:
        bc_name = bc.get("metadata", {}).get("name", "")
        if matches_criteria(bc):
            update_build_config(project_name, bc_name)
        else:
            logging.info(f"BuildConfig '{bc_name}' does not match the criteria and will not be updated.")

# Entry point
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update OpenShift BuildConfigs.")
    parser.add_argument('--project', required=True, help="Project namespace.")
    parser.add_argument('--build-configs', nargs='+', help="List of BuildConfig names to update.")
    parser.add_argument('--update-all', action='store_true', help="Update all BuildConfigs in the namespace.")
    args = parser.parse_args()

    # Update multiple BuildConfigs or all BuildConfigs in the namespace
    if args.build_configs:
        update_multiple_build_configs(args.project, args.build_configs)
    elif args.update_all:
        update_all_build_configs_in_namespace(args.project)
    else:
        logging.error("Please specify --build-configs to update specific BuildConfigs or --update-all to update all.")
