import subprocess
import os
import sys
import json
import getpass
import yaml
import logging
import re
from glob import glob
from datetime import datetime
import requests

# Constants
OUTPUT_DIR = "/tmp/output"
LOG_DIR = "/tmp/logs"
CONFIG_FILE = "config.yaml"
LOGIN_SCRIPT = "./apic_login.sh"
LIST_PRODUCTS_SCRIPT = "./list_products.sh"
GET_SWAGGER_SCRIPT = "./get_swagger_by_name.sh"
API_PUSH_URL = ""

HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "insomnia/10.0.0",
    "x-api-key": "",
    "x-apigw-api-id": "",
    "x-app-cat-id": "sdsadas",
    "x-database-schema": "",
    "x-fapi-financial-id": "sdsadasdsadsadasdsa",
    "x-request-id": "abcd"
}

# Configure Logging
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"swagger_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename)
    ]
)

logger = logging.getLogger(__name__)


class CommandError(Exception):
    """Custom exception to indicate a command execution failure."""
    pass


def load_config():
    """Load configurations from YAML file."""
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"Configuration file {CONFIG_FILE} not found.")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, "r") as file:
            config = yaml.safe_load(file)
            # Validate required fields
            required_keys = ["environment", "username", "password", "catalog", "space"]
            for key in required_keys:
                if key not in config or not config[key]:
                    logger.error(f"Configuration key '{key}' is missing or empty.")
                    sys.exit(1)
            return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        sys.exit(1)


