def filter_swagger_content(raw_content):
    """
    Filters the Swagger content and extracts relevant details into a dictionary.
    Handles improper single quotes, trailing commas, and malformed JSON.
    """
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    dataclassification_code = ""
    paths_data = []

    # Step 1: Capture relevant Swagger lines
    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)

    filtered_content = "\n".join(swagger_lines) if swagger_lines else None

    if filtered_content:
        try:
            # Step 2: Pre-clean the JSON content
            fixed_content = filtered_content.replace("'", '"')  # Replace single quotes with double quotes
            fixed_content = re.sub(r",\s*}", "}", fixed_content)  # Remove trailing commas before }
            fixed_content = re.sub(r",\s*]", "]", fixed_content)  # Remove trailing commas before ]
            fixed_content = re.sub(r",\s*\n", "\n", fixed_content)  # Remove trailing commas at the end of lines
            fixed_content = re.sub(r"(\w+):", r'"\1":', fixed_content)  # Add quotes around unquoted keys

            # Step 3: Parse the cleaned JSON
            swagger_json = json.loads(fixed_content)

            # Step 4: Extract basepath
            if "servers" in swagger_json:
                basepath = swagger_json["servers"][0].get("url", "")

            # Step 5: Extract info fields
            if "info" in swagger_json:
                info = swagger_json["info"]
                info_data = {
                    "api_name": info.get("title", ""),
                    "api_version": info.get("version", ""),
                    "x_bmo_api_provider_id": safe_int(info.get("x-bmo-api-provider-id", 0)),
                    "x_template_version": info.get("x-template-version", "N/A"),
                    "description": info.get("description", "")
                }

            # Step 6: Extract x-dataclassification-code and paths
            for path, methods in swagger_json.get("paths", {}).items():
                for method, details in methods.items():
                    paths_data.append({
                        "path": path,
                        "verb": method.upper(),
                        "dataclassification_code": details.get("x-dataclassification-code", "N/A")
                    })

            return swagger_json, basepath, info_data, dataclassification_code, paths_data

        except json.JSONDecodeError as e:
            logging.error(f"JSON parsing error: {e}. Content skipped.")
            return None, "", {}, "", []  # Return empty values on error

    return None, "", {}, "", []  # Return empty values if no content is captured
