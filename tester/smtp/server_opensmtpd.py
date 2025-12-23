import os
import subprocess

def edit_config_file(config_path, bind_address, port):
    """
    Edits the OpenSMTPD configuration file to bind to localhost on the specified port.
    """
    try:
        # Define the configuration line
        config_line = f"listen on {bind_address} port {port}\n"

        # Check if the configuration file exists
        if not os.path.exists(config_path):
            print(f"Configuration file not found: {config_path}")
            return False

        # Read the current configuration
        with open(config_path, "r") as file:
            config_data = file.readlines()

        # Update or add the bind configuration
        updated = False
        for i, line in enumerate(config_data):
            if line.startswith("listen on"):
                config_data[i] = config_line
                updated = True
                break
        if not updated:
            config_data.append(config_line)

        # Write back the updated configuration
        with open(config_path, "w") as file:
            file.writelines(config_data)

        print(f"Configuration updated: {bind_address}:{port}")
        return True
    except Exception as e:
        print(f"Error editing configuration file: {e}")
        return False


def start_smtpd():
    """
    Starts the OpenSMTPD server in debugging mode.
    """
    try:
        # Ensure the control socket is clean
        control_socket = "/var/run/smtpd.sock"
        if os.path.exists(control_socket):
            os.remove(control_socket)
            print("Removed stale control socket.")

        # Start the SMTP server
        process = subprocess.Popen(
            ["smtpd", "-d"],
            stdout=None,
            stderr=None,
        )
        print("OpenSMTPD server started in debugging mode.")

        return process
    except Exception as e:
        print(f"Error starting SMTPD server: {e}")
        return None


if __name__ == "__main__":
    CONFIG_PATH = "/etc/smtpd.conf"
    BIND_ADDRESS = "localhost"
    PORT = 8030

    # Step 1: Edit the configuration file
    if edit_config_file(CONFIG_PATH, BIND_ADDRESS, PORT):
        # Step 2: Start the server
        server_process = start_smtpd()
        if server_process:
            try:
                print("Press Ctrl+C to stop the server.")
                server_process.wait()
            except KeyboardInterrupt:
                print("\nStopping the server...")
                server_process.terminate()
