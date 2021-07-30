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

- GPIO19 = pin 35 left 3rd from the bottom, for signalhorn
- GPIO20 = pin 38 right 2nd from the bottom, for lamp1
- GPIO26 = pin 37 left 2nd from the bottom, for lamp2
- GPIO21 = pin 40 right 1th from bottom

Get Dropbox working:
- Open: https://www.dropbox.com/developers/apps
- Generate token.
- sudo /usr/lib/cgi-bin/dropbox_uploader.sh
- Add token
- sudo chmod -R 755 /usr/lib/cgi-bin/
- sudo chown -R www-data:www-data /usr/lib/cgi-bin
