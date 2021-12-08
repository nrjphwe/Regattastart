# Regattastart
Machine to start Sailing-regattas and capturing video of the start and finish.


Installation

Connect to your Raspberry Pi via SSH
Clone this repo: git clone https://github.com/nrjphwe/Regattastart
Then cd Regattastart 
and run the setup script: ./script/install_regattastart.sh


The shut down uses GPIO4, which is Pin 7 and pin 9 (ground)

The i2c connection uses pin 3 for SDA, and pin 5 for SCL
The shut down uses GPIO4, which is Pin 7.

- Pin 2 5V power
- Pin 3 i2c SDA
- Pin 5 i2c SCL
- Pin 6 Ground
- Pin 7 GPIO4 used for shutdown
- Pin 9 Ground used for shutdown

- GPIO20 = pin 38 right 2nd from the bottom, for lamp1
- GPIO21 = pin 40 right 1th from bottom, for lamp2
- GPIO26 = pin 37 left 2nd from the bottom, for signal

Get Dropbox working:
- Open: https://www.dropbox.com/developers/apps
- Generate token.
- sudo /usr/lib/cgi-bin/dropbox_uploader.sh
- Add token
- sudo chmod -R 755 /usr/lib/cgi-bin/
- sudo chown -R www-data:www-data /usr/lib/cgi-bin

Setting up wireless networking:
- You will need to define a wpa_supplicant.conf file for your particular wireless network. Put this file in the boot folder, and when the Pi first boots, it will copy that file into the correct location (/etc/wpa_supplicant/wpa_supplicant.conf) in the Linux root file system and use those settings to start up wireless networking.
