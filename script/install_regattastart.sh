#!/bin/bash
#trap 'read -p "run: $BASH_COMMAND "' DEBUG

#set -e
set -x

cd "$(dirname "$0")/.."

echo "=> Installing regattastart files at CGI-BIN...\n"
sudo cp -v regattastart7.py /usr/lib/cgi-bin
sudo cp -v regattastart6.py /usr/lib/cgi-bin
sudo cp -v select_data7.py /usr/lib/cgi-bin
sudo cp -v select_data6.py /usr/lib/cgi-bin
sudo cp -v logging.conf /usr/lib/cgi-bin/
sudo cp -v logging.conf /usr/lib/cgi-bin/
sudo cp -v dropbox_uploader.sh /usr/lib/cgi-bin/
sudo cp -vr Dropbox-Uploader /usr/lib/cgi-bin/
sudo chmod -R 755 /usr/lib/cgi-bin
sudo chown -R www-data:www-data /usr/lib/cgi-bin

echo "=> Installing regattastart php files at /var/www/html/...\n"
sudo mkdir -v -p /var/www/html/images
sudo cp -v /var/www/html/index.html /var/www/html/index0.html
sudo rm -v /var/www/html/index.html
sudo cp -v index.php /var/www/html
sudo cp -v index0.php /var/www/html
sudo cp -v index6.php /var/www/html
sudo cp -v index7.php /var/www/html
sudo cp -v w3.css /var/www/html
sudo chmod -R 755 /var/www/html/
sudo chown -R www-data:www-data /var/www/html

echo "=> setup for videocamera ...\n"
sudo usermod -a -G video www-data
sudo chmod 777 /dev/vchiq
sudo chown root.gpio /dev/gpiomem
sudo chmod g+rw /dev/gpiomem
sudo usermod -a -G gpio www-data

echo "=> setup for video encoding...\n"
sudo apt install -y gpac
