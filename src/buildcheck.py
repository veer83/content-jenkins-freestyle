import json
import subprocess
import logging
import argparse
import csv

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

# Fetch build configs from the project
def get_build_configs(project_name: str):
    logging.info(f"Fetching build configs for project {project_name}")
    output = run_oc_command(["oc", "get", "bc", "-n", project_name, "-o", "json"])
    return json.loads(output) if output else None

# Check if a build config matches the criteria
def matches_criteria(bc: dict) -> bool:
    source = bc.get("spec", {}).get("source", {})
    context_dir = source.get("contextDir", "")
    git = source.get("git", {})
    uri = git.get("uri", "")
    ref = git.get("ref", "")

    return (
        context_dir == " and
        uri == "t" and
        ref == 
    )

# Extract required information from a BuildConfig
def extract_buildconfig_info(bc: dict) -> dict:
    metadata = bc.get("metadata", {})
    spec = bc.get("spec", {})
    output_to = spec.get("output", {}).get("to", {}).get("name", "")
    context_dir = spec.get("source", {}).get("contextDir", "")
    pull_secret = spec.get("strategy", {}).get("dockerStrategy", {}).get("pullSecret", {}).get("name", "")
    secrets = [secret.get("secret", {}).get("name", "") for secret in spec.get("triggers", [])]

    return {
        "metadata_name": metadata.get("name", ""),
        "push_secret": output_to,
        "pull_secret": pull_secret,
        "context_dir": context_dir,
        "secrets": ", ".join(secrets),
    }

# Function to count and save matching build configs to CSV
def count_and_save_matching_build_configs(projects: list, csv_file: str) -> None:
    total_count = 0  # To count the total number of matching build configs
    results = []  # List to store extracted info

    for project_name in projects:
        matching_count = 0  # To count matches within each project
        build_configs = get_build_configs(project_name)
        if build_configs:
            for bc in build_configs.get("items", []):
                if matches_criteria(bc):
                    info = extract_buildconfig_info(bc)
                    info["project_name"] = project_name
                    results.append(info)
                    matching_count += 1
                    total_count += 1
            logging.info(f"Found {matching_count} matching build configs in project {project_name}")
        else:
            logging.warning(f"No build configs found for project {project_name}")

    # Save results to CSV
    if results:
        keys = results[0].keys()
        with open(csv_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Saved {total_count} matching build configs to {csv_file}")
    else:
        logging.info("No matching build configs to save.")

# Function to load projects dynamically (either from input or config)
def load_projects(project_file: str = None, specific_projects: list = None) -> list:
    # Load from a file if specified
    if project_file:
        with open(project_file, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    # Use projects provided by the user
    elif specific_projects:
        return specific_projects
    return []

# Entry point with arguments for flexibility
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Count and save matching OpenShift BuildConfigs to a CSV.")
    parser.add_argument('--projects', nargs='+', help="List of specific projects to update.")
    parser.add_argument('--project-file', help="File containing a list of projects to process (one per line).")
    parser.add_argument('--batch-size', type=int, default=5, help="Number of projects to process in a batch.")
    parser.add_argument('--output-file', default="matching_buildconfigs.csv", help="CSV file to save results.")
    args = parser.parse_args()

    # Load the projects either from a file or a provided list
    projects = load_projects(args.project_file, args.projects)

    if not projects:
        logging.error("No projects provided. Use --projects or --project-file.")
    else:
        # Process in batches to avoid processing too many projects at once
        batch_size = args.batch_size
        for i in range(0, len(projects), batch_size):
            project_batch = projects[i:i + batch_size]
            count_and_save_matching_build_configs(project_batch, args.output_file)
