def filter_swagger_content(raw_content):
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    dataclassification_code = ""
    paths_data = []  

    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)
    filtered_content = "\n".join(swagger_lines) if swagger_lines else None

    if filtered_content:
        try:
            fixed_content = filtered_content.replace("'", '"')  # Fix JSON formatting
            swagger_json = json.loads(fixed_content)

            # Basepath extraction
            if "servers" in swagger_json:
                basepath = swagger_json["servers"][0].get("url", "")

            # Info fields
            if "info" in swagger_json:
                info = swagger_json["info"]
                info_data = {
                    "api_name": info.get("title", ""),
                    "api_version": info.get("version", ""),
                    "x_bmo_api_provider_id": safe_int(info.get("x-bmo-api-provider-id", 0)),
                    "x_template_version": info.get("x-template-version", "N/A"),
                    "description": info.get("description", "")
                }

            # x-dataclassification-code and paths
            for path, methods in swagger_json.get("paths", {}).items():
                for method, details in methods.items():
                    paths_data.append({
                        "path": path,
                        "verb": method.upper(),
                        "dataclassification_code": details.get("x-dataclassification-code", "N/A")
                    })

            return swagger_json, basepath, info_data, paths_data
        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}")
    return None, "", {}, []



def push_to_database(product, plan, swagger_content, basepath, env, space, org, created_date, updated_date, info_data, paths_data):
    if isinstance(swagger_content, str):
        try:
            swagger_content = json.loads(swagger_content)  # Ensure proper JSON format
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing Swagger content: {e}")
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
            "x_bmo_api_provider_id": info_data.get("x_bmo_api_provider_id", 0),
            "x_template_version": info_data.get("x_template_version", "N/A"),
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
        logging.info(f"Payload data: {json_data}")

        try:
            # Send payload to the API
            result = subprocess.run(
                ["curl", "--insecure", "--request", "POST", "--url", API_PUSH_URL,
                 "--header", "Content-Type: application/json", "--data", json_data],
                check=True, capture_output=True, text=True)
            logging.info(f"API Response: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error pushing to database: {e.stderr}")



def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        logging.warning(f"Invalid integer value: {value}. Defaulting to {default}.")
        return default

