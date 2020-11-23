#! /bin/sh

set -e

cd "$(dirname "$0")/.."

echo "=> Installing apache...\n"
sudo apt update
sudo apt install apache2 -y
sudo a2enmod cgi


echo "=> Installing regattastart files at CGI-BIN...\n"
sudo cp regattastart7.py /usr/lib/cgi-bin
sudo cp regattastart6.py /usr/lib/cgi-bin
sudo cp select_data7.py /usr/lib/cgi-bin
sudo cp select_data6.py /usr/lib/cgi-bin
sudo cp logging.conf /usr/lib/cgi-bin/
sudo cp power_check.py /usr/lib/cgi-bin
sudo cp .dropbox_uploader /usr/lib/cgi-bin/
sudo cp -vr /Dropbox-Uploader /usr/lib/cgi-bin/
sudo chmod -R 755 /usr/lib/cgi-bin
sudo chown -R www-data:www-data /usr/lib/cgi-bin

echo "=> Installing PHP...\n"
sudo apt install php libapache2-mod-php -y

echo "=> Installing regattastart php files at /var/www/html/...\n"
sudo mkdir /var/www/html/images
sudo cp index.php /var/www/html
sudo cp index0.php /var/www/html
sudo cp index4.php /var/www/html
sudo cp index5.php /var/www/html
sudo cp index6.php /var/www/html
sudo cp index7.php /var/www/html
sudo cp w3.css /var/www/html
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
