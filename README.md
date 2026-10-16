# Green Pulse - An IoT-Based Smart Plant Monitoring and Care System

## Deployment Guide (AWS EC2)

Green Pulse uses an ESP32-based IoT device to monitor plant environmental conditions and a cloud-based backend to process sensor readings, retrieve weather information, generate plant-care recommendations, and manage notifications.

The Python backend is deployed on an Amazon EC2 instance, allowing the system to operate continuously without requiring a local computer to run the backend.

### 1. System Architecture

The deployed system consists of the following components:

* **ESP32:** Collects temperature, humidity, soil moisture, and light intensity readings from connected sensors.
* **AWS IoT Core:** Provides secure MQTT communication between the ESP32 and the backend.
* **Amazon EC2:** Hosts the Python backend and agent orchestration services.
* **Amazon DynamoDB:** Stores sensor readings for monitoring and historical reference.
* **Weather Service:** Retrieves current weather information for weather-aware plant-care decisions.
* **LLM Integration:** Generates contextual plant-care recommendations and summarizes relevant information.
* **Gmail Integration:** Supports email-based care notifications.
* **Node-RED Dashboard:** Displays sensor readings, plant-care recommendations, weather information, and notifications.

### 2. Prerequisites

Before deploying the backend, ensure that you have:

* An AWS account.
* An Amazon EC2 instance running Amazon Linux 2023.
* SSH access to the EC2 instance.
* AWS IoT Core configured with the required certificates and policies.
* An existing DynamoDB table for sensor readings.
* The Green Pulse source code.
* Python 3 and pip.
* The required API credentials for weather, LLM, and email integrations.

The following deployment configuration is assumed:

| Component        | Configuration             |
| ---------------- | ------------------------- |
| Cloud provider   | Amazon Web Services (AWS) |
| Compute service  | Amazon EC2                |
| Operating system | Amazon Linux 2023         |
| Instance type    | `t3.micro`                |
| Backend language | Python                    |
| MQTT broker      | AWS IoT Core              |
| Database         | Amazon DynamoDB           |
| Process manager  | systemd                   |
| Device           | ESP32 DevKit V1           |

*Note: The instance type is an example configuration. Actual resource requirements depend on the backend workload and LLM integration.*

### 3. Launch the EC2 Instance

1. Sign in to the AWS Management Console.
2. Open the Amazon EC2 console.
3. Launch a new instance with the following configuration:

   * **Name:** `GreenPulse-Backend`
   * **AMI:** Amazon Linux 2023
   * **Instance type:** `t3.micro`
   * **Key pair:** Select an existing key pair or create a new one.
4. Configure the security group to allow SSH access on port `22` from your own IP address.
5. Launch the instance.

The Python backend communicates with AWS IoT Core over MQTT using a secure TLS connection. Therefore, ensure that outbound network access is available.

Inbound MQTT port `8883` does not need to be opened on the EC2 instance because the backend connects to AWS IoT Core as an MQTT client.

### 4. Connect to the EC2 Instance

Connect to the instance using SSH from your local terminal.

Replace `<EC2_PUBLIC_IP>` with the instance's public IP address and `<KEY_FILE.pem>` with the path to your private key.

```bash
ssh -i "<KEY_FILE.pem>" ec2-user@<EC2_PUBLIC_IP>
```

After connecting, update the system packages:

```bash
sudo dnf update -y
```

Install Python, pip, Git, and other useful utilities:

```bash
sudo dnf install -y python3 python3-pip git
```

Verify the Python installation:

```bash
python3 --version
pip3 --version
```

### 5. Transfer the Green Pulse Backend

