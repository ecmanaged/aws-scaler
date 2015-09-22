#!/usr/bin/env python

import os
import sys

# Add my dir to path
root_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(root_dir + '/lib')

from config import *
from ackscaler import ACKScaler

# Commands
commands = ['scale_up', 'scale_down', 'create_image']

# Check for a valid argument
if len(sys.argv) < 2 or sys.argv[1] not in commands:
  sys.exit('Usage: %s %s' % (sys.argv[0],'|'.join(commands)))
action = sys.argv[1]

scaler = ACKScaler(TARGET_INSTANCE_ID, AWS_KEY_ID, AWS_SECRET, AWS_REGION, COOLDOWN)
instances = scaler.get_instances()
  
if action == 'scale_up':
  if len(instances) >= MAX_INSTANCES:
    print "[ERROR] Too many instances running"
    sys.exit(1)
      
  # Try to scale UP
  id = scaler.scale_up(NEW_SERVER_KEY_NAME, NEW_SERVER_TYPE, NEW_SERVER_FIREWALL)
  
  # if created instance, add to balancer
  if id and BALANCER_NAME:
    scaler.add_to_balancer(BALANCER_NAME, id)
      
elif action == 'scale_down':
  if len(instances) <= MIN_INSTANCES:
    print "[ERROR] To few instances running"
    sys.exit(1)

  # Try to scale DOWN
  scaler.scale_down()

elif action == 'create_image':
  # Create a new image and remove old ones
  scaler.create_image()

