def clean_json_content(content):
    """
    Cleans JSON content to replace single quotes, fix trailing commas, and correct key formatting.
    """
    try:
        # Replace single quotes with double quotes
        content = content.replace("'", '"')
        
        # Fix keys without quotes (e.g., key: value → "key": value)
        content = re.sub(r'(?<!")(\b\w+\b):', r'"\1":', content)

        # Remove trailing commas before closing braces or brackets
        content = re.sub(r",\s*}", "}", content)
        content = re.sub(r",\s*]", "]", content)

        # Remove unnecessary commas at the end of lines
        content = re.sub(r",\s*\n", "\n", content)

        return content
    except Exception as e:
        logging.error(f"Error cleaning JSON content: {e}")
        return content

def filter_swagger_content(raw_content):
    """
    Filters and cleans the Swagger content before parsing.
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
            # Step 2: Clean JSON content
            cleaned_content = clean_json_content(filtered_content)

            # Step 3: Parse the cleaned JSON
            swagger_json = json.loads(cleaned_content)

            # Step 4: Extract basepath
            if "servers" in swagger_json:
                basepath = swagger_json["servers"][0].get("url", "")

            # Step 5: Extract info fields
            if "info" in swagger_json:
                info = swagger_json["info"]
                info_data = {
                    "api_name": info.get("title", ""),
                    "api_version": info.get("version", ""),
                    "x_bmo_api_provider_id": info.get("x-bmo-api-provider-id", "N/A"),
                    "x_template_version": info.get("x-template-version", "N/A"),
                    "description": info.get("description", "")
                }

            # Step 6: Extract paths and dataclassification-code
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