Clone the Green Pulse repository onto the EC2 instance:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
```

Navigate to the project directory:

```bash
cd <YOUR_REPOSITORY_DIRECTORY>
```

If the repository is private, configure an appropriate authentication method before cloning it.

Alternatively, transfer the project files from your local computer using SCP or another secure file-transfer method.

Ensure that the backend files are available, including:

* `main.py`
* `mqtt_service.py`
* `orchestrator.py`
* Any additional Python modules imported by the backend.

The `Main.ino` firmware and `flows.json` Node-RED configuration are used by separate components and do not need to be executed by the Python backend.

### 6. Set Up the Python Environment

Create a virtual environment inside the project directory:

```bash
python3 -m venv venv
```

Activate the environment:

```bash
source venv/bin/activate
```

Upgrade pip:

```bash
python -m pip install --upgrade pip
```

Install the project's Python dependencies.

If a `requirements.txt` file exists in the repository:

```bash
pip install -r requirements.txt
```

If the project does not contain a dependency file, install the packages required by the existing source code.

These may include:

* `paho-mqtt` for MQTT communication.
* `boto3` for DynamoDB integration.
* `python-dotenv` for environment-variable loading.
* `requests` for HTTP API requests.
* Any additional packages used by the weather, notification, and LLM agents.

Only install packages that are actually required by the implementation.

Verify that the application imports successfully before proceeding.

### 7. Configure Environment Variables

The backend requires configuration values for its AWS IoT connection, weather service, LLM integration, and email notification functionality.

Create a `.env` file in the project directory if the application uses `python-dotenv`:

```bash
nano .env
```

Add the configuration variables required by your implementation. An illustrative example is shown below:

```env
AWS_REGION=us-east-1

AWS_IOT_ENDPOINT=<YOUR_AWS_IOT_ENDPOINT>
AWS_IOT_CERT_PATH=/etc/greenpulse/certs/device.pem.crt
AWS_IOT_KEY_PATH=/etc/greenpulse/certs/private.pem.key
AWS_IOT_ROOT_CA_PATH=/etc/greenpulse/certs/AmazonRootCA1.pem

OPENWEATHER_API_KEY=<YOUR_OPENWEATHER_API_KEY>

