#! /bin/sh

set -e

cd "$(dirname "$0")/.."

echo "=> Installing apache...\n"
sudo apt update
sudo apt install apache2 -y
sudo a2enmod cgi

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

echo "=> Installing PHP...\n"
sudo apt install php libapache2-mod-php -y

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

# We have a script "listen-for-shutdown.py", which will shutdown the PI when triggered by a switch.  
# We need to start this script on boot. So we'll place the script in /usr/local/bin and make it executable:
sudo cp listen-for-shutdown.py /usr/local/bin/
sudo chmod +x /usr/local/bin/listen-for-shutdown.py

# Now add another script called listen-for-shutdown.sh that will start/stop our service.
# Place this file in /etc/init.d and make it executable.
sudo cp listen-for-shutdown.sh /etc/init.d/
sudo chmod +x /etc/init.d/listen-for-shutdown.sh
# Now we'll register the script to run on boot.
sudo update-rc.d listen-for-shutdown.sh defaults

