import re
import json

def filter_swagger_content(raw_content):
    """
    Filters the Swagger content, extracts relevant details, and handles malformed JSON.
    Returns the cleaned JSON, basepath, dataclassification_code, and paths_data.
    """
    swagger_lines = []
    capture = False
    basepath = ""
    info_data = {}
    dataclassification_code = ""
    paths_data = []

    # Capture relevant Swagger lines
    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:
            capture = True
        if capture:
            swagger_lines.append(line)

    # If no content is captured, return empty
    if not swagger_lines:
        return None, "", {}, "", []

    try:
        # Clean malformed JSON
        filtered_content = "\n".join(swagger_lines)
        fixed_content = filtered_content.replace("'", '"')  # Replace single quotes with double quotes
        fixed_content = re.sub(r",\s*}", "}", fixed_content)  # Remove trailing commas before }
        fixed_content = re.sub(r",\s*]", "]", fixed_content)  # Remove trailing commas before ]
        fixed_content = re.sub(r",\s*\n", "\n", fixed_content)  # Remove trailing commas at the end of lines
        fixed_content = re.sub(r"(\w+):", r'"\1":', fixed_content)  # Add quotes around unquoted keys

        # Parse fixed JSON content
        swagger_json = json.loads(fixed_content)

        # Extract basepath
        if "servers" in swagger_json:
            basepath = swagger_json.get("servers", [{}])[0].get("url", "")

        # Extract info fields
        if "info" in swagger_json:
            info = swagger_json["info"]
            info_data = {
                "api_name": info.get("title", ""),
                "api_version": info.get("version", ""),
                "x_bmo_api_provider_id": safe_int(info.get("x-bmo-api-provider-id", 0)),
                "x_template_version": info.get("x-template-version", "N/A"),
                "description": info.get("description", "")
            }

        # Extract paths and x-dataclassification-code
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
        return None, "", {}, "", []
