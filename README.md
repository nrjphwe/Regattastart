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

Temperature during execution with cooler.

The apache-server resides in a Raspberry Pi5 with Bookworm, The web-page index9.php triggers execution of a python script regattastart9.py. The script triggers relays to turn on signals and lamps at the start, then takes pictures and makes videos. The video1 is made through image recognition of sailboats, inference using yolov5. After the video1 is made the index.php page is used to see the resulting time for the sailboats crossing the finish-line, as time is annotated.

