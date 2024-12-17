

def filter_swagger_content(raw_content):
    """Parses Swagger content and extracts relevant information."""
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    paths_data = []


        # Step 2: Capture relevant Swagger lines
        for line in cleaned_content.splitlines():
            if "openapi" in line or "swagger" in line:
                capture = True
            if capture:
                swagger_lines.append(line)

        # Step 3: Combine and parse YAML content
        filtered_content = "\n".join(swagger_lines)
        swagger_json = yaml.safe_load(filtered_content)

        if not isinstance(swagger_json, dict):
            raise ValueError("Swagger content is not a valid dictionary")

        # Step 4: Extract basepath
        servers = swagger_json.get("servers", [])
        if isinstance(servers, list) and servers:
            basepath = servers[0].get("url", "")

        # Step 5: Extract 'info' and 'paths' data
        info_data = swagger_json.get("info", {})
        paths = swagger_json.get("paths", {})

        for path, methods in paths.items():
            if not isinstance(methods, dict):
                logging.warning(f"Skipping invalid path: {path}")
                continue

            for method, details in methods.items():
                if not isinstance(method, str) or not isinstance(details, dict):
                    logging.warning(f"Skipping invalid method in path {path}")
                    continue

                dataclassification_code = details.get("x-dataclassification-code", "")
                paths_data.append({
                    "path": path,
                    "verb": method.upper(),
                    "dataclassification_code": dataclassification_code
                })

        return swagger_json, basepath, info_data, paths_data

    except (yaml.YAMLError, ValueError, TypeError) as e:
        logging.error(f"Error parsing Swagger content: {e}")
        logging.debug(f"Problematic content: {raw_content}")
        return None, None, None, None

def save_swagger_file(name, version, content):
    """Saves filtered Swagger content to a JSON file."""
    swagger_output_file = os.path.join(OUTPUT_DIR, f"{name}_{version}.json")
    try:
        with open(swagger_output_file, 'w') as output_file:
            output_file.write(json.dumps(content, indent=4))
        logging.info(f"Swagger successfully saved to {swagger_output_file}")
        return swagger_output_file
    except Exception as e:
        logging.error(f"Failed to save Swagger for {name}:{version}: {e}")
        return None
