#!/bin/bash
#trap 'read -p "run: $BASH_COMMAND "' DEBUG

#set -e
set -x

cd "$(dirname "$0")/.."

echo "=> Installing regattastart files at CGI-BIN...\n"
sudo cp -v regattastart10.py /usr/lib/cgi-bin
sudo cp -v regattastart9.py /usr/lib/cgi-bin
sudo cp -v regattastart6.py /usr/lib/cgi-bin
sudo cp -v logging.conf /usr/lib/cgi-bin
sudo cp -v common_module.py /usr/lib/cgi-bin
sudo chmod -R 755 /usr/lib/cgi-bin
sudo chown -R www-data:www-data /usr/lib/cgi-bin

sudo apt update
sudo apt install apache2 -y
sudo systemctl restart apache2.service

sudo apt install php libapache2-mod-php -y


echo "=> Installing regattastart php files at /var/www/html/...\n"
sudo mkdir -v -p /var/www/html/images
sudo cp -v /var/www/html/index.html /var/www/html/index0.html
sudo rm -v /var/www/html/index.html
sudo cp -v index.php /var/www/html
sudo cp -v index6.php /var/www/html
sudo cp -v index9.php /var/www/html
sudo cp -v functions.php /var/www/html
sudo cp -v get_video1_content.php /var/www/html
sudo cp -v stop_recording.php /var/www/html
sudo mkdir /var/www/html/tmp
sudo mkdir /var/www/html/tmp/stop_recording_pipe
sudo cp -v w3.css /var/www/html
sudo chmod -R 755 /var/www/html/
sudo chown -R www-data:www-data /var/www/html


echo "=> setup for videocamera ...\n"
sudo usermod -a -G video www-data
sudo adduser www-data video
echo: maybe not needed sudo chmod 777 /dev/vchiq
sudo chown root:gpio /dev/gpiomem
sudo chmod g+rw /dev/gpiomem
sudo usermod -a -G gpio www-data

echo: "to let above commands survice reboot"
echo: Create a file, e.g., /etc/udev/rules.d/99-mem.rules, with the following content:
sudo mkdir -v -p /etc/udev/rules.d/99-mem.rules
echo 'KERNEL=="mem", MODE="0660"' | sudo tee -a /etc/udev/rules.d/99-mem.rules

sudo mkdir -v -p /etc/udev/rules.d/99-gpioomem.rules
echo 'KERNEL=="gpiomem", GROUP="gpio", MODE="0660"' | sudo tee -a /etc/udev/rules.d/99-gpiomem.rules

echo "=> setup for camera...\n"
python3 -m venv yolov5_env
python3 -m venv --system-site-packages yolov5_env
source /home/pi/yolov5_env/bin/activate
pip install opencv-contrib-python
python3 -m pip install opencv-python
deactivate

sudo chown -R pi:www-data /home/pi/yolov5_env/bin/python