def run_command(command, success_msg, error_msg, capture_output=False):
    """
    Run a command using subprocess and handle errors.
    Raises CommandError on failure.
    """
    logger.debug(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=capture_output, text=True)
        logger.info(success_msg)
        if capture_output:
            logger.debug(f"Command output: {result.stdout}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"{error_msg}: {e}")
        if capture_output and e.stderr:
            logger.error(e.stderr)
        raise CommandError(error_msg)


def setup_output_directory():
    """Ensure that output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"Output directory set up at {OUTPUT_DIR}")


def find_latest_yaml_file():
    """Find the latest YAML file in the output directory."""
    yaml_files = glob(os.path.join(OUTPUT_DIR, "*.yaml"))
    if not yaml_files:
        logger.error("No YAML files found in the output directory.")
        return None

    latest_file = max(yaml_files, key=os.path.getctime)
    logger.info(f"Using product list file: {latest_file}")
    return latest_file


def load_product_list():
    """Load the product list from the latest YAML file."""
    file_path = find_latest_yaml_file()
    if not file_path:
        logger.error("Exiting due to missing product list file.")
        sys.exit(1)

    with open(file_path, 'r') as f:
        data = yaml.safe_load(f) or {}
        if not data:
            logger.error("Error: Product list is empty or could not be loaded properly.")
            sys.exit(1)
        return data


def login(env, username, password):
    """Login using the provided credentials and return environment data."""
    logger.debug("Attempting login...")
    login_command = [LOGIN_SCRIPT, env, username, password]
    result = run_command(login_command, "Login successful", "Error during login", capture_output=True)

    try:
        login_output = result.stdout.strip()
        logger.info(f"Login output: {login_output}")
        login_data = json.loads(login_output)
        return login_data.get("env"), login_data.get("space"), login_data.get("org")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing login output JSON: {e}")
        sys.exit(1)


def list_products(env, catalog, space):
    """Download the list of products for the given environment, catalog, and space."""
    run_command(
        [LIST_PRODUCTS_SCRIPT, env, OUTPUT_DIR, catalog, space],
        "Product list downloaded successfully.",
        "Error downloading product list"
    )


def filter_swagger_content(raw_content):
    """
    Extract and parse the Swagger/OpenAPI JSON content from the raw command output.
    Attempts to correct common JSON formatting issues.
    Returns swagger_json, basepath, info_data, paths_data.
    """
    swagger_lines = []
    capture = False
    paths_data = []

    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)

    if not swagger_lines:
        logger.warning("No swagger content found in the output.")
        return None, "", {}, []

    # Attempt to fix formatting issues
    fixed_content = "\n".join(swagger_lines)
    # Replace single quotes with double quotes carefully
    fixed_content = fixed_content.replace("'", '"')
    # Remove trailing commas before } or ]
    fixed_content = re.sub(r",\s*}", "}", fixed_content)
    fixed_content = re.sub(r",\s*]", "]", fixed_content)
    # Remove trailing commas at line endings
    fixed_content = re.sub(r",\s*\n", "\n", fixed_content)
    # Add quotes around keys if not present - this is heuristic and might need improvement
    fixed_content = re.sub(r"(\w+):", r'"\1":', fixed_content)

    try:
        swagger_json = json.loads(fixed_content)
        basepath = ""
        if isinstance(swagger_json.get("servers"), list) and swagger_json["servers"]:
            basepath = swagger_json["servers"][0].get("url", "")

        info_data = swagger_json.get("info", {})
        for path, methods in swagger_json.get("paths", {}).items():
            for method, details in methods.items():
                paths_data.append({
                    "path": path,
                    "verb": method.upper(),
                    "dataclassification_code": details.get("x-dataclassification-code", "N/A")
                })

        return swagger_json, basepath, info_data, paths_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}. Content skipped.")
        return None, "", {}, []


def push_to_database(product, swagger_content, basepath, env, space, org, created_date, updated_date, info_data, paths_data):
    """
    Push the extracted product and API data to the database using a POST request.
    Uses the 'requests' library instead of curl.
    """
    if isinstance(swagger_content, str):
        try:
            swagger_content = json.loads(swagger_content)
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Swagger content: {e}")
            return

    for path_data in paths_data:
        data = {
            "prod_name": product.get("name", ""),
            "prod_title": product.get("title", ""),
            "prod_version": product.get("version", ""),
            "env": env,
            "space": space,
            "org": org,
            "api_name": info_data.get("api_name", ""),
            "api_version": info_data.get("api_version", ""),
            "x_mqm_api_provider_id": info_data.get("x-mqm-api-provider-id", 0),
            "x_template_version": info_data.get("x-template-version", "N/A"),
            "description": info_data.get("description", ""),
            "dataclassification_code": path_data.get("dataclassification_code", "N/A"),
            "path": path_data["path"],
            "verb": path_data["verb"],
            "swagger": swagger_content,
            "prod_created_date": created_date,
            "prod_updated_date": updated_date,
            "basepath": basepath
        }

        json_data = json.dumps(data, indent=4)
        logger.debug(f"POST Payload: {json_data}")

        try:
            response = requests.post(API_PUSH_URL, headers=HEADERS, data=json_data, verify=False)
            if response.status_code == 200:
                logger.info("Data pushed successfully.")
                logger.debug(f"API Response: {response.text}")
            else:
                logger.error(f"Error pushing to database. Status code: {response.status_code}, Response: {response.text}")
        except requests.RequestException as e:
            logger.error(f"Network error pushing to database: {e}")


def process_product(product, env, space, org, catalog):
    """
    Process a single product:
    - Fetch the swagger file
    - Parse it
    - Push the data to the database
    """
    product_name = product.get('name')
    product_version = product.get('version')
    logger.info(f"Processing product: {product_name}")

    swagger_command = [GET_SWAGGER_SCRIPT, env, f"{product_name}:{product_version}", catalog, OUTPUT_DIR]
    try:
        result = run_command(swagger_command, "Swagger downloaded successfully", "Error downloading Swagger", capture_output=True)
    except CommandError:
        logger.error(f"Skipping product {product_name} due to fetch error.")
        return

    swagger_json, basepath, info_data, paths_data = filter_swagger_content(result.stdout)
    if swagger_json:
        created_date = product.get("created_date", "")
        updated_date = product.get("updated_date", "")
        push_to_database(
            product,
            swagger_json,
            basepath,
            env,
            space,
            org,
            created_date,
            updated_date,
            info_data,
            paths_data
        )
    else:
        logger.warning(f"No valid swagger extracted for product {product_name}, skipping.")


def process_products(product_list, env, space, org, catalog):
    """
    Process all products from the product list.
    """
    for product in product_list.get("results", []):
        process_product(product, env, space, org, catalog)


def main():
    try:
        config = load_config()
        setup_output_directory()

        env = config.get("environment")
        username = config.get("username")
        password = config.get("password")
        catalog = config.get("catalog")
        space = config.get("space")

        # Login and get environment info
        env, space, org = login(env, username, password)

        # Download product list
        list_products(env, catalog, space)

        # Load product list from downloaded YAML
        product_list = load_product_list()
        if not product_list:
            logger.error("Exiting due to empty or invalid product list.")
            sys.exit(1)

        # Process each product
        process_products(product_list, env, space, org, catalog)
        logger.info("Completed all operations successfully.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
