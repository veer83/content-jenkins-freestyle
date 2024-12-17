

# Configure logging
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

def setup_output_directory():
    """Ensures the output directory exists."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logging.info(f"Created output directory at {OUTPUT_DIR}")

def run_command(command, success_msg, error_msg, capture_output=False):
    """Runs a shell command with optional output capturing."""
    try:
        result = subprocess.run(
            command, check=True, capture_output=capture_output, text=True
        )
        if success_msg:
            logging.info(success_msg)
        return result
    except subprocess.CalledProcessError as e:
        logging.error(f"{error_msg}: {e.stderr}")
        exit(1)

def login(env, username, password):
    """Logs into the environment using the login script."""
    login_command = [LOGIN_SCRIPT, env, username, password]
    result = run_command(
        login_command,
        "Login successful.",
        "Error during login",
        capture_output=True
    )
    if result and result.stdout:
        login_data = json.loads(result.stdout.strip())
        return login_data.get("env"), login_data.get("space"), login_data.get("org")
    else:
        logging.error("Failed to capture login output.")
        exit(1)

def list_products(env, catalog, space):
    """Runs the product listing script and generates a product list YAML."""
    run_command(
        [LIST_PRODUCTS_SCRIPT, env, OUTPUT_DIR, "0", catalog, space],
        "Product list downloaded successfully.",
        "Error downloading product list"
    )

def filter_swagger_content(raw_content):
    """
    Filters the Swagger content and extracts relevant details into a dictionary.
    """
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    dataclassification_code = ""
    paths_data = []  # To store path and verb information

    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)
    filtered_content = "\n".join(swagger_lines) if swagger_lines else None

    if filtered_content:
        try:
            swagger_json = json.loads(filtered_content)

            # Extract basepath
            if "basePath" in swagger_json:
                basepath = swagger_json["basePath"]
            elif "servers" in swagger_json:
                servers = swagger_json.get("servers", [{}])
                if isinstance(servers, list) and "url" in servers[0]:
                    basepath = servers[0].get("url", "")

            # Extract info fields for the API
            if "info" in swagger_json:
                info = swagger_json["info"]
                info_data = {
                    "api_name": info.get("title", ""),
                    "api_title": info.get("title", ""),
                    "api_version": info.get("version", ""),
                    "description": info.get("description", ""),
                    "x_ibm_name": info.get("x-ibm-name", ""),
                    "x_bmo_api_type": info.get("x-bmo-api-type", ""),
                    "x_template_version": info.get("x-template-version", ""),
                }

            # Extract x-dataclassification-code and paths/verbs
            if "paths" in swagger_json:
                for path, methods in swagger_json["paths"].items():
                    for method, details in methods.items():
                        if "x-dataclassification-code" in details:
                            dataclassification_code = details["x-dataclassification-code"]

                        # Store the path and HTTP verb
                        paths_data.append({
                            "path": path,
                            "verb": method.upper()  # Convert verb to uppercase for consistency
                        })

            return swagger_json, basepath, info_data, dataclassification_code, paths_data
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
            return None, "", {}, "", []
    return None, "", {}, "", []

def push_to_database(product, plan, api_name, api_version, swagger_content, basepath, env, space, org, created_date, updated_date, info_data, dataclassification_code, paths_data):
    """
    Pushes the Swagger content and additional metadata to the database.
    """
    if isinstance(swagger_content, str):
        try:
            swagger_content = json.loads(swagger_content)  # Ensure it's a dictionary
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing Swagger content: {e}")
            return

    for path_data in paths_data:
        # Preparing the payload
        data = {
            "prod_name": product.get("name", ""),
            "prod_title": product.get("title", ""),
            "prod_state": product.get("state", ""),
            "prod_version": product.get("version", ""),
            "env": env,
            "space": space,
            "org": org,
            "api_name": info_data.get("api_name", ""),
            "api_title": info_data.get("api_title", ""),
            "api_version": info_data.get("api_version", ""),
            "swagger": swagger_content,
            "prod_created_date": created_date,
            "prod_updated_date": updated_date,
            "basepath": basepath,
            "description": info_data.get("description", ""),
            "x_ibm_name": info_data.get("x_ibm_name", ""),
            "x_bmo_api_type": info_data.get("x_bmo_api_type", ""),
            "x_template_version": info_data.get("x_template_version", ""),
            "dataclassification_code": dataclassification_code,
            "path": path_data["path"],
            "verb": path_data["verb"],
            **info_data
        }

        json_data = json.dumps(data, indent=4)
        logging.info(f"Payload being sent for product: {product.get('name')} plan: {plan.get('name')}")
        logging.info(f"Payload data: {json_data}")

        # Preparing the curl command
        curl_command = [
            "curl", "--insecure", "--request", "POST",
            "--url", API_PUSH_URL,
            "--header", f"Content-Type: {HEADERS['Content-Type']}",
            "--header", f"User-Agent: {HEADERS['User-Agent']}",
            "--header", f"x-api-key: {HEADERS['x-api-key']}",
            "--header", f"x-apigw-api-id: {HEADERS['x-apigw-api-id']}",
            "--header", f"x-app-cat-id: {HEADERS['x-app-cat-id']}",
            "--header", f"x-database-schema: {HEADERS['x-database-schema']}",
            "--header", f"x-fapi-financial-id: {HEADERS['x-fapi-financial-id']}",
            "--header", f"x-request-id: {HEADERS['x-request-id']}",
            "--data", json_data
        ]

        try:
            result = subprocess.run(curl_command, check=True, capture_output=True, text=True)
            logging.info(f"API Response: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error pushing data to the database: {e.stderr}")

