# Regattastart
Machine to start Sailing-regattas and capturing video of the start and finish.

Installation

Connect to your Raspberry Pi via SSH
Clone this repo: git clone https://github.com/nrjphwe/Regattastart
Then cd Regattastart 
and run the setup script: ./script/install_regattastart.sh

The i2c connection uses pin 3 for SDA, and pin 5 for SCL

- Pin 2 5V power
- Pin 3 i2c SDA
- Pin 5 i2c SCL
- Pin 6 Ground

- GPIO20 = pin 38 right 2nd from the bottom, for lamp1
- GPIO21 = pin 40 right 1th from bottom, for lamp2
- GPIO26 = pin 37 left 2nd from the bottom, for signal

Setting up wireless networking (Not valid with RPI5 and Bookworm):
- You will need to define a wpa_supplicant.conf file for your particular wireless network. Put this file in the boot folder, and when the Pi first boots, it will copy that file into the correct location (/etc/wpa_supplicant/wpa_supplicant.conf) in the Linux root file system and use those settings to start up wireless networking.


Temperature during execution with cooler, not over 60 degree.
