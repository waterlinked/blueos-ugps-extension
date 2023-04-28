FROM python:3.9-slim-bullseye

COPY app /app
RUN python /app/setup.py install

EXPOSE 80/tcp

LABEL version="1.0.6"

LABEL permissions='\
{\
  "NetworkMode": "host",\
  "Env": [\
	"UGPS_HOST=http://192.168.2.94",\
	"MAVLINK_HOST=http://192.168.2.2:6040",\
	"QGC_IP=192.168.2.1"\
  ]\
}'
LABEL authors='[\
    {\
        "name": "Willian Galvani",\
        "email": "willian@bluerobotics.com"\
    }\
]'
LABEL company='{\
        "about": "",\
        "name": "Water Linked",\
        "email": "support@waterlinked.com"\
    }'
LABEL type="device-integration"
LABEL tags='[\
    "positioning",\
    "navigation",\
    "short-baseline"\
]'
LABEL readme='https://raw.githubusercontent.com/waterlinked/blueos-ugps-extension/{tag}/readme.md'
LABEL links='{\
    "website": "https://github.com/waterlinked/blueos-ugps-extension",\
    "support": "https://github.com/waterlinked/blueos-ugps-extension/issues"\
}'
LABEL requirements="core >= 1.1"

CMD cd /app && python main.py --ugps_host $UGPS_HOST --mavlink_host $MAVLINK_HOST --qgc_ip $QGC_IP
