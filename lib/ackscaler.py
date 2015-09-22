#!/usr/bin/env python

import datetime
import time
import sys
import os
import logging

import boto.ec2
import boto.ec2.elb

COOLDOWN_FILE_PREFIX = '/tmp/.scaler_cooldown'

MYTIME = int(time.time())

class ACKScaler(object):
  def __init__(self, target, key, secret, region, cooldown=15):
    self.target = target
    self.name = 'scaler-' + target
    self.key = key
    self.secret = secret
    self.region = region
    self.cooldown = cooldown

    self.images = []
    self.instances = []
        
    self.conn = self._connect()
      
  def _connect(self):
    try:
      conn = boto.ec2.connect_to_region(
          self.region,
          aws_access_key_id=self.key,
          aws_secret_access_key=self.secret
      )

    except Exception as e:
      print("[ERROR] Unable to connecto to AWS (EC2). Please check your credentials and network connectivity\n")
      sys.exit(2)
    
    return conn

  def _connect_elb(self):
    try:
      conn = boto.ec2.elb.connect_to_region(
          self.region,
          aws_access_key_id=self.key,
          aws_secret_access_key=self.secret
      )

    except Exception as e:
      print("[ERROR] Unable to connect to AWS (ELB). Please check your credentials and network connectivity\n")
      sys.exit(2)
    
    return conn

  def get_oldest_instance(self):
    older_timestamp = 0
    older_instance = None
    
    for instance in self.get_instances():
      lt_datetime = datetime.datetime.strptime(instance.launch_time, '%Y-%m-%dT%H:%M:%S.000Z')
      timestamp = time.mktime(lt_datetime.timetuple())
      
      if not older_timestamp:
        older_instance = instance
    
      if timestamp < older_timestamp:
        older_instance = instance
        
    return older_instance

  def get_latest_image(self):
    latest_timestamp = 0
    latest_image = None
    
    for image in self.get_images():
      lt_datetime = datetime.datetime.strptime(image.creationDate, '%Y-%m-%dT%H:%M:%S.000Z')
      timestamp = time.mktime(lt_datetime.timetuple())
    
      if timestamp > latest_timestamp:
        latest_image = image
        
    return latest_image
    

  def get_images(self):
    # From cache
    if self.images:
      return self.images
      
    retval = []
    for image in self.conn.get_all_images(owners = ['self']):
      if not image.name.startswith(self.name):
        continue
        
      if image.state != 'available':
        print "[WARN ] Image %s is not ready" %image.name
        continue
    
      retval.append(image)
        
    # Cache and return
    self.images = retval
    return retval

  def get_instances(self):
    # From cache
    if self.instances:
      return self.instances
      
    retval = []
    for r in self.conn.get_all_instances():
      for i in r.instances:
        if not self._name(i).startswith(self.name):
          continue
          
        if i.state == 'terminated':
          continue
          
        if i.state != 'running':
          print "[WARN ] Intance %s is not ready" %self._name(i)
          continue
          
        retval.append(i)

    # Cache and return
    self.instances = retval
    return retval

  def create_image(self):
    self._cooldown_check('image')
    images = self.get_images()
    latest_image = self.get_latest_image()
    
    # delete all images except the last one
    for image in images:
      if image.id != latest_image.id:
        print "[INFO ] Deleting old image: %s" % image.name
        try: image.deregister()
        except: pass
        
    # Create image from server
    print "[INFO ] Creating new image: %s" %self.name + '-' + str(MYTIME)
    self.conn.create_image(self.target, self.name + '-' + str(MYTIME), no_reboot=True) 
    self._cooldown_write('image')
    
    return 
    
  def scale_up(self, key_name, size, firewall):
    self._cooldown_check('up')
    image = self.get_latest_image()

    if image:
      name = self.name + '-' + str(MYTIME)
      print "[INFO ] Creating intance: %s" %name
      reservation = self.conn.run_instances(image_id=image.id, key_name=key_name, instance_type=size, security_groups = [firewall])
      instance = reservation.instances[0]
      instance.add_tag("Name",name)
      
      self._cooldown_write('up')
      return instance.id
      
    else:
      print "[ERROR] Cannot find a valid image"
      sys.exit(1)

  def scale_down(self):
    self._cooldown_check('down')
    instance = self.get_oldest_instance()
    if instance:
      print "[INFO ] Deleting instance: %s" %self._name(instance)
      self.conn.terminate_instances(instance_ids=[instance.id])
      
      self._cooldown_write('down')
      return instance.id
      
    else:
      print "[ERROR] Cannot find a valid instance"
      sys.exit(1)

  def add_to_balancer(self, balancer_name, instance_id):
    elb = self._connect_elb()
    balancers = elb.get_all_load_balancers()
    
    for balancer in balancers:
      if balancer.name == balancer_name:
        print "[INFO ] Adding instance to: %s" %balancer.name
        balancer.register_instances([instance_id])
        
    return
    
  def _cooldown_check(self, action):
    if os.path.isfile(COOLDOWN_FILE_PREFIX + action):
      ltime = 0
      with open(COOLDOWN_FILE_PREFIX + action) as ofile:
        ltime = ofile.read()

      if ltime and int(ltime) > MYTIME - (self.cooldown*60):
        print "[ERROR] Can't do that in cooldown period"
        sys.exit(1)
        
    return False
    
  @staticmethod
  def _cooldown_write(action):
    with open(COOLDOWN_FILE_PREFIX + action, 'w') as ofile:
      ofile.write(str(MYTIME))
  
  @staticmethod
  def _name(i):
    n = '[unknown]'
    if 'Name' in i.tags:
      n = i.tags['Name']

    return n

