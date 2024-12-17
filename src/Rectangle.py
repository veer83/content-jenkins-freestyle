def download_swagger(env, catalog, product_list, space, org):
    for product in product_list.get("results", []):
        created_date = product.get("created_at", "N/A")
        updated_date = product.get("updated_at", "N/A")
        for plan in product.get("plans", []):
            for api in plan.get("apis", []):
                name, version = api.get("name"), api.get("version")
                if name and version:
                    logging.info(f"Processing API: {name} with version: {version} under product: {product.get('name')} and plan: {plan.get('name')}")
                    
                    get_swagger_command = [
                        GET_SWAGGER_SCRIPT, env, f"{name}:{version}", catalog, OUTPUT_DIR
                    ]
                    result = run_command(
                        get_swagger_command,
                        None,
                        f"Error downloading Swagger for {name}:{version}",
                        capture_output=True
                    )

                    # Extract swagger content
                    swagger_content, basepath, info_data, paths_data = filter_swagger_content(result.stdout)

                    # Check and push to database
                    if swagger_content:
                        swagger_file_path = save_swagger_file(name, version, swagger_content)
                        if swagger_file_path:
                            push_to_database(
                                product, plan.get("name"), name, version, swagger_content,
                                basepath, env, space, org, created_date, updated_date, info_data, paths_data
                            )
                    else:
                        logging.warning(f"No relevant Swagger content found for {name}:{version}")
                else:
                    logging.warning(f"Skipping API with missing name or version: {api}")
