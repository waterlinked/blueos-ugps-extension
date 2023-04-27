# BlueOS Extension for Water Linked Underwater GPS

## State

This extension is currently in development. It **has no UI page** (so creates no listing in the sidebar of BlueOS).

## Functionality

Assuming the UGPS is detected and working this service
* forwards MAVLink data from [Mavlink2Rest](https://github.com/patrickelectric/mavlink2rest) like depth to the UGPS Topside (to enable it to function)
* forwards locator position from UGPS Topside to MAVLink (message `GPS_INPUT`)
    * the autopilot should send corresponding `GPS_RAW_INT` messages to the topside computer (QGroundControl)
    * the autopilot sends regular `GLOBAL_POSITION_INT` messages to the topside computer with its filtered position estimates
* forwards topside position from UGPS Topside to UDP port `14401` with NMEA to be received by QGroundControl (implemented, but currently not tested)

If you do not have access to a UGPS system, you can use UGPS_HOST=https://demo.waterlinked.com , which simulates a UGPS system with its API.

Hardware documentation can be found at https://waterlinked.github.io/underwater-gps/integration/bluerov-integration/

## How to install

There are 2 options

### Use the extensions manager in BlueOS 1.1.0
* Click Extensions > Extensions Manager
* Install this extension

Configuration is usually not required, but can be done by editing the extension in the "Installed" tab of the Extensions Manager.

Editing requires [Pirate Mode](https://docs.bluerobotics.com/ardusub-zola/software/onboard/BlueOS-latest/advanced-usage/#pirate-mode)
to be enabled, after which the "Edit" button can be used. Copy the Original Settings contents
into the Custom settings box, and (if necessary) change the IPs/Host addresses, e.g. to use the demo server:
```
{
  "NetworkMode": "host",
  "Env": [
	"UGPS_HOST=https://demo.waterlinked.com",
	"MAVLINK_HOST=http://192.168.2.2:6040",
	"QGC_IP=192.168.2.1"
  ]
}
```

Use the "View Logs" button to check the status.

### Build docker image yourself and start it

To set this up, ssh into the Raspberry Pi (or access via `red-pill` in [BlueOS Terminal](https://docs.bluerobotics.com/ardusub-zola/software/onboard/BlueOS-1.0/advanced-usage/#terminal))

install git, clone this repository and run
```
# build the docker image
docker build -t waterlinked/blueos-ugps-extension:latest .
# see all images
docker images

# running the plugin

# either: run detached
#   with standard command
docker run -d --net=host waterlinked/blueos-ugps-extension:latest python app/main.py --ugps_host http://192.168.2.94 --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
#   or with demo server
docker run -d --net=host waterlinked/blueos-ugps-extension:latest python app/main.py --ugps_host https://demo.waterlinked.com --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1

# or: in interactive shell to get debug output
docker run -it waterlinked/blueos-ugps-extension:latest /bin/bash
#   with standard command
cd app && python main.py --ugps_host http://192.168.2.94 --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
#   or with demo server
cd app && python main.py --ugps_host https://demo.waterlinked.com --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
# end interactive session
exit

# then stop/start/look at log with
docker stop [container-id]
docker start [container-id]
docker log [container-id] # if run detached

# if you are a developer, upload to registry with (replace latest with desired tag)
docker login -u waterlinked
docker push waterlinked/blueos-ugps-extension:latest
```