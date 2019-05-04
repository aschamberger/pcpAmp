#!/bin/sh

# squeezelite gpio power script
# squeezelite -S /home/tc/power_mute_<gpio>.sh
# squeezelite sets $1 to
#	0: off
#	1: on
#	2: init

GPIO_RELAY=4
GPIOS_MUTE="18
8
12
26
20
21"

init_gpio_out() {
  ACTIVE_LOW=${2:-0}
  sudo sh -c "echo '$1' > /sys/class/gpio/export"
  sudo sh -c "echo '$ACTIVE_LOW' > /sys/class/gpio/gpio$1/active_low"
  sudo sh -c "echo 'out' > /sys/class/gpio/gpio$1/direction"
  sudo sh -c "echo '0' > /sys/class/gpio/gpio$1/value"
}

gpio_on() {
  sudo sh -c "echo '1' > /sys/class/gpio/gpio$1/value"
}

gpio_off() {
  sudo sh -c "echo '0' > /sys/class/gpio/gpio$1/value"
}

# redirect output to ssh window if exist
TERMINAL=/dev/pts/0
if [ ! -e $TERMINAL ]; then
  TERMINAL=/dev/null
fi

# extract GPIO number from script filename
NUM=$0
NUM=${NUM%.*}
NUM=${NUM##*_}
if [ "$NUM" = "mute" ]; then
  echo "create symlink with '_<gpio_id>' added to filename" >$TERMINAL
  exit 1
fi

case $1 in
# init
2)
  # check if other player already initialized relay
  if [ ! -d "/sys/class/gpio/gpio$GPIO_RELAY/" ]; then
    echo "set up relay (GPIO $GPIO_RELAY)" >$TERMINAL
    init_gpio_out $GPIO_RELAY
  fi
  # check if GPIO already initialized
  if [ ! -d "/sys/class/gpio/gpio$NUM/" ]; then
    echo "set up muting (GPIO $NUM)" >$TERMINAL
    init_gpio_out $NUM 1
  fi
;;
# on
1)
  RELAY_ON=$(sudo sh -c "cat /sys/class/gpio/gpio$GPIO_RELAY/value")
  if [ $RELAY_ON == 0 ]; then
    echo "power on relay (GPIO $GPIO_RELAY)" >$TERMINAL
    gpio_on $GPIO_RELAY
  fi
  echo "unmute (GPIO $NUM)" >$TERMINAL
  gpio_on $NUM
;;
# off
0)
  echo "mute (GPIO $NUM)" >$TERMINAL
  gpio_off $NUM
  ALL_MUTE=1
  for ID in $GPIOS_MUTE
  do
    if [ ! -d "/sys/class/gpio/gpio$NUM/" ]; then
      GPIO_ON=$(sudo sh -c "cat /sys/class/gpio/gpio$ID/value")
      if [ GPIO_ON == 1 ]; then
        ALL_MUTE=0
        break
      fi
    fi
  done
  if [ $ALL_MUTE == 1 ]; then
    echo "power off relay (GPIO $GPIO_RELAY)" >$TERMINAL
    gpio_off $GPIO_RELAY
  fi
;;
esac
