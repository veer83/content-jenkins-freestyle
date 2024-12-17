def filter_swagger_content(raw_content):
    swagger_lines = []   # List to collect Swagger lines
    capture = False      # Flag to capture relevant lines
    basepath = ""        # Placeholder for basepath
    info_data = {}       # Placeholder for API metadata
    paths_data = []      # List to store path and verb data

    # Step 1: Capture relevant Swagger lines
    for line in raw_content.splitlines():
        if "openapi" in line or "swagger" in line:  # Detect start of Swagger JSON
            capture = True
        if capture:
            swagger_lines.append(line)  # Add lines to swagger_lines

    # Step 2: Parse JSON content
    try:
        filtered_content = "\n".join(swagger_lines)  # Join lines into a single string
        swagger_json = json.loads(filtered_content)  # Parse JSON

        if not isinstance(swagger_json, dict):  # Validate the parsed JSON is a dictionary
            raise ValueError("Swagger content is not a valid dictionary")

        # Step 3: Extract basepath
        servers = swagger_json.get("servers", [])
        if isinstance(servers, list) and servers:
            basepath = servers[0].get("url", "")


        # Step 5: Extract paths and methods
        paths = swagger_json.get("paths", {})
        for path, methods in paths.items():
            if not isinstance(methods, dict):  # Validate methods structure
                logging.warning(f"Skipping invalid methods data: {methods}")
                continue

            for method, details in methods.items():
                if not isinstance(method, str):  # Ensure method is a string
                    logging.warning(f"Skipping invalid method: {method}")
                    continue

                paths_data.append({
                    "path": path,
                    "verb": method.upper()
                })

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logging.error(f"JSON parsing error: {e}. Content skipped.")
        return None, None, None, None  # Return early if parsing fails

    # Step 6: Return parsed and cleaned data
    return swagger_json, basepath, info_data, paths_data
