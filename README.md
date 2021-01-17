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

Pin 2 5V power
Pin 3 i2c SDA
Pin 5 i2c SCL
Pin 6 Ground
Pin 7 GPIO4 used for shutdown
Pin 9 Ground used for shutdown
