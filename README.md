# Wavin Sentio for Home Assistant

## Requirements
- A Wavin Sentio heated floor controller that is connected to the internet via the RJ45 connector.
- The controller must be added to a Wavin Sentio account. Both things are done via the Wavin Sentio app available in your app store.

## Installation
Files are installed by downloading the files to your custom_components folder directly from here or by adding it via HACS.

Afterwards you can go to the Integrations sections and click the add integration button. Search for Wavin and choose the newly added Wavin Sentio integration.

- First step will ask you to enter you username and password. 
- Second step will ask you to choose the location (controller) you want to add

It will automatically add all the thermostats to your Home Assistant installation and show each one as thermostats in the standard lovelace thermostat UI.

## Changelog
- 2025-08-02 Fix preset, vacation mode, standby mode, cooling mode and outdoor temperature
- 2025-07-03 Major changes for support of v18 - only works with v18 firmware as of now
- 2024-07-09 Removed use of deprecated TEMP_CELSIUS thanks to @https://github.com/201505409 
- 2024-03-05 Changed HVAC logic mode to always be heating
- 2023-12-26 Fixed bug due to new url in API
- 2023-06-25 Fixed bug when having multiple Wavin Sentio controllers same HA instance.
- 2023-05-06 Fixed bug regarding removed async_setup_platforms
- 2023-03-03 Added support for standby switch and refactored existing code
- 2021-12-04 Added support for reauth and outdoor temperature sensor

