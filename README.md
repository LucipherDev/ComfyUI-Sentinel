<p align="center">
<img src="./sentinel-web/assets/logo_transparent.png" alt="ComfyUI Sentinel Logo" width="200px">
</p>

<div align="center">

# ComfyUI Sentinel
#### ComfyUI Extension for Advanced Security. Implements login, multi-user registration, IP filtering, and user-specific input/output directories.

</div>

### ***☢️ This is still under development. Use at your own risk. ☢️***

## Jump to Section
- **[Installation](#installation)**
- **[Setup](#setup)**
- **[Features](#features)**
- **[ToDo](#todo)**
- **[API Access](#api-access)**
- **[Disclaimer](#%EF%B8%8F-disclaimer)**

## Installation

1. Navigate to your ComfyUI `custom_nodes` directory:
```bash
cd ComfyUI/custom_nodes
```

2. Clone this repository:
```bash
git clone https://github.com/LucipherDev/ComfyUI-Sentinel
```

3. Install dependencies:
```bash
cd ComfyUI-Sentinel
pip install -r requirements.txt
```

### Or Install via ComfyUI Manager

## Setup

1. **Edit `config.json` according to your preferences:**
    - `secret_key_env`: Name of the environment variable for the secret key used to encrypt JWT tokens. If no secret key is set, a random key will be generated.
        - Type: **str**
        - Default: **SECRET_KEY**
    - `users_db`: Name of the user database file.
        - Type: **str**
        - Default: **users_db.json**
    - `access_token_expiration_hours`: Duration (in hours) for which JWT tokens remain valid.
        - Type: **number**
        - Default: **12**
    - `max_access_token_expiration_hours`: Max allowed duration (in hours) for which JWT tokens remain valid.
        - Type: **number**
        - Default: **8760**
    - `log`: Name of the log file.
        - Type: **str**
        - Default: **sentinel.log**
    - `log_levels`: Message levels to log.
        - Type: **str**
        - Options: **["INFO", "WARNING", "ERROR", "DEBUG"]**
        - Default: **["INFO"]**
    - `whitelist`: List of allowed IPs.
        - Type: **str**
        - Default: **whitelist.txt**
    - `blacklist`: List of blocked IPs.
        - Type: **str**
        - Default: **blacklist.txt**
    - `blacklist_after_attempts`: Number of failed login attempts before an IP is blacklisted (0 to disable).
        - Type: **int**
        - Default: **0**
    - `free_memory_on_logout`: Free memory when a user logs out.
        - Type: **bool**
        - Default: **false**
    - `force_https`: Force ComfyUI to use HTTPS.
        - Type: **bool**
        - Default: **false**
    - `separate_users`: Isolate user input/output and queue history. <span style="color:#ef4444">****Experimental***</span>
        - Type: **bool**
        - Default: **false**
    - `manager_admin_only`: Control who can access [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager)
        - Type: **bool**
        - Default: **false**

2. **Run ComfyUI**
3. **Access the GUI URL**
4. **Register the admin account**

**Done!**

### Forgot Admin Password?
- Delete the database file and start over.

*OR*

- Remove the admin user and promote an existing user to admin by adding `"admin": true` to their profile.

***To remove Sentinel, delete the `ComfyUI-Sentinel` folder or uninstall via ComfyUI Manager.***

## Features

- ### Admin Registration
    - Upon the first run, register an admin user with full access and management capabilities.

![admin-register-page](https://github.com/user-attachments/assets/7b3575e8-0dce-4d8e-9417-17baa22bf95f)

- ### User Registration
    - Admins can register new users and assign credentials.

![register-page](https://github.com/user-attachments/assets/0d5002d3-3ee8-4611-a83c-bffe101e8a04)

- ### User Login

![login-page](https://github.com/user-attachments/assets/2ba998eb-3774-4e20-aa15-69e429717028)

- ### Generate Token
    - Get a JWT token for accessing the API.

![generate-token-page](https://github.com/user-attachments/assets/30dd6324-352b-46fb-96f9-2c7132096a16)

- ### Logout
    - A discreet logout button is available.

![logout-button](https://github.com/user-attachments/assets/488e62b7-f124-4dfd-bade-1e6cb1dc84f3)

- ### Timeout Protection
    - Implements a timeout for IP addresses after too many failed login/register attempts. Maximum timeout is 5 minutes unless `blacklist_after_attempts > 0`, in which case the IP will be blacklisted.
    
![failed-attempts](https://github.com/user-attachments/assets/13d9be6e-9f14-47a5-a11d-aec0a9b8d33f)

- ### IP Filtering
    - Filters IP addresses based on whitelist/blacklist rules.
        - **If a whitelist exists, only those IPs will be allowed.**
        - Otherwise, blacklisted IPs will be blocked.

- ### Separate Users <span style="color:#ef4444">****Experimental***</span>
    - Each user has an isolated input/output directory and queue history. Folder access is restricted accordingly. *Still under development but fairly functional. Use at your own risk*

- ### ComfyUI Manager Access
    - If turned on, only the admin user will be able to access the [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) Extension.

## API Access

All API calls to the ComfyUI server require authentication.
You can:
- Include the authentication token in headers: `Authorization: Bearer eyJhbGci...`
- Include it as a cookie named `jwt_token` in the request.

### Register

**Endpoint:**  `POST /register`

**Request Body:**
```json
{
  "new_user_username": "your_username",
  "new_user_password": "your_password",
  "username": "admin_username",   // Required if admin exists
  "password": "admin_password"    // Required if admin exists
}
```

### Login

**Endpoint:**  `POST /login`

**Request Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

## ⚠️ Disclaimer  

*While **ComfyUI Sentinel** enhances security for ComfyUI, it **does not guarantee absolute protection**. Security is about risk mitigation, not elimination. Users are responsible for implementing their own security measures.*  

***Use at your own discretion.***