LLM_MODE=<YOUR_CONFIGURED_LLM_MODE>
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
```

**Important:** These are example configuration names. Use the exact environment-variable names and values expected by your existing Python modules. Remove variables for integrations that are not used.

The AWS IoT endpoint can be obtained from the AWS IoT Core console.

The LLM configuration should match the mode supported by your `CareAgent` implementation. If the application uses a mock mode, it can be selected according to the existing backend configuration.

Protect the configuration file:

```bash
chmod 600 .env
```

Do not commit `.env`, private keys, certificates, OAuth tokens, or API credentials to a public repository.

### 8. Configure AWS Credentials and Permissions

The backend requires AWS permissions to interact with DynamoDB and other AWS services.

#### Recommended approach: EC2 IAM role

1. Open the IAM console.
2. Create an IAM role for the EC2 service.
3. Attach a policy granting the backend only the required permissions.
4. Associate the role with the `GreenPulse-Backend` EC2 instance.

For DynamoDB, grant the necessary actions on the specific sensor-reading table. For example, the backend may require `dynamodb:PutItem` to save sensor readings.

Add read permissions only if the implementation retrieves existing records.

Use the actual table name and ARN configured in the project.

The IAM role allows the backend to obtain AWS credentials automatically without storing long-lived AWS access keys on the instance.

**Note:** AWS IoT Core MQTT authentication is separate from IAM permissions for DynamoDB. The backend must still have the appropriate IoT certificates, private key, root CA certificate, endpoint, and MQTT permissions.

### 9. Configure AWS IoT Core Certificates

The backend must connect securely to AWS IoT Core.

Ensure that the required certificates are available on the EC2 instance:

* Device or client certificate.
* Corresponding private key.
* Amazon Root CA certificate.

Create a directory to store the certificates:

```bash
sudo mkdir -p /etc/greenpulse/certs
```

Transfer the required certificate files securely to the instance, then move or copy them into this directory.

Set appropriate ownership and permissions. For example:

```bash
sudo chown -R root:root /etc/greenpulse/certs
sudo chmod 700 /etc/greenpulse/certs
sudo chmod 600 /etc/greenpulse/certs/*
```

Ensure that the backend process can read the files. If the service runs as a dedicated non-root user, configure ownership and permissions accordingly.

In the AWS IoT Core console, verify that:

1. The certificate is active.
2. The certificate is associated with the correct IoT policy.
3. The policy permits the required MQTT connection, publishing, and subscription actions.
4. The client ID used by the backend does not conflict with another connected MQTT client.

The MQTT client ID must match the value configured in the backend, not necessarily the ESP32's client ID.

### 10. Configure Gmail Notifications

If the notification agent uses Gmail OAuth, transfer the required OAuth client configuration securely and complete any necessary authorization flow.

Ensure that the application has the permissions required to send email messages and retrieve care-related emails, according to the implemented functionality.

Store sensitive OAuth files outside the public repository and restrict access to them.

If the OAuth flow requires an interactive browser, complete the authorization process using a suitable secure workflow before starting the service.

Verify that token files remain accessible to the backend service after deployment.

### 11. Test the Backend

Activate the virtual environment if it is not already active:

```bash
source venv/bin/activate
```

Run the backend manually:

```bash
python main.py
```

Confirm that the application starts without import errors or missing configuration errors.

Check the logs for successful MQTT connection and subscription messages.

The backend should connect to AWS IoT Core and subscribe to the sensor and device-status topics configured in `mqtt_service.py`.

The project's existing MQTT configuration includes topics such as:

```text
greenpulse/device01/sensors
greenpulse/device01/status
greenpulse/device01/care
```

Use the actual topic names configured in the firmware and backend. Additional topics may be used for weather information and notifications.

Verify the following:

* The backend connects to AWS IoT Core.
* Sensor messages are received from the ESP32.
* Sensor readings are processed by the agent orchestrator.
* Sensor readings are stored in DynamoDB.
* Weather information is retrieved successfully.
* Plant-care recommendations are generated.
* Notification functionality works as expected.
* MQTT messages are published for the Node-RED dashboard.

Once testing is complete, stop the manually running process before configuring the system service.

### 12. Run the Backend Automatically with systemd

To keep the Green Pulse backend running after SSH disconnection and automatically restart it following an instance reboot, configure a systemd service.

First, identify the absolute paths to the project directory and Python interpreter.

For example:

```text
/home/ec2-user/<YOUR_REPOSITORY_DIRECTORY>
/home/ec2-user/<YOUR_REPOSITORY_DIRECTORY>/venv/bin/python
```

Create a service file:

```bash
sudo nano /etc/systemd/system/greenpulse.service
```

Add the following configuration, replacing the project directory and paths with the actual values:

```ini
[Unit]
Description=Green Pulse IoT Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/<YOUR_REPOSITORY_DIRECTORY>
EnvironmentFile=/home/ec2-user/<YOUR_REPOSITORY_DIRECTORY>/.env
ExecStart=/home/ec2-user/<YOUR_REPOSITORY_DIRECTORY>/venv/bin/python /home/ec2-user/<YOUR_REPOSITORY_DIRECTORY>/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

If the application uses certificate files or OAuth tokens, ensure that the `ec2-user` account has the required read permissions. Alternatively, run the service under a dedicated service account and configure file permissions accordingly.

Save the file and reload systemd:

```bash
sudo systemctl daemon-reload
```

Enable the service to start automatically at boot:

```bash
sudo systemctl enable greenpulse
```

Start the backend:

```bash
sudo systemctl start greenpulse
```

Check its status:

```bash
sudo systemctl status greenpulse
```

View live logs:

```bash
sudo journalctl -u greenpulse -f
```

To restart the backend after making changes:

```bash
sudo systemctl restart greenpulse
```

To stop the service:

```bash
sudo systemctl stop greenpulse
```

### 13. Configure the Node-RED Dashboard

The Node-RED dashboard can run separately from the Python backend.

Import the project's `flows.json` file into the Node-RED environment:

1. Open the Node-RED editor.
2. Select the import option.
3. Choose `flows.json`.
4. Deploy the imported flows.
5. Verify the MQTT broker configuration.

Ensure that Node-RED can connect to AWS IoT Core or to the MQTT endpoint configured by the project.

If Node-RED connects directly to AWS IoT Core, configure its MQTT client with the appropriate endpoint, certificates, and permissions.

Check that the configured topics match those used by the ESP32 firmware and backend.

The dashboard should display the available sensor readings, environmental conditions, plant-care recommendations, weather information, and notifications.

### 14. Update the ESP32 Firmware

Open `Main.ino` in the Arduino IDE or your preferred ESP32 development environment.

Verify the following settings:

* Wi-Fi SSID and password.
* AWS IoT Core endpoint.
* MQTT client ID.
* MQTT topic names.
* TLS certificate configuration.

Upload the firmware to the ESP32 DevKit V1.

After connecting to Wi-Fi, the ESP32 should publish sensor readings to the configured MQTT sensor topic.

The EC2 backend receives the readings through AWS IoT Core, processes the data, stores sensor readings in DynamoDB, and publishes relevant results for the dashboard.

Ensure that the ESP32 and backend use compatible MQTT topics and payload formats.

### 15. Verify the Complete Deployment

After all components are configured, perform an end-to-end test.

| Test                 | Expected Result                                                |
| -------------------- | -------------------------------------------------------------- |
| ESP32 startup        | Device initializes and connects to Wi-Fi.                      |
| MQTT connection      | ESP32 and backend connect to AWS IoT Core.                     |
| Sensor readings      | Environmental readings are published by the ESP32.             |
| Backend processing   | The backend receives and processes sensor messages.            |
| Database storage     | Sensor readings are stored in DynamoDB.                        |
| Weather integration  | Current weather information is retrieved when available.       |
| Care recommendations | The care agent generates plant-care guidance.                  |
| Notifications        | Email-related functionality operates as configured.            |
| Dashboard            | Node-RED displays the available readings and updates.          |
| Backend recovery     | systemd restarts the backend after an unexpected process exit. |

### 16. Troubleshooting

**Backend fails to start**

Check the service logs:

```bash
sudo journalctl -u greenpulse -n 100 --no-pager
```

Verify the Python interpreter path, working directory, installed dependencies, and environment variables.

**MQTT connection fails**

Check the AWS IoT endpoint, certificate paths, certificate status, IoT policy, client ID, and network connectivity.

Ensure that the backend uses the correct MQTT port and TLS configuration.

**Sensor readings are not stored in DynamoDB**

Verify the DynamoDB table name, AWS region, EC2 IAM role, and permissions required to write sensor records.

Check the backend logs for DynamoDB validation errors.

**Weather information is unavailable**

Verify the weather API key and internet connectivity. Check whether the weather agent is falling back to mock data.

**LLM recommendations fail**

Verify the configured LLM mode, required API credentials, network connectivity, and applicable API limits.

**Gmail notifications fail**

Check the OAuth credentials, token file permissions, authorization scopes, and token validity.

**Node-RED does not display updates**

Verify the MQTT broker connection, topic names, payload structure, and dashboard deployment.

**Backend stops unexpectedly**

Inspect the systemd logs and confirm that the service is enabled:

```bash
sudo systemctl is-enabled greenpulse
sudo systemctl status greenpulse
```

### 17. Security and Maintenance

Follow these practices when operating the deployed system:

* Restrict SSH access to trusted IP addresses.
* Avoid exposing unnecessary inbound ports.
* Use an EC2 IAM role instead of hardcoding AWS access keys.
* Protect MQTT private keys, certificates, API keys, and OAuth tokens.
* Apply least-privilege permissions to AWS IoT policies and IAM roles.
* Keep the operating system and Python dependencies updated.
* Monitor systemd logs and AWS service usage.
* Avoid committing credentials or sensitive configuration files to Git.
* Review AWS costs associated with EC2, DynamoDB, AWS IoT Core, and external APIs.

For a production deployment, configure appropriate backups, monitoring, and recovery procedures.

### 18. Deployment Summary

The Green Pulse backend runs as a persistent Python service on Amazon EC2. AWS IoT Core provides secure MQTT communication between the ESP32 and the cloud backend, while DynamoDB stores sensor readings.

The backend orchestrates the environment, weather, care, and notification components. The resulting information is published through MQTT for visualization in the Node-RED dashboard.

This deployment removes the need to run the Python backend on a personal computer and provides a cloud-hosted foundation for continuous plant monitoring and care.

**Note:** The backend is expected to remain operational while the EC2 instance is running and available. Actual service availability depends on AWS resource availability, network connectivity, configuration, and the health of the application.
