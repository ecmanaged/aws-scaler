#!/usr/bin/env python

# Autentication data and region
AWS_KEY_ID='AKIxxxxx'
AWS_SECRET='xxxxxxxx'
AWS_REGION='eu-west-1'

# Instace to scale
TARGET_INSTANCE_ID='i-xxxxxx'

# Parameter for new server
NEW_SERVER_KEY_NAME = 'key_name'
NEW_SERVER_TYPE = 'm1.small'
NEW_SERVER_FIREWALL = 'security_group_name'

# Add to balancer
BALANCER_NAME = 'balancer_name'

# Min / Max instances in scaling group
MIN_INSTANCES = 0
MAX_INSTANCES = 10

# Cooldown period (in minutes)
COOLDOWN = 5
