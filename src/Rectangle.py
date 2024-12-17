def login(env, username, password):
    logger.debug("Attempting login...")
    login_command = ["sudo", LOGIN_SCRIPT, env, username, password]
    result = run_command(login_command, "Login successful", "Error during login", capture_output=True)
    login_output = result.stdout.strip()

    for line in login_output.splitlines():
        if "Logged into" in line and "successfully" in line:
            parts = line.split()
            if len(parts) >= 4:
                host = parts[2]
                match = re.search(r'api-manage-ui\.(?P<org>[^\.]+)\.(?P<env>[^\.]+)\.\.net', host)
                if match:
                    org_found = match.group('org')
                    env_found = match.group('env')
                    # We don't get space from here, so we'll rely on config for space.
                    # Just return the env and org found. We'll assume space is already known from config.
                    return env_found, None, org_found

    logger.error("Unable to extract env, space, and org from login output.")
    sys.exit(1)


def main():
    try:
        config = load_config()
        setup_output_directory()

        env = config.get("environment")
        username = config.get("username")
        password = config.get("password")
        catalog = config.get("catalog")
        # We'll assume space is known from config since login does not provide it.
        space = config.get("space")

        # Login and get environment info from the text output
        env_found, space_found, org_found = login(env, username, password)
        
        # If login extracted env, org but not space, use config space as fallback:
        if space_found is None:
            space_found = space

        # Download product list
        list_products(env_found, catalog, space_found)

        # Load product list from downloaded YAML
        product_list = load_product_list()
        if not product_list:
            logger.error("Exiting due to empty or invalid product list.")
            sys.exit(1)

        # Process each product
        process_products(product_list, env_found, space_found, org_found, catalog)
        logger.info("Completed all operations successfully.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
