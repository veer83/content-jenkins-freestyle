
def filter_swagger_content(raw_content):
    """Parses Swagger content and extracts relevant information for Swagger 2.0 and OpenAPI 3.0."""
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    paths_data = []

    try:
        # Step 1: Capture relevant Swagger lines
        for line in raw_content.splitlines():
            if "openapi" in line or "swagger" in line:
                capture = True
            if capture:
                swagger_lines.append(line)

        # Step 2: Combine and parse YAML content
        filtered_content = "\n".join(swagger_lines)
        swagger_json = yaml.safe_load(filtered_content)

        if not isinstance(swagger_json, dict):
            raise ValueError("Swagger content is not a valid dictionary")

        # Step 3: Detect Swagger version and extract basepath
        if "openapi" in swagger_json:  # OpenAPI 3.0
            logging.info("Detected OpenAPI 3.0 specification.")
            servers = swagger_json.get("servers", [])
            if isinstance(servers, list) and servers:
                basepath = servers[0].get("url", "")
            else:
                logging.warning("No 'servers' field found in OpenAPI 3.0.")

        elif "swagger" in swagger_json and swagger_json["swagger"] == "2.0":  # Swagger 2.0
            logging.info("Detected Swagger 2.0 specification.")
            basepath = swagger_json.get("basePath", "")
            schemes = swagger_json.get("schemes", [])
            if schemes and basepath:
                basepath = f"{schemes[0]}://{basepath}"  # Combine scheme and basePath
            elif basepath:
                logging.warning("No 'schemes' field found; using 'basePath' as is.")
            else:
                logging.warning("No 'basePath' field found in Swagger 2.0.")

        else:
            logging.error("Unknown Swagger/OpenAPI format.")
            return None, None, None, None

        # Step 4: Extract 'info' section
        info_data = swagger_json.get("info", {})

        # Step 5: Extract paths and methods
        paths = swagger_json.get("paths", {})
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                logging.warning(f"Skipping invalid path: {path}")
                continue

            for method, details in methods.items():
                if not isinstance(method, str) or not isinstance(details, dict):
                    logging.warning(f"Skipping invalid method in path {path}")
                    continue

                dataclassification_code = details.get("x-dataclassification-code")
                paths_data.append({
                    "path": path,
                    "verb": method.upper(),
                    "dataclassification_code": dataclassification_code
                })

        return swagger_json, basepath, info_data, paths_data

    except (yaml.YAMLError, ValueError, TypeError) as e:
        logging.error(f"Error parsing Swagger content: {e}")
        return None, None, None, None
